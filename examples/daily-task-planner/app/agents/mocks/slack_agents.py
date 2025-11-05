"""
Mock Slack Agents
Simulates Slack API calls without real credentials
Useful for testing, development, and checkpoint/resume scenarios
"""

import time
from typing import Dict
from datetime import datetime


# ============================================================================
# Mock Data
# ============================================================================

MOCK_SLACK_MESSAGES = [
    {
        'from': 'Alice Chen',
        'channel': 'engineering',
        'type': 'channel',
        'text': 'The staging environment is down. Can someone investigate? @here',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'Bob Smith',
        'channel': 'DM',
        'type': 'dm',
        'text': 'Hey! Quick question about the database schema. Do we need to add an index on the user_id column?',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'Carol Johnson',
        'channel': 'product',
        'type': 'mention',
        'text': '@you Can you join the product sync meeting tomorrow at 2pm? We need your input on the API design.',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'David Lee',
        'channel': 'DM',
        'type': 'dm',
        'text': 'The client is asking about the timeline for feature X. Can you provide an estimate by end of day?',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'Eve Wilson',
        'channel': 'general',
        'type': 'channel',
        'text': 'Reminder: Team lunch on Friday at noon. Please RSVP in the thread.',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'Frank Martinez',
        'channel': 'engineering',
        'type': 'mention',
        'text': '@you I pushed a PR for review. Can you take a look when you get a chance? #2345',
        'timestamp': datetime.now().isoformat()
    }
]

MOCK_SLACK_SUMMARY = """
💬 Slack Summary (Last 24 hours):

**Direct Messages (2)**:
• Bob Smith: Question about database schema indexing
• David Lee: Client asking for timeline estimate by EOD

**Channel Messages (2)**:
• #engineering - Alice Chen: Staging environment is down (@here)
• #general - Eve Wilson: Team lunch reminder for Friday

**Mentions (2)**:
• #product - Carol Johnson: Product sync meeting tomorrow 2pm (API design input needed)
• #engineering - Frank Martinez: PR #2345 ready for review

**Action Items**: 
- Investigate staging outage (urgent)
- Provide client timeline estimate (by EOD)
- Review PR #2345
"""


# ============================================================================
# Mock Configuration
# ============================================================================

class MockSlackConfig:
    """Configuration for mock slack agent behavior"""
    
    # Failure simulation
    FAIL_ON_COLLECTION = False  # Simulate collection failure
    FAIL_ON_SUMMARIZATION = False  # Simulate summarization failure
    
    # Timing simulation
    COLLECTION_DELAY = 0.8  # Seconds (simulate API latency)
    SUMMARIZATION_DELAY = 1.2  # Seconds (simulate LLM processing)
    
    # Data simulation
    MESSAGE_COUNT = 6  # Number of mock messages to return
    INCLUDE_DMS = True
    INCLUDE_CHANNELS = True
    INCLUDE_MENTIONS = True
    
    @classmethod
    def enable_collection_failure(cls):
        """Enable collection failure for testing"""
        cls.FAIL_ON_COLLECTION = True
    
    @classmethod
    def enable_summarization_failure(cls):
        """Enable summarization failure for testing"""
        cls.FAIL_ON_SUMMARIZATION = True
    
    @classmethod
    def reset(cls):
        """Reset to default (no failures)"""
        cls.FAIL_ON_COLLECTION = False
        cls.FAIL_ON_SUMMARIZATION = False


# ============================================================================
# Mock Slack Collector Agent
# ============================================================================

def slack_collector_agent(state: Dict) -> Dict:
    """Mock slack collector - simulates Slack API calls"""
    print(f"💬 [MOCK] Slack Collector: Fetching messages from last {state['time_range_hours']} hours...")
    
    # Simulate API latency
    time.sleep(MockSlackConfig.COLLECTION_DELAY)
    
    # Simulate failure if configured
    if MockSlackConfig.FAIL_ON_COLLECTION:
        error_msg = "[MOCK] Slack collection failed - simulated failure"
        print(f"✗ {error_msg}")
        state['errors'].append(error_msg)
        state['slack_messages'] = []
        raise Exception(error_msg)  # Raise to test checkpoint/resume
    
    try:
        # Filter mock messages based on config
        filtered_messages = []
        for msg in MOCK_SLACK_MESSAGES[:MockSlackConfig.MESSAGE_COUNT]:
            if (msg['type'] == 'dm' and MockSlackConfig.INCLUDE_DMS) or \
               (msg['type'] == 'channel' and MockSlackConfig.INCLUDE_CHANNELS) or \
               (msg['type'] == 'mention' and MockSlackConfig.INCLUDE_MENTIONS):
                filtered_messages.append(msg)
        
        state['slack_messages'] = filtered_messages
        
        # Count by type
        dm_count = sum(1 for m in filtered_messages if m['type'] == 'dm')
        channel_count = sum(1 for m in filtered_messages if m['type'] == 'channel')
        mention_count = sum(1 for m in filtered_messages if m['type'] == 'mention')
        
        print(f"✓ [MOCK] Collected {len(filtered_messages)} messages:")
        print(f"   - {dm_count} DMs")
        print(f"   - {channel_count} channel messages")
        print(f"   - {mention_count} mentions")
        
    except Exception as e:
        error_msg = f"[MOCK] Slack collection error: {str(e)}"
        state['errors'].append(error_msg)
        state['slack_messages'] = []
        print(f"✗ {error_msg}")
    
    return state


# ============================================================================
# Mock Slack Summarizer Agent
# ============================================================================

def slack_summarizer_agent(state: Dict) -> Dict:
    """Mock slack summarizer - simulates LLM summarization"""
    print("🤖 [MOCK] Slack Summarizer: Generating Slack summary...")
    
    slack_messages = state['slack_messages']
    
    if not slack_messages:
        state['slack_summary'] = "[MOCK] No Slack messages found in the specified time range."
        print("✓ [MOCK] No Slack messages to summarize")
        return state
    
    # Simulate LLM processing time
    time.sleep(MockSlackConfig.SUMMARIZATION_DELAY)
    
    # Simulate failure if configured
    if MockSlackConfig.FAIL_ON_SUMMARIZATION:
        error_msg = "[MOCK] Slack summarization failed - simulated failure"
        print(f"✗ {error_msg}")
        state['errors'].append(error_msg)
        state['slack_summary'] = "Error generating summary (mock failure)"
        raise Exception(error_msg)  # Raise to test checkpoint/resume
    
    try:
        # Use pre-generated mock summary
        state['slack_summary'] = MOCK_SLACK_SUMMARY
        print("✓ [MOCK] Slack summary generated")
        
    except Exception as e:
        error_msg = f"[MOCK] Slack summarization error: {str(e)}"
        state['errors'].append(error_msg)
        state['slack_summary'] = f"Error generating summary: {str(e)}"
        print(f"✗ {error_msg}")
    
    return state


# ============================================================================
# Utility Functions
# ============================================================================

def set_mock_messages(messages: list):
    """Replace mock messages with custom test data"""
    global MOCK_SLACK_MESSAGES
    MOCK_SLACK_MESSAGES = messages


def add_mock_message(message: Dict):
    """Add a mock message to the dataset"""
    MOCK_SLACK_MESSAGES.append(message)


def clear_mock_messages():
    """Clear all mock messages"""
    global MOCK_SLACK_MESSAGES
    MOCK_SLACK_MESSAGES = []


def get_mock_message_count():
    """Get current number of mock messages"""
    return len(MOCK_SLACK_MESSAGES)

