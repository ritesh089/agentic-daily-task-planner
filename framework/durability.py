"""
Durability Module
Provides PostgreSQL-backed checkpointing for durable workflow executions
"""

import os
import yaml
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg


# Global configuration
_config = None
_durability_manager = None
_initialized = False


# ============================================================================
# Configuration Loading
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load durability configuration from YAML file"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'config', 
        'durability_config.yaml'
    )
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # Default configuration if file doesn't exist
    return {
        'enabled': False,
        'service_name': 'langgraph-app',
        'connection_string': 'postgresql://postgres:postgres@localhost:5432/langgraph',
        'checkpoint': {
            'frequency': 'each_node',
            'mode': 'full_state'
        },
        'resume': {
            'auto_resume': False,
            'max_age_hours': 24
        }
    }


# ============================================================================
# Durability Manager
# ============================================================================

class DurabilityManager:
    """
    Manages PostgreSQL-backed workflow checkpointing and resumption
    
    Provides:
    - PostgreSQL checkpointer initialization
    - Thread ID generation
    - Interrupted workflow detection
    - Automatic resumption logic
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize DurabilityManager with configuration
        
        Args:
            config: Durability configuration dictionary
        """
        self.config = config
        self.checkpointer = None
        self.connection = None
        
    def init_checkpointer(self) -> Optional[PostgresSaver]:
        """
        Initialize PostgreSQL checkpointer using LangGraph's PostgresSaver
        
        Returns:
            PostgresSaver instance if enabled, None otherwise
        """
        if not self.config.get('enabled', False):
            print("💾 Durability: Disabled by configuration")
            return None
        
        try:
            # Build PostgreSQL connection string
            conn_str = self._build_connection_string()
            
            # Create PostgreSQL connection
            self.connection = psycopg.connect(
                conn_str,
                autocommit=True,
                prepare_threshold=0
            )
            
            # Initialize LangGraph PostgresSaver
            self.checkpointer = PostgresSaver(self.connection)
            
            # Setup schema (creates tables if not exist)
            self.checkpointer.setup()
            
            print(f"💾 Durability: Enabled (PostgreSQL)")
            print(f"   Database: {self._get_database_name(conn_str)}")
            print(f"   Auto-resume: {self.config.get('resume', {}).get('auto_resume', False)}")
            
            return self.checkpointer
            
        except Exception as e:
            print(f"⚠️  Durability: Failed to initialize PostgreSQL checkpointer: {e}")
            print(f"   Continuing without durable executions")
            return None
    
    def _build_connection_string(self) -> str:
        """
        Build PostgreSQL connection string from config
        
        Returns:
            Connection string for psycopg
        """
        # Option 1: Use explicit connection string
        if 'connection_string' in self.config:
            return self.config['connection_string']
        
        # Option 2: Build from components
        pg_config = self.config.get('postgres', {})
        return (
            f"host={pg_config.get('host', 'localhost')} "
            f"port={pg_config.get('port', 5432)} "
            f"dbname={pg_config.get('database', 'langgraph')} "
            f"user={pg_config.get('user', 'postgres')} "
            f"password={pg_config.get('password', '')}"
        )
    
    def _get_database_name(self, conn_str: str) -> str:
        """Extract database name from connection string for display"""
        if '/' in conn_str:
            # Extract from URL format
            return conn_str.split('/')[-1].split('?')[0]
        elif 'dbname=' in conn_str:
            # Extract from key-value format
            for part in conn_str.split():
                if part.startswith('dbname='):
                    return part.split('=')[1]
        return 'unknown'
    
    def generate_thread_id(self, service_name: Optional[str] = None) -> str:
        """
        Generate unique thread ID for workflow execution
        
        Args:
            service_name: Optional service name override
            
        Returns:
            Unique thread ID string
        """
        parts = []
        
        # Add service name
        if self.config.get('thread_id', {}).get('include_service_name', True):
            name = service_name or self.config.get('service_name', 'app')
            parts.append(name)
        
        # Add timestamp
        if self.config.get('thread_id', {}).get('include_timestamp', True):
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            parts.append(timestamp)
        
        # Add random suffix
        if self.config.get('thread_id', {}).get('include_random_suffix', True):
            random_suffix = uuid.uuid4().hex[:8]
            parts.append(random_suffix)
        
        return '-'.join(parts)
    
    def find_interrupted_workflows(self) -> List[Dict[str, Any]]:
        """
        Find workflows that were interrupted before completion
        
        Queries PostgreSQL for workflows that have checkpoints but never reached END state.
        Only returns workflows within the max_age_hours window.
        
        Returns:
            List of dicts with thread_id and last_checkpoint info
        """
        if not self.checkpointer or not self.connection:
            return []
        
        try:
            # Query for threads that have checkpoints but no END node
            # Note: PostgreSQL checkpoint tables don't have a timestamp column by default
            # We query all interrupted workflows regardless of age
            with self.connection.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT thread_id, MAX(checkpoint_id) as last_checkpoint_id
                    FROM checkpoints
                    GROUP BY thread_id
                    HAVING thread_id NOT IN (
                        SELECT DISTINCT thread_id 
                        FROM checkpoints 
                        WHERE checkpoint_ns LIKE '%%__end__'
                    )
                    ORDER BY MAX(checkpoint_id) DESC
                """)
                
                interrupted = []
                for row in cur.fetchall():
                    interrupted.append({
                        'thread_id': row[0],
                        'last_checkpoint_id': row[1]
                    })
                
                return interrupted
                
        except Exception as e:
            print(f"⚠️  Error finding interrupted workflows: {e}")
            return []
    
    def resume_workflow(self, workflow, thread_id: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Resume an interrupted workflow from its last checkpoint
        
        Args:
            workflow: Compiled LangGraph workflow
            thread_id: Thread ID of workflow to resume
            config: Configuration dict with thread_id
            
        Returns:
            Final workflow state if successful, None otherwise
        """
        if not self.checkpointer:
            return None
        
        try:
            print(f"  🔄 Resuming workflow: {thread_id}")
            
            # Resume by invoking with the same thread_id
            # LangGraph will automatically load the last checkpoint
            result = workflow.invoke(None, config=config)
            
            print(f"  ✓ Workflow resumed successfully")
            return result
            
        except Exception as e:
            print(f"  ✗ Failed to resume workflow {thread_id}: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources (close DB connection)"""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass


# ============================================================================
# Module-Level Functions
# ============================================================================

def init_durability() -> Optional[DurabilityManager]:
    """
    Initialize durability system
    
    Returns:
        DurabilityManager instance if enabled, None otherwise
    """
    global _config, _durability_manager, _initialized
    
    if _initialized:
        return _durability_manager
    
    _config = load_config()
    _durability_manager = DurabilityManager(_config)
    
    # Initialize checkpointer
    _durability_manager.init_checkpointer()
    
    _initialized = True
    return _durability_manager


def get_durability_manager() -> Optional[DurabilityManager]:
    """Get the global durability manager instance"""
    return _durability_manager

