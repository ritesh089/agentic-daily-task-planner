"""
Pytest Configuration for Mock-based Checkpoint Tests
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_db: marks tests that require PostgreSQL"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests"""
    print("\n" + "="*70)
    print("Setting up test environment...")
    print("="*70)
    
    # Check if PostgreSQL is running
    import psycopg
    try:
        conn = psycopg.connect(
            "postgresql://postgres:postgres@localhost:5432/langgraph",
            connect_timeout=3
        )
        conn.close()
        print("✓ PostgreSQL connection successful")
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        print("   Some tests will be skipped")
    
    print("="*70)
    yield
    print("\n" + "="*70)
    print("Test environment cleanup complete")
    print("="*70)

