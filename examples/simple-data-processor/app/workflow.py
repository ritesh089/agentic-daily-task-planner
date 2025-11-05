"""
Simple Data Processor Workflow
Demonstrates a basic ETL (Extract, Transform, Load) pattern
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import START, END
from framework import ObservableStateGraph

# Import agents
from app.agents.processor_agents import (
    data_extractor,
    data_transformer,
    data_loader,
    report_generator
)


# ============================================================================
# State Definition
# ============================================================================

class DataProcessorState(TypedDict):
    """State for data processing workflow"""
    
    # Configuration
    source_file: str
    output_file: str
    
    # Processing stages
    raw_data: List[Dict[str, Any]]
    transformed_data: List[Dict[str, Any]]
    load_status: str
    
    # Results
    report: str
    records_processed: int
    
    # Error tracking
    errors: List[str]


# ============================================================================
# Workflow Builder
# ============================================================================

def build_workflow():
    """
    Builds a simple ETL workflow
    
    ETL Flow:
    1. Extract - Read data from source
    2. Transform - Process and clean data
    3. Load - Write to destination
    4. Report - Generate processing report
    
    Returns:
        Uncompiled workflow (framework adds checkpointer)
    """
    
    # Create observable workflow
    workflow = ObservableStateGraph(DataProcessorState)
    
    # Add nodes (each is auto-instrumented)
    workflow.add_node("extract", data_extractor)
    workflow.add_node("transform", data_transformer)
    workflow.add_node("load", data_loader)
    workflow.add_node("report", report_generator)
    
    # Define linear flow
    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "transform")
    workflow.add_edge("transform", "load")
    workflow.add_edge("load", "report")
    workflow.add_edge("report", END)
    
    # Return uncompiled (framework adds checkpointer)
    return workflow

