#!/bin/bash

# Start Daily Task Planner with Jaeger Tracing
# This script starts Jaeger and runs the application with tracing enabled

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Starting Daily Task Planner with Observability${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"

# Step 1: Start Jaeger
echo -e "${GREEN}Step 1: Starting Jaeger...${NC}"
if docker-compose ps | grep -q "daily-task-planner-jaeger"; then
    echo -e "${YELLOW}   Jaeger is already running${NC}"
else
    docker-compose up -d
    echo -e "${GREEN}   ✓ Jaeger started${NC}"
    
    # Wait for Jaeger to be ready
    echo -n "   Waiting for Jaeger to be ready"
    for i in {1..30}; do
        if curl -s http://localhost:16686 > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
fi

# Step 2: Check observability config
echo -e "\n${GREEN}Step 2: Checking observability configuration...${NC}"
if grep -q "otlp: true" config/observability_config.yaml; then
    echo -e "${GREEN}   ✓ OTLP exporter is enabled${NC}"
else
    echo -e "${YELLOW}   ⚠️  OTLP exporter is disabled${NC}"
    echo -e "${YELLOW}   To enable tracing, edit config/observability_config.yaml:${NC}"
    echo -e "${YELLOW}   Set 'exporters.otlp: true'${NC}\n"
    read -p "   Enable OTLP now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Enable OTLP in config
        sed -i.bak 's/otlp: false/otlp: true/' config/observability_config.yaml
        echo -e "${GREEN}   ✓ OTLP enabled${NC}"
    fi
fi

# Step 3: Check virtual environment
echo -e "\n${GREEN}Step 3: Checking virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${GREEN}   ✓ Virtual environment found${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}   ⚠️  Virtual environment not found${NC}"
    echo -e "${YELLOW}   Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Step 4: Check dependencies
echo -e "\n${GREEN}Step 4: Checking OpenTelemetry dependencies...${NC}"
if venv/bin/python -c "import opentelemetry" 2>/dev/null; then
    echo -e "${GREEN}   ✓ OpenTelemetry installed${NC}"
else
    echo -e "${YELLOW}   ⚠️  Installing OpenTelemetry dependencies...${NC}"
    venv/bin/pip install -q opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation
    echo -e "${GREEN}   ✓ Dependencies installed${NC}"
fi

# Step 5: Display info
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Ready to run with tracing!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"
echo -e "   Jaeger UI: ${BLUE}http://localhost:16686${NC}"
echo -e "   Service:   ${BLUE}daily-task-planner-agent${NC}\n"

# Step 6: Ask to run or just setup
read -p "Run the application now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${GREEN}Running Daily Task Planner...${NC}\n"
    venv/bin/python main.py
    
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Complete!${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"
    echo -e "View your traces at: ${BLUE}http://localhost:16686${NC}\n"
    echo -e "1. Select service: ${YELLOW}daily-task-planner-agent${NC}"
    echo -e "2. Click ${YELLOW}'Find Traces'${NC}"
    echo -e "3. Explore your workflow execution! 🎉\n"
else
    echo -e "\n${GREEN}Setup complete!${NC}"
    echo -e "Run the application with: ${YELLOW}venv/bin/python main.py${NC}\n"
fi

# Cleanup instruction
echo -e "To stop Jaeger: ${YELLOW}docker-compose down${NC}"

