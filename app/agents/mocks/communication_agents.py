"""
Mock Communication Agents
Simulates email sending without real Gmail API
"""

import time
from typing import Dict


class MockCommunicationConfig:
    """Configuration for mock communication agents"""
    
    FAIL_ON_SEND = False
    SEND_DELAY = 0.2  # Simulate email sending latency
    
    @classmethod
    def enable_send_failure(cls):
        """Enable send failure for testing"""
        cls.FAIL_ON_SEND = True
    
    @classmethod
    def reset(cls):
        """Reset to default (no failures)"""
        cls.FAIL_ON_SEND = False


def email_sender_agent(state: Dict) -> Dict:
    """Mock email sender - simulates sending without Gmail API"""
    print("📤 [MOCK] Email Sender: Preparing to send email...")
    
    prioritized_tasks = state.get('prioritized_tasks', [])
    
    if not prioritized_tasks:
        print("  No tasks to send, skipping email")
        state['email_sent'] = False
        state['email_status'] = "No tasks to send"
        return state
    
    # Simulate email sending delay
    time.sleep(MockCommunicationConfig.SEND_DELAY)
    
    # Simulate failure if configured
    if MockCommunicationConfig.FAIL_ON_SEND:
        error_msg = "[MOCK] Email sending failed - simulated failure"
        print(f"✗ {error_msg}")
        state['errors'].append(error_msg)
        state['email_sent'] = False
        state['email_status'] = "Send failed (mock failure)"
        raise Exception(error_msg)
    
    try:
        # Mock successful send
        state['email_sent'] = True
        state['email_status'] = f"Email sent successfully to mock recipient (mock mode - not actually sent)"
        
        print(f"✓ [MOCK] Email 'sent' successfully (simulated)")
        print(f"   Tasks in email: {len(prioritized_tasks)}")
        
    except Exception as e:
        error_msg = f"[MOCK] Email sending error: {str(e)}"
        state['errors'].append(error_msg)
        state['email_sent'] = False
        state['email_status'] = f"Send failed: {str(e)}"
        print(f"✗ {error_msg}")
    
    return state

