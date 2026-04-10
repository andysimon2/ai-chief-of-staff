#!/usr/bin/env python3
"""
Extract tasks and WaitingOn items from Gmail
"""

import os
import sys
import json
import pickle
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.discovery import build as sheets_build
import anthropic

# Load environment
load_dotenv()

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

def authenticate_gmail():
    """Authenticate with Gmail API"""
    creds = None
    token_path = 'credentials/gmail_token.pickle'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials/gmail_credentials.json', GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def get_sheets_service():
    """Authenticate and return Sheets service"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SHEETS_SCOPES
    )
    return sheets_build('sheets', 'v4', credentials=credentials)

def get_emails_last_24h(service):
    """Fetch emails from last 24 hours"""
    yesterday = datetime.now() - timedelta(days=1)
    query = f'after:{int(yesterday.timestamp())}'
    
    print(f"📧 Fetching emails from last 24 hours...")
    
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=100
    ).execute()
    
    messages = results.get('messages', [])
    print(f"✅ Found {len(messages)} emails")
    
    emails = []
    for msg in messages:
        message = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()
        
        # Extract headers
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract body
        body = ""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        emails.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'body': body[:2000]  # Limit to first 2000 chars
        })
    
    return emails

def extract_tasks_with_claude(emails):
    """Use Claude to extract tasks and WaitingOn items"""
    
    if not emails:
        return {'tasks': [], 'waiting_on': []}
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare email summary
    email_text = "\n\n".join([
        f"From: {e['from']}\nSubject: {e['subject']}\nDate: {e['date']}\n\n{e['body']}"
        for e in emails[:20]  # Limit to 20 most recent
    ])
    
    prompt = f"""Analyze these emails and extract:
1. TASKS - things I need to do
2. WAITING_ON - things others committed to send me

For each task:
- title: brief description
- description: more detail if available
- linked_person: who it's related to
- priority: high/medium/low (default: medium)
- source_confidence: 0.0-1.0 based on clarity

For each waiting_on:
- description: what they owe me
- person: who owes it
- source_confidence: 0.0-1.0 based on clarity

Return ONLY valid JSON with this structure:
{{
  "tasks": [
    {{"title": "...", "description": "...", "linked_person": "...", "priority": "medium", "source_confidence": 0.8}}
  ],
  "waiting_on": [
    {{"description": "...", "person": "...", "source_confidence": 0.9}}
  ]
}}

EMAILS:
{email_text}
"""
    
    print("\n🤖 Using Claude to extract tasks and waiting_on items...")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse response
    response_text = response.content[0].text
    
    # Extract JSON from response
    try:
        # Try to find JSON in the response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        json_str = response_text[start:end]
        result = json.loads(json_str)
    except:
        print("⚠️  Could not parse Claude response as JSON")
        result = {'tasks': [], 'waiting_on': []}
    
    print(f"✅ Extracted {len(result.get('tasks', []))} tasks and {len(result.get('waiting_on', []))} waiting_on items")
    
    return result

def write_to_sheets(sheets_service, data):
    """Write tasks and waiting_on to Google Sheets"""
    
    timestamp = datetime.now().isoformat()
    
    # Write tasks
    if data['tasks']:
        print(f"\n📝 Writing {len(data['tasks'])} tasks to Google Sheets...")
        
        task_rows = []
        for i, task in enumerate(data['tasks'], 1):
            task_id = f"EMAIL_{timestamp}_{i}"
            task_rows.append([
                task_id,
                task.get('title', ''),
                task.get('description', ''),
                'you',  # primary_owner
                '',  # collaborators
                'solo',  # collaboration_type
                'open',  # status
                task.get('priority', 'medium'),
                '',  # due_date
                'email',  # source
                str(task.get('source_confidence', 0.7)),
                task.get('linked_person', ''),
                '',  # linked_meeting
                timestamp,  # created_at
                timestamp,  # updated_at
                'FALSE',  # duplicate_flag
                ''  # potential_duplicates
            ])
        
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Tasks!A:Q',
            valueInputOption='RAW',
            body={'values': task_rows}
        ).execute()
        
        print(f"✅ Wrote {len(task_rows)} tasks")
    
    # Write waiting_on
    if data['waiting_on']:
        print(f"\n⏳ Writing {len(data['waiting_on'])} waiting_on items to Google Sheets...")
        
        waiting_rows = []
        for i, item in enumerate(data['waiting_on'], 1):
            waiting_id = f"WAIT_{timestamp}_{i}"
            waiting_rows.append([
                waiting_id,
                item.get('description', ''),
                item.get('person', ''),
                '',  # related_task
                'email',  # source
                str(item.get('source_confidence', 0.7)),
                timestamp,  # last_activity_date
                'waiting',  # status
                '',  # completed_at
                '',  # completion_note
                'FALSE',  # deliverable_matched
                '0',  # days_waiting (will be calculated)
                'FALSE'  # escalation_flag
            ])
        
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='WaitingOn!A:M',
            valueInputOption='RAW',
            body={'values': waiting_rows}
        ).execute()
        
        print(f"✅ Wrote {len(waiting_rows)} waiting_on items")

def main():
    """Main execution"""
    
    print("=" * 60)
    print("📧 GMAIL → TASKS EXTRACTION")
    print("=" * 60)
    
    # Authenticate
    gmail_service = authenticate_gmail()
    sheets_service = get_sheets_service()
    
    # Fetch emails
    emails = get_emails_last_24h(gmail_service)
    
    if not emails:
        print("\n✅ No emails in last 24 hours")
        return
    
    # Extract tasks
    extracted = extract_tasks_with_claude(emails)
    
    # Write to sheets
    write_to_sheets(sheets_service, extracted)
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
