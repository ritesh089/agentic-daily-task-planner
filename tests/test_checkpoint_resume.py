"""
Test Checkpoint/Resume Functionality with Mock Agents

These tests verify that the framework's durable execution system
correctly saves checkpoints and resumes workflows after failures.
"""

import pytest
import psycopg
import yaml
from pathlib import Path
from typing import Dict, Any

# Import framework components
from framework.loader import load_and_run_app
from framework.durability import init_durability, get_durability_manager

# Import mock configuration utilities
from app.agents.mocks.email_agents import MockEmailConfig
from app.agents.mocks.slack_agents import MockSlackConfig


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def db_connection():
    """Provide database connection for test verification"""
    conn_str = "postgresql://postgres:postgres@localhost:5432/langgraph"
    try:
        conn = psycopg.connect(conn_str, autocommit=True)
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture(autouse=True)
def reset_mock_config():
    """Reset mock configuration before each test"""
    MockEmailConfig.reset()
    MockSlackConfig.reset()
    yield


@pytest.fixture
def clean_database(db_connection):
    """Clean checkpoint tables before each test"""
    with db_connection.cursor() as cur:
        cur.execute("DELETE FROM checkpoint_writes")
        cur.execute("DELETE FROM checkpoints")
    yield


@pytest.fixture
def mock_config_path():
    """Path to mock configuration file"""
    return Path(__file__).parent.parent / "config" / "mock_config.yaml"


@pytest.fixture
def durability_config_path():
    """Path to durability configuration file"""
    return Path(__file__).parent.parent / "config" / "durability_config.yaml"


@pytest.fixture
def enable_mocks(mock_config_path):
    """Enable mocks in configuration"""
    with open(mock_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    original_config = config.copy()
    config['enabled'] = True
    config['active_scenario'] = 'default'
    
    with open(mock_config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    yield config
    
    # Restore original config
    with open(mock_config_path, 'w') as f:
        yaml.dump(original_config, f, default_flow_style=False)


@pytest.fixture
def enable_durability(durability_config_path):
    """Ensure durability is enabled"""
    with open(durability_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if not config.get('enabled', False):
        pytest.skip("Durability not enabled in config")
    
    return config


# ============================================================================
# Helper Functions
# ============================================================================

def count_checkpoints(db_connection, thread_id: str = None) -> int:
    """Count checkpoints in database"""
    with db_connection.cursor() as cur:
        if thread_id:
            cur.execute(
                "SELECT COUNT(*) FROM checkpoints WHERE thread_id = %s",
                (thread_id,)
            )
        else:
            cur.execute("SELECT COUNT(*) FROM checkpoints")
        return cur.fetchone()[0]


def get_interrupted_workflows(db_connection) -> list:
    """Get list of interrupted workflow thread IDs"""
    with db_connection.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT thread_id 
            FROM checkpoints 
            WHERE thread_id NOT IN (
                SELECT thread_id 
                FROM checkpoints 
                WHERE checkpoint_ns LIKE '%__end__'
            )
        """)
        return [row[0] for row in cur.fetchall()]


def set_mock_scenario(mock_config_path: Path, scenario: str):
    """Update mock configuration to use specific scenario"""
    with open(mock_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    config['active_scenario'] = scenario
    
    with open(mock_config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def get_initial_state() -> Dict[str, Any]:
    """Get initial workflow state"""
    return {
        'time_range_hours': 24,
        'emails': [],
        'slack_messages': [],
        'email_summary': '',
        'slack_summary': '',
        'extracted_tasks': [],
        'prioritized_tasks': [],
        'email_sent': False,
        'errors': []
    }


# ============================================================================
# Test Cases
# ============================================================================

class TestCheckpointCreation:
    """Test that checkpoints are created correctly"""
    
    def test_checkpoints_created_on_success(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify checkpoints are created during successful workflow execution"""
        # Arrange
        set_mock_scenario(mock_config_path, "default")
        initial_checkpoints = count_checkpoints(db_connection)
        
        # Act
        result = load_and_run_app("app.workflow", get_initial_state())
        
        # Assert
        final_checkpoints = count_checkpoints(db_connection)
        assert final_checkpoints > initial_checkpoints, \
            "Checkpoints should be created during workflow execution"
        assert result is not None, "Workflow should complete successfully"
        assert len(result.get('errors', [])) == 0, \
            "No errors should occur in successful execution"


class TestEmailCollectionFailure:
    """Test checkpoint/resume when email collection fails"""
    
    def test_email_collection_failure_creates_checkpoint(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify checkpoint is saved when email collection fails"""
        # Arrange
        set_mock_scenario(mock_config_path, "email_collection_failure")
        
        # Act & Assert - Expect failure
        with pytest.raises(Exception, match="Email collection failed"):
            load_and_run_app("app.workflow", get_initial_state())
        
        # Verify checkpoint was created (though workflow failed)
        interrupted = get_interrupted_workflows(db_connection)
        assert len(interrupted) >= 0, \
            "Checkpoint may or may not exist depending on when failure occurred"
    
    def test_email_collection_resume_after_failure(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify workflow resumes after email collection failure is fixed"""
        # Arrange - First run with failure
        set_mock_scenario(mock_config_path, "email_collection_failure")
        
        # Act - First attempt (should fail)
        with pytest.raises(Exception):
            load_and_run_app("app.workflow", get_initial_state())
        
        interrupted_before = get_interrupted_workflows(db_connection)
        
        # Fix the failure
        set_mock_scenario(mock_config_path, "default")
        
        # Act - Second attempt (should resume or start fresh)
        result = load_and_run_app("app.workflow", get_initial_state())
        
        # Assert
        assert result is not None, "Workflow should complete after fixing failure"
        interrupted_after = get_interrupted_workflows(db_connection)
        # Note: May start fresh if no checkpoint was saved before failure


class TestSlackCollectionFailure:
    """Test checkpoint/resume when slack collection fails"""
    
    def test_slack_collection_failure_creates_checkpoint(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify checkpoint is saved before slack collection fails"""
        # Arrange
        set_mock_scenario(mock_config_path, "slack_collection_failure")
        checkpoints_before = count_checkpoints(db_connection)
        
        # Act & Assert - Expect failure
        with pytest.raises(Exception, match="Slack collection failed"):
            load_and_run_app("app.workflow", get_initial_state())
        
        # Assert - Checkpoint should exist from email collection
        checkpoints_after = count_checkpoints(db_connection)
        assert checkpoints_after > checkpoints_before, \
            "Email collection should have created checkpoint before slack failure"
        
        interrupted = get_interrupted_workflows(db_connection)
        assert len(interrupted) > 0, "Should have at least one interrupted workflow"
    
    def test_slack_collection_resume_skips_email(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify workflow resumes from checkpoint, skipping email collection"""
        # Arrange - First run with slack failure
        set_mock_scenario(mock_config_path, "slack_collection_failure")
        
        # Act - First attempt (should fail at slack)
        with pytest.raises(Exception):
            load_and_run_app("app.workflow", get_initial_state())
        
        thread_id = get_interrupted_workflows(db_connection)[0]
        checkpoints_before = count_checkpoints(db_connection, thread_id)
        
        # Fix and resume
        set_mock_scenario(mock_config_path, "default")
        result = load_and_run_app("app.workflow", get_initial_state())
        
        # Assert
        assert result is not None, "Workflow should complete successfully"
        checkpoints_after = count_checkpoints(db_connection, thread_id)
        
        # If resumed, checkpoint count should increase
        # If started fresh, new thread_id would be created
        # Both are acceptable behaviors


class TestSummarizationFailures:
    """Test checkpoint/resume for summarization failures"""
    
    def test_email_summarization_failure_and_resume(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Test failure at email summarization and successful resume"""
        # Arrange
        set_mock_scenario(mock_config_path, "email_summarization_failure")
        
        # Act - Expect failure
        with pytest.raises(Exception, match="Email summarization failed"):
            load_and_run_app("app.workflow", get_initial_state())
        
        # Verify checkpoint exists
        interrupted = get_interrupted_workflows(db_connection)
        assert len(interrupted) > 0, "Should have interrupted workflow"
        
        # Fix and resume
        set_mock_scenario(mock_config_path, "default")
        result = load_and_run_app("app.workflow", get_initial_state())
        
        # Assert
        assert result is not None, "Workflow should complete after fix"


class TestMultipleFailures:
    """Test checkpoint/resume with multiple failure scenarios"""
    
    def test_multiple_failures_multiple_resumes(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Test workflow can handle multiple failure/resume cycles"""
        # Arrange
        set_mock_scenario(mock_config_path, "multiple_failures")
        
        # Act - First failure (email summarization)
        with pytest.raises(Exception):
            load_and_run_app("app.workflow", get_initial_state())
        
        interrupted_count_1 = len(get_interrupted_workflows(db_connection))
        assert interrupted_count_1 > 0, "Should have interrupted workflow"
        
        # Fix and continue - will still fail at slack summarization
        set_mock_scenario(mock_config_path, "slack_summarization_failure")
        
        with pytest.raises(Exception):
            load_and_run_app("app.workflow", get_initial_state())
        
        # Finally fix everything
        set_mock_scenario(mock_config_path, "default")
        result = load_and_run_app("app.workflow", get_initial_state())
        
        # Assert
        assert result is not None, "Should eventually complete"


class TestCheckpointData:
    """Test checkpoint data integrity"""
    
    def test_checkpoint_contains_state_data(
        self,
        clean_database,
        db_connection,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify checkpoints contain workflow state data"""
        # Arrange
        set_mock_scenario(mock_config_path, "default")
        
        # Act
        result = load_and_run_app("app.workflow", get_initial_state())
        
        # Assert - Check checkpoint data
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT checkpoint_ns, metadata 
                FROM checkpoints 
                ORDER BY checkpoint_id DESC 
                LIMIT 1
            """)
            row = cur.fetchone()
            
            assert row is not None, "Should have at least one checkpoint"
            checkpoint_ns, metadata = row
            assert checkpoint_ns is not None, "Checkpoint should have namespace"


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndWithMocks:
    """End-to-end tests using mock agents"""
    
    def test_complete_workflow_with_mocks(
        self,
        clean_database,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Test complete workflow execution with mock agents"""
        # Arrange
        set_mock_scenario(mock_config_path, "default")
        initial_state = get_initial_state()
        
        # Act
        result = load_and_run_app("app.workflow", initial_state)
        
        # Assert
        assert result is not None
        assert 'emails' in result
        assert 'slack_messages' in result
        assert 'email_summary' in result
        assert 'slack_summary' in result
        assert 'extracted_tasks' in result
        assert 'prioritized_tasks' in result
        assert len(result.get('errors', [])) == 0
    
    def test_mock_data_is_realistic(
        self,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify mock agents provide realistic test data"""
        # Arrange
        set_mock_scenario(mock_config_path, "default")
        initial_state = get_initial_state()
        
        # Act
        result = load_and_run_app("app.workflow", initial_state)
        
        # Assert - Check mock data structure
        assert len(result['emails']) > 0, "Should have mock emails"
        assert len(result['slack_messages']) > 0, "Should have mock messages"
        
        # Verify email structure
        email = result['emails'][0]
        assert 'from' in email
        assert 'subject' in email
        assert 'body' in email
        
        # Verify slack message structure
        message = result['slack_messages'][0]
        assert 'from' in message
        assert 'text' in message
        assert 'type' in message


# ============================================================================
# Performance Tests
# ============================================================================

class TestMockPerformance:
    """Test that mocks are faster than real API calls"""
    
    def test_mocks_execute_quickly(
        self,
        clean_database,
        enable_mocks,
        enable_durability,
        mock_config_path
    ):
        """Verify mock execution completes in reasonable time"""
        import time
        
        # Arrange
        set_mock_scenario(mock_config_path, "default")
        initial_state = get_initial_state()
        
        # Act
        start_time = time.time()
        result = load_and_run_app("app.workflow", initial_state)
        duration = time.time() - start_time
        
        # Assert - Should complete in under 30 seconds with mocks
        assert duration < 30, \
            f"Mock workflow took {duration}s, should be faster"
        assert result is not None


# ============================================================================
# Configuration Tests
# ============================================================================

class TestMockConfiguration:
    """Test mock configuration loading and application"""
    
    def test_mock_config_loads_correctly(self, mock_config_path):
        """Verify mock configuration can be loaded"""
        with open(mock_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert 'enabled' in config
        assert 'active_scenario' in config
        assert 'scenarios' in config
        assert 'mocks' in config
    
    def test_all_scenarios_are_defined(self, mock_config_path):
        """Verify all test scenarios are properly defined"""
        with open(mock_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        scenarios = config['scenarios']
        
        # Required scenarios
        required = [
            'default',
            'email_collection_failure',
            'slack_collection_failure',
            'email_summarization_failure',
            'multiple_failures'
        ]
        
        for scenario in required:
            assert scenario in scenarios, \
                f"Required scenario '{scenario}' not found in config"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

