"""
Mock Email Agents
Simulates email collection and summarization without Gmail API
Useful for testing, development, and checkpoint/resume scenarios
"""

import time
from typing import Dict
from datetime import datetime


# ============================================================================
# Mock Data
# ============================================================================

MOCK_EMAILS = [
    {
        'from': 'alice@example.com',
        'subject': 'Urgent: Project deadline moved to Friday',
        'body': 'Hi team, the project deadline has been moved up to this Friday. We need to prioritize the remaining tasks. Can you review the draft by Wednesday?',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'bob@company.com',
        'subject': 'Quick question about the API',
        'body': 'Hey, I noticed the API endpoint is returning a 500 error. Can you take a look when you get a chance? Not urgent but would be good to fix.',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'carol@startup.io',
        'subject': 'Meeting request for next week',
        'body': 'Would you be available for a 30-minute call next Tuesday to discuss the integration? Let me know what time works for you.',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'notifications@github.com',
        'subject': '[Repo] New pull request opened',
        'body': 'A new pull request has been opened on your repository. Please review when you have time.',
        'timestamp': datetime.now().isoformat()
    },
    {
        'from': 'david@partner.com',
        'subject': 'Critical: Production deployment failed',
        'body': 'The production deployment failed at 3am. We need to roll back immediately and investigate. Please respond ASAP!',
        'timestamp': datetime.now().isoformat()
    }
]

MOCK_EMAIL_SUMMARY = """
📧 Email Summary (Last 24 hours):

• **Urgent**: Project deadline moved to Friday - Review draft needed by Wednesday (from alice@example.com)
• **Critical**: Production deployment failed, needs immediate rollback (from david@partner.com)  
• **Issue**: API endpoint returning 500 errors - non-urgent fix needed (from bob@company.com)
• **Meeting**: Request for 30-min call next Tuesday about integration (from carol@startup.io)
• **Notification**: New pull request opened on GitHub repository

**Priority**: 2 urgent/critical items requiring immediate attention.
"""


# ============================================================================
# Mock Configuration
# ============================================================================

class MockEmailConfig:
    """Configuration for mock email agent behavior"""
    
    # Failure simulation
    FAIL_ON_COLLECTION = False  # Simulate collection failure
    FAIL_ON_SUMMARIZATION = False  # Simulate summarization failure
    
    # Timing simulation
    COLLECTION_DELAY = 0.5  # Seconds (simulate API latency)
    SUMMARIZATION_DELAY = 1.0  # Seconds (simulate LLM processing)
    
    # Data simulation
    EMAIL_COUNT = 5  # Number of mock emails to return
    
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
# Mock Email Collector Agent
# ============================================================================

def email_collector_agent(state: Dict) -> Dict:
    """Mock email collector - simulates Gmail API calls"""
    print(f"📧 [MOCK] Email Collector: Fetching emails from last {state['time_range_hours']} hours...")
    
    # Simulate API latency
    time.sleep(MockEmailConfig.COLLECTION_DELAY)
    
    # Simulate failure if configured
    if MockEmailConfig.FAIL_ON_COLLECTION:
        error_msg = "[MOCK] Email collection failed - simulated failure"
        print(f"✗ {error_msg}")
        state['errors'].append(error_msg)
        state['emails'] = []
        raise Exception(error_msg)  # Raise to test checkpoint/resume
    
    try:
        # Return mock emails
        email_count = min(MockEmailConfig.EMAIL_COUNT, len(MOCK_EMAILS))
        collected_emails = MOCK_EMAILS[:email_count]
        
        state['emails'] = collected_emails
        print(f"✓ [MOCK] Collected {len(collected_emails)} emails")
        
        # Simulate storing Gmail service (would be real in production)
        state['gmail_service'] = "mock_service"
        state['gmail_credentials'] = "mock_credentials"
        
    except Exception as e:
        error_msg = f"[MOCK] Email collection error: {str(e)}"
        state['errors'].append(error_msg)
        state['emails'] = []
        print(f"✗ {error_msg}")
    
    return state


# ============================================================================
# Mock Email Summarizer Agent
# ============================================================================

def email_summarizer_agent(state: Dict) -> Dict:
    """Mock email summarizer - simulates LLM summarization"""
    print("🤖 [MOCK] Email Summarizer: Generating email summary...")
    
    emails = state['emails']
    
    if not emails:
        state['email_summary'] = "[MOCK] No emails found in the specified time range."
        print("✓ [MOCK] No emails to summarize")
        return state
    
    # Simulate LLM processing time
    time.sleep(MockEmailConfig.SUMMARIZATION_DELAY)
    
    # Simulate failure if configured
    if MockEmailConfig.FAIL_ON_SUMMARIZATION:
        error_msg = "[MOCK] Email summarization failed - simulated failure"
        print(f"✗ {error_msg}")
        state['errors'].append(error_msg)
        state['email_summary'] = "Error generating summary (mock failure)"
        raise Exception(error_msg)  # Raise to test checkpoint/resume
    
    try:
        # Use pre-generated mock summary
        state['email_summary'] = MOCK_EMAIL_SUMMARY
        print("✓ [MOCK] Email summary generated")
        
    except Exception as e:
        error_msg = f"[MOCK] Email summarization error: {str(e)}"
        state['errors'].append(error_msg)
        state['email_summary'] = f"Error generating summary: {str(e)}"
        print(f"✗ {error_msg}")
    
    return state


# ============================================================================
# Utility Functions
# ============================================================================

def set_mock_emails(emails: list):
    """Replace mock emails with custom test data"""
    global MOCK_EMAILS
    MOCK_EMAILS = emails


def add_mock_email(email: Dict):
    """Add a mock email to the dataset"""
    MOCK_EMAILS.append(email)


def clear_mock_emails():
    """Clear all mock emails"""
    global MOCK_EMAILS
    MOCK_EMAILS = []


def get_mock_email_count():
    """Get current number of mock emails"""
    return len(MOCK_EMAILS)

