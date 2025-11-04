#!/bin/bash
#
# Test Durability Execution with Mocks
# Verifies checkpoint/resume functionality using mock agents
#

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Durability Test Suite - Mock Agents                           ║${NC}"
echo -e "${BLUE}║        Testing Checkpoint/Resume Functionality                        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
echo -e "${CYAN}[1/6] Checking Prerequisites...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "  Run: python3 -m venv venv"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment exists${NC}"

# Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "  Activating virtual environment..."
    source venv/bin/activate
fi
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check if pytest is installed
if ! venv/bin/python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest not found, installing...${NC}"
    
    # Try to install, if it fails the venv might be broken
    if ! venv/bin/pip install pytest pytest-cov -q 2>/dev/null; then
        echo -e "${RED}✗ Virtual environment appears broken${NC}"
        echo ""
        echo "Your venv has a hardcoded path from another directory."
        echo "Please recreate the virtual environment:"
        echo ""
        echo "  rm -rf venv"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        echo ""
        exit 1
    fi
fi
echo -e "${GREEN}✓ pytest installed${NC}"

echo ""

# ============================================================================
# Step 2: Verify PostgreSQL
# ============================================================================
echo -e "${CYAN}[2/6] Verifying PostgreSQL...${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ docker-compose not found${NC}"
    exit 1
fi

# Check if PostgreSQL container is running
if ! docker ps | grep -q daily-task-planner-postgres; then
    echo -e "${YELLOW}⚠️  PostgreSQL not running, starting...${NC}"
    docker-compose up -d postgres
    echo "  Waiting for PostgreSQL to be ready..."
    
    # Wait for PostgreSQL to accept connections (up to 60 seconds)
    echo -n "  "
    for i in {1..60}; do
        if venv/bin/python -c "import psycopg; psycopg.connect('postgresql://postgres:postgres@localhost:5432/langgraph', connect_timeout=2)" 2>/dev/null; then
            echo ""
            break
        fi
        if [ $i -eq 60 ]; then
            echo ""
            echo -e "${RED}✗ PostgreSQL failed to start after 60 seconds${NC}"
            echo ""
            echo "Troubleshooting:"
            echo "  • Check logs: docker-compose logs postgres"
            echo "  • Check status: docker ps | grep postgres"
            echo "  • Try manually: docker-compose restart postgres"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Verify connection (wait up to 30 seconds if container just started)
echo -n "  Verifying connection"
CONNECTION_OK=false
for i in {1..30}; do
    if venv/bin/python -c "import psycopg; psycopg.connect('postgresql://postgres:postgres@localhost:5432/langgraph', connect_timeout=2)" 2>/dev/null; then
        CONNECTION_OK=true
        echo ""
        break
    fi
    echo -n "."
    sleep 1
done

if [ "$CONNECTION_OK" = true ]; then
    echo -e "${GREEN}✓ PostgreSQL connection successful${NC}"
else
    echo ""
    echo -e "${RED}✗ Cannot connect to PostgreSQL after 30 seconds${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  • Check container: docker ps | grep postgres"
    echo "  • Check logs: docker-compose logs postgres --tail=20"
    echo "  • Test manually: psql postgresql://postgres:postgres@localhost:5432/langgraph"
    echo "  • Restart: docker-compose restart postgres"
    exit 1
fi

echo ""

# ============================================================================
# Step 3: Verify Configuration
# ============================================================================
echo -e "${CYAN}[3/6] Verifying Test Configuration...${NC}"

# Check if mock config exists
if [ ! -f "config/mock_config.yaml" ]; then
    echo -e "${RED}✗ config/mock_config.yaml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Mock configuration exists${NC}"

# Check if durability config exists
if [ ! -f "config/durability_config.yaml" ]; then
    echo -e "${RED}✗ config/durability_config.yaml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Durability configuration exists${NC}"

# Verify mocks are enabled in config
if grep -q "enabled: true" config/mock_config.yaml; then
    echo -e "${GREEN}✓ Mocks are enabled${NC}"
else
    echo -e "${YELLOW}⚠️  Mocks not enabled in config (tests will enable them)${NC}"
fi

# Verify durability is enabled
if grep -q "enabled: true" config/durability_config.yaml; then
    echo -e "${GREEN}✓ Durability is enabled${NC}"
else
    echo -e "${RED}✗ Durability not enabled in config${NC}"
    echo "  Edit config/durability_config.yaml and set enabled: true"
    exit 1
fi

echo ""

# ============================================================================
# Step 4: Setup Database
# ============================================================================
echo -e "${CYAN}[4/6] Setting Up Database Schema...${NC}"

# Check if tables exist, create if needed
if venv/bin/python -c "
import psycopg
try:
    conn = psycopg.connect('postgresql://postgres:postgres@localhost:5432/langgraph', autocommit=True)
    with conn.cursor() as cur:
        cur.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'checkpoints')\")
        exists = cur.fetchone()[0]
        if not exists:
            print('need_setup')
    conn.close()
except Exception as e:
    print(f'error: {e}')
" | grep -q "need_setup"; then
    echo -e "${YELLOW}⚠️  Database tables not found, creating...${NC}"
    if [ -f "framework/setup_postgres.py" ]; then
        venv/bin/python framework/setup_postgres.py
        echo -e "${GREEN}✓ Database schema created${NC}"
    else
        echo -e "${YELLOW}⚠️  setup_postgres.py not found, tests will create schema${NC}"
    fi
else
    echo -e "${GREEN}✓ Database schema exists${NC}"
fi

echo ""

# ============================================================================
# Step 5: Run Tests
# ============================================================================
echo -e "${CYAN}[5/6] Running Durability Tests...${NC}"
echo ""

# Run pytest with detailed output
venv/bin/pytest tests/test_checkpoint_resume.py \
    -v \
    --tb=short \
    --color=yes \
    -ra \
    2>&1

TEST_EXIT_CODE=$?

echo ""

# ============================================================================
# Step 6: Summary
# ============================================================================
echo -e "${CYAN}[6/6] Test Summary${NC}"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✅ ALL TESTS PASSED! ✅                             ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Durability verification complete!${NC}"
    echo ""
    echo "What was tested:"
    echo "  ✅ Checkpoint creation during workflow execution"
    echo "  ✅ Email collection failure and resume"
    echo "  ✅ Slack collection failure and resume"
    echo "  ✅ Summarization failure and resume"
    echo "  ✅ Multiple failure/resume cycles"
    echo "  ✅ Checkpoint data integrity"
    echo "  ✅ Mock data realism"
    echo "  ✅ Performance with mocks"
    echo ""
    echo "Next steps:"
    echo "  • View checkpoints: docker-compose exec postgres psql -U postgres -d langgraph -c 'SELECT * FROM checkpoints LIMIT 5;'"
    echo "  • Run with coverage: pytest tests/ --cov=framework --cov=app --cov-report=html"
    echo "  • Try manual test: python example_mock_test.py"
    echo ""
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                      ❌ TESTS FAILED ❌                                ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  • Check PostgreSQL: docker-compose logs postgres"
    echo "  • Verify configs: cat config/mock_config.yaml config/durability_config.yaml"
    echo "  • Check dependencies: pip list | grep -E 'pytest|langgraph|psycopg'"
    echo "  • Re-run specific test: pytest tests/test_checkpoint_resume.py::TestName::test_name -v"
    echo ""
    exit 1
fi

# Show database stats
echo -e "${BLUE}Database Statistics:${NC}"
CHECKPOINT_COUNT=$(docker-compose exec -T postgres psql -U postgres -d langgraph -t -c "SELECT COUNT(*) FROM checkpoints;" 2>/dev/null | tr -d ' ' || echo "0")
echo "  • Total checkpoints created: $CHECKPOINT_COUNT"

THREAD_COUNT=$(docker-compose exec -T postgres psql -U postgres -d langgraph -t -c "SELECT COUNT(DISTINCT thread_id) FROM checkpoints;" 2>/dev/null | tr -d ' ' || echo "0")
echo "  • Unique workflows tested: $THREAD_COUNT"

echo ""
echo -e "${GREEN}✅ Durability tests completed successfully!${NC}"

