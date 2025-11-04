"""
Task Agent Module
Handles task extraction and prioritization from emails and Slack messages
"""

from typing import Dict, List
from langchain_ollama import ChatOllama
import json

# ============================================================================
# Task Extractor Agent
# ============================================================================

def task_extractor_agent(state: Dict) -> Dict:
    """Extracts actionable tasks from emails and Slack messages"""
    print("📋 Task Extractor: Identifying actionable items...")
    
    emails = state['emails']
    slack_messages = state['slack_messages']
    
    if not emails and not slack_messages:
        state['tasks'] = []
        print("✓ No messages to extract tasks from")
        return state
    
    # Format all messages for LLM
    messages_text = ""
    
    # Add emails
    if emails:
        messages_text += "\n=== EMAILS ===\n"
        for i, email in enumerate(emails, 1):
            messages_text += f"\nEmail {i}:\n"
            messages_text += f"From: {email['from']}\n"
            messages_text += f"Subject: {email['subject']}\n"
            messages_text += f"Content: {email['body'][:400]}...\n"
    
    # Add Slack messages
    if slack_messages:
        messages_text += "\n=== SLACK MESSAGES ===\n"
        for i, msg in enumerate(slack_messages, 1):
            messages_text += f"\nMessage {i} [{msg['type']}]:\n"
            messages_text += f"From: {msg['from']}\n"
            if 'channel' in msg:
                messages_text += f"Channel: {msg['channel']}\n"
            messages_text += f"Content: {msg['text'][:400]}...\n"
    
    prompt = f"""You are a task extraction assistant. Analyze the following emails and Slack messages and extract ALL actionable tasks, requests, and to-dos.

For each task, identify:
1. What needs to be done (clear, concise description)
2. Who requested it (person's name)
3. The source (Email or Slack)
4. Any mentioned deadline or urgency indicators

Messages to analyze:
{messages_text}

Return your response as a JSON array of tasks with this structure:
[
  {{
    "task": "Clear description of what needs to be done",
    "requested_by": "Person's name",
    "source": "Email" or "Slack",
    "urgency_indicators": ["deadline: Friday", "urgent", "asap", etc],
    "context": "Brief context or reason"
  }}
]

Only include actual actionable tasks - ignore informational messages, promotions, and automated notifications.
If there are no actionable tasks, return an empty array: []

Return ONLY the JSON array, nothing else."""
    
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.3)  # Lower temp for structured output
        response = llm.invoke(prompt)
        
        # Parse JSON response
        response_text = response.content.strip()
        
        # Handle empty or non-JSON responses
        if not response_text or response_text == "":
            state['tasks'] = []
            print(f"✓ No actionable tasks found in messages")
            return state
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Try to find JSON array if not at start
        if not response_text.startswith('['):
            # Look for [ to ] pattern
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            else:
                # No valid JSON found
                print(f"⚠️  LLM did not return valid JSON format. Using empty task list.")
                state['tasks'] = []
                return state
        
        tasks = json.loads(response_text)
        
        # Validate structure
        if not isinstance(tasks, list):
            tasks = []
        
        state['tasks'] = tasks
        print(f"✓ Extracted {len(tasks)} actionable tasks")
        
    except json.JSONDecodeError as e:
        error_msg = f"Task extraction parsing error: {str(e)}"
        print(f"⚠️  {error_msg}")
        print(f"   LLM response was not valid JSON. No tasks extracted.")
        state['tasks'] = []
        # Don't add to errors - this is expected sometimes
    except Exception as e:
        error_msg = f"Task extraction error: {str(e)}"
        state['errors'].append(error_msg)
        state['tasks'] = []
        print(f"✗ {error_msg}")
    
    return state

# ============================================================================
# Task Prioritizer Agent
# ============================================================================

def task_prioritizer_agent(state: Dict) -> Dict:
    """Prioritizes tasks based on urgency, importance, and deadlines"""
    print("🎯 Task Prioritizer: Ranking tasks by priority...")
    
    tasks = state['tasks']
    
    if not tasks:
        state['prioritized_tasks'] = []
        print("✓ No tasks to prioritize")
        return state
    
    # Format tasks for LLM
    tasks_text = ""
    for i, task in enumerate(tasks, 1):
        tasks_text += f"\nTask {i}:\n"
        tasks_text += f"  Description: {task['task']}\n"
        tasks_text += f"  Requested by: {task['requested_by']}\n"
        tasks_text += f"  Source: {task['source']}\n"
        tasks_text += f"  Urgency indicators: {', '.join(task.get('urgency_indicators', ['none']))}\n"
        tasks_text += f"  Context: {task.get('context', 'N/A')}\n"
    
    prompt = f"""You are a task prioritization assistant. Analyze these tasks and assign each one a priority level and ranking.

Priority Levels:
- P0 (Critical): Urgent deadlines, blocks others, executive requests
- P1 (High): Important deadlines this week, team dependencies
- P2 (Medium): Important but not urgent, deadlines next week
- P3 (Low): Nice to have, no deadline, informational

Tasks to prioritize:
{tasks_text}

For each task, determine:
1. Priority level (P0, P1, P2, or P3)
2. Reasoning for the priority
3. Recommended action

Return your response as a JSON array ordered from highest to lowest priority:
[
  {{
    "task": "Original task description",
    "requested_by": "Person's name",
    "source": "Email or Slack",
    "priority": "P0, P1, P2, or P3",
    "priority_reason": "Brief explanation of why this priority",
    "recommended_action": "Specific next step to take",
    "estimated_effort": "Quick (< 1h), Medium (1-4h), or Large (> 4h)"
  }}
]

Return ONLY the JSON array, nothing else."""
    
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.3)
        response = llm.invoke(prompt)
        
        # Parse JSON response
        response_text = response.content.strip()
        
        # Handle empty responses
        if not response_text:
            # Fallback: use default priorities
            state['prioritized_tasks'] = [
                {**task, 'priority': 'P2', 'priority_reason': 'Default priority', 
                 'recommended_action': 'Review and take action', 'estimated_effort': 'Medium'}
                for task in tasks
            ]
            print(f"⚠️  Empty LLM response - using default priorities")
            return state
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Try to find JSON array if not at start
        if not response_text.startswith('['):
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            else:
                # No valid JSON - use defaults
                state['prioritized_tasks'] = [
                    {**task, 'priority': 'P2', 'priority_reason': 'Default priority', 
                     'recommended_action': 'Review and take action', 'estimated_effort': 'Medium'}
                    for task in tasks
                ]
                print(f"⚠️  LLM did not return valid JSON - using default priorities")
                return state
        
        prioritized = json.loads(response_text)
        
        # Validate structure
        if not isinstance(prioritized, list):
            prioritized = []
        
        state['prioritized_tasks'] = prioritized
        
        # Count by priority
        priority_counts = {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0}
        for task in prioritized:
            p = task.get('priority', 'P3')
            priority_counts[p] = priority_counts.get(p, 0) + 1
        
        print(f"✓ Prioritized {len(prioritized)} tasks")
        print(f"   P0: {priority_counts['P0']}, P1: {priority_counts['P1']}, P2: {priority_counts['P2']}, P3: {priority_counts['P3']}")
        
    except json.JSONDecodeError as e:
        error_msg = f"Task prioritization parsing error: {str(e)}"
        print(f"⚠️  {error_msg} - using default priorities")
        # Fallback: just pass through tasks with default priority
        state['prioritized_tasks'] = [
            {**task, 'priority': 'P2', 'priority_reason': 'Default priority', 
             'recommended_action': 'Review and take action', 'estimated_effort': 'Medium'}
            for task in tasks
        ]
        # Don't add to errors - fallback is acceptable
    except Exception as e:
        error_msg = f"Task prioritization error: {str(e)}"
        state['errors'].append(error_msg)
        state['prioritized_tasks'] = []
        print(f"✗ {error_msg}")
    
    return state

