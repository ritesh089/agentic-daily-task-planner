"""
Email Agent Module
Handles email collection and summarization using Gmail API and LLM
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import base64
from typing import Dict
from langchain_ollama import ChatOllama

# Gmail API Scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
                'https://www.googleapis.com/auth/gmail.send']

# ============================================================================
# Email Collector Agent
# ============================================================================

def email_collector_agent(state: Dict) -> Dict:
    """Collects emails from Gmail for the specified time range"""
    print(f"📧 Email Collector: Fetching emails from last {state['time_range_hours']} hours...")
    
    try:
        # OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", GMAIL_SCOPES)
        creds = flow.run_local_server(port=8080)
        service = build('gmail', 'v1', credentials=creds)
        
        # Store credentials and service in state for reuse by other agents
        state['gmail_credentials'] = creds
        state['gmail_service'] = service
        
        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=state['time_range_hours'])
        
        # Fetch messages
        results = service.users().messages().list(userId='me', maxResults=50).execute()
        messages = results.get('messages', [])
        
        def get_body(payload):
            """Extract text body from email payload"""
            if 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    elif 'parts' in part:
                        result = get_body(part)
                        if result:
                            return result
            return "No text content found"
        
        # Filter and collect emails
        collected_emails = []
        for msg in messages:
            message = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = message['payload']['headers']
            date_header = next((h['value'] for h in headers if h['name'] == 'Date'), None)
            
            if date_header:
                try:
                    email_date = parsedate_to_datetime(date_header)
                    if email_date >= cutoff_time:
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                        body = get_body(message['payload'])
                        
                        collected_emails.append({
                            'from': sender,
                            'subject': subject,
                            'body': body[:500],
                            'timestamp': date_header
                        })
                except Exception:
                    continue
        
        state['emails'] = collected_emails
        print(f"✓ Collected {len(collected_emails)} emails")
        
    except Exception as e:
        error_msg = f"Email collection error: {str(e)}"
        state['errors'].append(error_msg)
        state['emails'] = []
        print(f"✗ {error_msg}")
    
    return state

# ============================================================================
# Email Summarizer Agent
# ============================================================================

def email_summarizer_agent(state: Dict) -> Dict:
    """Summarizes collected emails using LLM"""
    print("🤖 Email Summarizer: Generating email summary...")
    
    emails = state['emails']
    
    if not emails:
        state['email_summary'] = "No emails found in the specified time range."
        print("✓ No emails to summarize")
        return state
    
    # Format emails for LLM
    email_text = ""
    for i, email in enumerate(emails, 1):
        email_text += f"\n{i}. From: {email['from']}\n"
        email_text += f"   Subject: {email['subject']}\n"
        email_text += f"   Preview: {email['body'][:300]}...\n"
    
    prompt = f"""You are an email assistant. Provide a concise summary of these emails in 3-4 bullet points.
Focus on the most important and actionable information.

Emails from last {state['time_range_hours']} hours ({len(emails)} total):
{email_text}

Provide a clear, actionable summary:"""
    
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.7)
        response = llm.invoke(prompt)
        state['email_summary'] = response.content
        print("✓ Email summary generated")
    except Exception as e:
        error_msg = f"Email summarization error: {str(e)}"
        state['errors'].append(error_msg)
        state['email_summary'] = f"Error generating summary: {str(e)}"
        print(f"✗ {error_msg}")
    
    return state

