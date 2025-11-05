"""
Data Processing Agents
Simple ETL agents for demonstration
"""

from typing import Dict, Any
import json
import os


def data_extractor(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract: Read data from source file
    """
    print("📥 Extractor: Reading source data...")
    
    source_file = state.get('source_file', 'data.json')
    
    try:
        # Check if file exists
        if os.path.exists(source_file):
            with open(source_file, 'r') as f:
                data = json.load(f)
                state['raw_data'] = data
                print(f"✓ Extracted {len(data)} records from {source_file}")
        else:
            # Use sample data if file doesn't exist
            sample_data = [
                {'id': 1, 'name': 'Alice', 'score': 85},
                {'id': 2, 'name': 'Bob', 'score': 92},
                {'id': 3, 'name': 'Charlie', 'score': 78}
            ]
            state['raw_data'] = sample_data
            print(f"ℹ️  File not found, using {len(sample_data)} sample records")
    
    except Exception as e:
        error_msg = f"Extraction error: {str(e)}"
        print(f"✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['raw_data'] = []
    
    return state


def data_transformer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform: Process and clean data
    """
    print("🔄 Transformer: Processing data...")
    
    raw_data = state.get('raw_data', [])
    
    if not raw_data:
        print("ℹ️  No data to transform")
        state['transformed_data'] = []
        return state
    
    try:
        transformed = []
        for record in raw_data:
            # Simple transformation: add grade and uppercase name
            transformed_record = {
                'id': record.get('id'),
                'name': record.get('name', '').upper(),
                'score': record.get('score', 0),
                'grade': _calculate_grade(record.get('score', 0)),
                'processed': True
            }
            transformed.append(transformed_record)
        
        state['transformed_data'] = transformed
        print(f"✓ Transformed {len(transformed)} records")
    
    except Exception as e:
        error_msg = f"Transformation error: {str(e)}"
        print(f"✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['transformed_data'] = []
    
    return state


def data_loader(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load: Write processed data to destination
    """
    print("📤 Loader: Writing output data...")
    
    transformed_data = state.get('transformed_data', [])
    output_file = state.get('output_file', 'output.json')
    
    if not transformed_data:
        state['load_status'] = "No data to load"
        print("ℹ️  No data to load")
        return state
    
    try:
        with open(output_file, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        state['load_status'] = f"Successfully wrote {len(transformed_data)} records to {output_file}"
        state['records_processed'] = len(transformed_data)
        print(f"✓ Loaded {len(transformed_data)} records to {output_file}")
    
    except Exception as e:
        error_msg = f"Load error: {str(e)}"
        print(f"✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['load_status'] = f"Failed: {error_msg}"
        state['records_processed'] = 0
    
    return state


def report_generator(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Report: Generate processing summary
    """
    print("📊 Reporter: Generating report...")
    
    report_lines = [
        "=" * 70,
        "📊 DATA PROCESSING REPORT",
        "=" * 70,
        "",
        f"Source: {state.get('source_file', 'N/A')}",
        f"Output: {state.get('output_file', 'N/A')}",
        f"Records Processed: {state.get('records_processed', 0)}",
        f"Status: {state.get('load_status', 'Unknown')}",
        "",
    ]
    
    # Add sample of transformed data
    if state.get('transformed_data'):
        report_lines.append("Sample Records:")
        report_lines.append("-" * 70)
        for record in state['transformed_data'][:3]:
            report_lines.append(
                f"  • {record['name']}: Score {record['score']} → Grade {record['grade']}"
            )
        if len(state['transformed_data']) > 3:
            report_lines.append(f"  ... and {len(state['transformed_data']) - 3} more")
        report_lines.append("")
    
    # Add errors if any
    if state.get('errors'):
        report_lines.append("⚠️  Errors:")
        report_lines.append("-" * 70)
        for error in state['errors']:
            report_lines.append(f"  • {error}")
        report_lines.append("")
    
    report_lines.append("=" * 70)
    
    state['report'] = '\n'.join(report_lines)
    print("✓ Report generated")
    
    return state


# Helper function
def _calculate_grade(score: int) -> str:
    """Calculate letter grade from score"""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'

