"""
Application Configuration
"""

from typing import Dict, Any


def get_initial_state() -> Dict[str, Any]:
    """
    Return initial state for data processor workflow
    """
    return {
        'source_file': 'input_data.json',
        'output_file': 'output_data.json',
        'raw_data': [],
        'transformed_data': [],
        'load_status': '',
        'report': '',
        'records_processed': 0,
        'errors': []
    }


def get_app_config() -> Dict[str, Any]:
    """
    App-specific configuration
    """
    return {
        'name': 'simple-data-processor',
        'version': '1.0.0',
        'description': 'Simple ETL workflow demonstrating framework usage'
    }

