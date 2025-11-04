#!/bin/bash

# Multi-Agent Email & Slack Summarizer Runner with Automatic Cleanup
# This script starts Ollama, runs the multi-agent summarizer, and cleans up everything

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track what we started
OLLAMA_STARTED=false
OLLAMA_PID=""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    
    # Stop Ollama if we started it
    if [ "$OLLAMA_STARTED" = true ] && [ ! -z "$OLLAMA_PID" ]; then
        echo -e "${YELLOW}Stopping Ollama (PID: $OLLAMA_PID)...${NC}"
        kill -TERM "$OLLAMA_PID" 2>/dev/null || true
        wait "$OLLAMA_PID" 2>/dev/null || true
        echo -e "${GREEN}✓ Ollama stopped${NC}"
    fi
    
    # Deactivate virtual environment
    deactivate 2>/dev/null || true
    
    echo -e "${GREEN}✨ Cleanup complete!${NC}"
}

# Set trap to ensure cleanup runs on exit
trap cleanup EXIT INT TERM

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Starting Multi-Agent Communication Summarizer...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}\n"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Error: Ollama is not installed.${NC}"
    echo "Please install Ollama from: https://ollama.ai"
    exit 1
fi

# Check if Ollama is already running
if pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}ℹ️  Ollama is already running (will not stop it at the end)${NC}"
    OLLAMA_STARTED=false
else
    echo -e "${GREEN}Starting Ollama...${NC}"
    # Start Ollama in the background
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!
    OLLAMA_STARTED=true
    
    # Wait for Ollama to be ready
    echo -n "Waiting for Ollama to start"
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
fi

# Check if llama3 or llama3.2 model is available
echo -e "${GREEN}Checking for llama3 model...${NC}"
if ! ollama list | grep -q "llama3"; then
    echo -e "${RED}Error: llama3 or llama3.2 model not found.${NC}"
    echo "Please install it first: ollama pull llama3.2"
    exit 1
fi
echo -e "${GREEN}✓ llama3 model found${NC}"

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
cd "$(dirname "$0")"
source venv/bin/activate

# Check if required credential files exist
echo -e "${GREEN}Checking credentials...${NC}"

if [ ! -f "credentials.json" ]; then
    echo -e "${RED}Error: credentials.json not found!${NC}"
    echo "Please add your Google Cloud credentials file."
    exit 1
fi
echo -e "${GREEN}✓ Gmail credentials found${NC}"

if [ ! -f "slack_credentials.json" ]; then
    echo -e "${YELLOW}⚠️  Warning: slack_credentials.json not found!${NC}"
    echo -e "${YELLOW}   Slack collection will be skipped.${NC}"
    echo -e "${YELLOW}   To enable Slack: cp slack_credentials.json.example slack_credentials.json${NC}"
    echo -e "${YELLOW}   and add your Slack user token.${NC}\n"
else
    echo -e "${GREEN}✓ Slack credentials found${NC}"
fi

# Run the multi-agent summarizer
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🤖 Running Multi-Agent Workflow...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}\n"

python main.py

echo -e "\n${GREEN}✅ Multi-agent workflow completed!${NC}\n"

# Cleanup will be called automatically via trap

