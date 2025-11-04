#!/bin/bash
#
# Run Checkpoint/Resume Tests
# Tests durable execution with mock agents and simulated failures
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Checkpoint/Resume Test Suite                               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo -e "Activating venv..."
    source venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found${NC}"
    echo "Installing pytest..."
    pip install pytest pytest-cov
fi

# Check if PostgreSQL is running
echo -e "${BLUE}Checking PostgreSQL...${NC}"
if docker ps | grep -q daily-task-planner-postgres; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL not running${NC}"
    echo "Starting PostgreSQL..."
    docker-compose up -d postgres
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Verify database connection
if venv/bin/python -c "import psycopg; psycopg.connect('postgresql://postgres:postgres@localhost:5432/langgraph', connect_timeout=3)" 2>/dev/null; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Cannot connect to database${NC}"
    echo "Make sure PostgreSQL is running: docker-compose up -d postgres"
    exit 1
fi

echo ""
echo -e "${BLUE}Running tests...${NC}"
echo ""

# Parse command line arguments
TEST_ARGS="$@"

# If no arguments provided, run all tests
if [ -z "$TEST_ARGS" ]; then
    TEST_ARGS="tests/ -v"
fi

# Run pytest
pytest $TEST_ARGS

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                      ✅ All Tests Passed!                              ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
else
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                      ❌ Tests Failed                                   ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Test Options:${NC}"
echo "  ./run_tests.sh                              # Run all tests"
echo "  ./run_tests.sh -k test_email                # Run specific test"
echo "  ./run_tests.sh -m integration               # Run integration tests only"
echo "  ./run_tests.sh -m 'not slow'                # Skip slow tests"
echo "  ./run_tests.sh --cov=framework --cov=app    # Run with coverage"
echo ""

