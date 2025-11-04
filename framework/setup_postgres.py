#!/usr/bin/env python3
"""
PostgreSQL Setup Helper
Creates database and tables for LangGraph checkpointing

Usage:
    python framework/setup_postgres.py
    
Or with custom connection string:
    python framework/setup_postgres.py "postgresql://user:pass@host:5432/dbname"
"""

import sys
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver


def setup_postgres_database(connection_string: str):
    """
    Setup PostgreSQL database for LangGraph checkpointing
    
    Args:
        connection_string: PostgreSQL connection string
    """
    print("🔧 Setting up PostgreSQL for LangGraph checkpointing...")
    print(f"   Connection: {_mask_password(connection_string)}")
    
    try:
        # Connect to PostgreSQL
        print("   Connecting to database...")
        conn = psycopg.connect(connection_string, autocommit=True, prepare_threshold=0)
        
        # Initialize PostgresSaver
        print("   Initializing checkpoint tables...")
        checkpointer = PostgresSaver(conn)
        
        # Create tables (idempotent operation)
        checkpointer.setup()
        
        print("\n✅ PostgreSQL setup complete!")
        print("\nCreated tables:")
        print("  • checkpoints         - Stores workflow state snapshots")
        print("  • checkpoint_writes   - Stores pending writes")
        
        # Verify tables exist
        print("\n📊 Verifying tables...")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('checkpoints', 'checkpoint_writes')
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            if len(tables) == 2:
                print(f"   ✓ Found {len(tables)} tables")
                for table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    print(f"   ✓ {table}: {count} rows")
            else:
                print(f"   ⚠️  Warning: Expected 2 tables, found {len(tables)}")
        
        conn.close()
        print("\n✨ Database is ready for durable executions!")
        
    except psycopg.OperationalError as e:
        print(f"\n❌ Error: Could not connect to PostgreSQL")
        print(f"   {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Verify connection string is correct")
        print("  3. Check database exists: createdb langgraph")
        print("  4. Check credentials and permissions")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)


def _mask_password(conn_str: str) -> str:
    """Mask password in connection string for display"""
    if ':' in conn_str and '@' in conn_str:
        # URL format: postgresql://user:pass@host/db
        parts = conn_str.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].rsplit(':', 1)
            return f"{user_pass[0]}:****@{parts[1]}"
    return conn_str


def load_config_connection_string() -> str:
    """Load connection string from durability config file"""
    import os
    import yaml
    
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'config',
        'durability_config.yaml'
    )
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get('connection_string', '')
    
    return ''


def main():
    """Main entry point"""
    print("="*70)
    print("PostgreSQL Setup for LangGraph Durable Executions")
    print("="*70 + "\n")
    
    # Get connection string from command line or config
    if len(sys.argv) > 1:
        connection_string = sys.argv[1]
    else:
        print("Loading connection string from config/durability_config.yaml...")
        connection_string = load_config_connection_string()
        
        if not connection_string:
            print("\n❌ Error: No connection string provided")
            print("\nUsage:")
            print("  1. Update config/durability_config.yaml with connection_string")
            print("  2. Or run: python framework/setup_postgres.py <connection_string>")
            print("\nExample:")
            print('  python framework/setup_postgres.py "postgresql://postgres:postgres@localhost:5432/langgraph"')
            sys.exit(1)
    
    # Run setup
    setup_postgres_database(connection_string)


if __name__ == "__main__":
    main()

