#!/bin/bash
#
# Fix Virtual Environment
# Recreates venv when it has wrong Python interpreter path
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Fixing Virtual Environment                                          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if venv exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Removing old virtual environment...${NC}"
    rm -rf venv
    echo -e "${GREEN}✓ Old venv removed${NC}"
else
    echo -e "${YELLOW}No existing venv found${NC}"
fi

echo ""
echo -e "${BLUE}Creating new virtual environment...${NC}"

# Create new venv
if ! python3 -m venv venv; then
    echo -e "${RED}✗ Failed to create virtual environment${NC}"
    echo "  Make sure python3 is installed: python3 --version"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment created${NC}"

echo ""
echo -e "${BLUE}Installing dependencies...${NC}"

# Activate and install
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip -q

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Virtual Environment Fixed!                                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Virtual environment recreated successfully!"
echo ""
echo "To activate it:"
echo "  source venv/bin/activate"
echo ""
echo "To run durability tests:"
echo "  ./test_durability.sh"
echo ""

