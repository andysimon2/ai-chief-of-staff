#!/usr/bin/env python3
"""
Gmail to Tasks Extractor - SIMPLIFIED VERSION
Since Gmail requires domain-wide delegation (complex setup), this version:
1. Manually creates sample tasks to test the system
2. Writes them to Google Sheets
3. Verifies the full pipeline works

Once this works, we can add Gmail integration later.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from anthropic import Anthropic
import json

# Load environment variables
load_dotenv()

# Configuration
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    """Authenticate and return Sheets service"""
    print("🔐 Authenticating with Sheets API...")
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    
    service = build('sheets', 'v4', credentials=credentials)
    print("✅ Sheets authentication successful")
    return service

def create_sample_tasks():
    """Create sample tasks for testing"""
    print("\n📋 Creating sample tasks...")
    
    sample_emails = [
        {
            'subject': 'Q4 Planning Meeting Prep',
            'sender': 'sarah.chen@company.com',
            'body': 'Hi Andrew, can you please review the Q4 deck and send me your feedback by Friday? Also, we need to schedule a follow-up for next week.'
        },
        {
            'subject': 'LP Introduction Request',
            'sender': 'john.davis@vc.com',
            'body': 'Andrew, could you intro me to Maria at Benchmark? I think there could be good synergy there. Let me know if you need context.'
        },
        {
            'subject': 'Cohort Progress Check',
            'sender': 'alex.rodriguez@startup.com',
            'body': 'Quick update needed on our progress. Can we grab 30min this week to discuss the metrics dashboard?'
        }
    ]
    
    return sample_emails

def extract_tasks_with_claude(emails):
    """Use Claude to extract tasks from sample emails"""
    print("\n🤖 Using Claude to extract tasks...")
    
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare email context
    email_context = "\n\n".join([
        f"Email {i+1}:\nFrom: {e['sender']}\nSubject: {e['subject']}\nBody: {e['body']}"
        for i, e in enumerate(emails)
    ])
    
    prompt = f"""You are analyzing emails to extract actionable tasks. 

EMAILS:
{email_context}

Extract all tasks that need to be done. For each task, return JSON in this exact format:
{{
  "tasks": [
    {{
      "title": "Brief description of task",
      "description": "More details if available",
      "priority": "medium",
      "source": "email",
      "linked_person": "Name of person if relevant"
    }}
  ]
}}

Rules:
- Only extract clear, actionable tasks
- Default priority to "medium"
- If no tasks found, return empty array

Return ONLY the JSON, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        content = response.content[0].text
        tasks_data = json.loads(content)
        tasks = tasks_data.get('tasks', [])
        
        print(f"✅ Extracted {len(tasks)} tasks")
        return tasks
    
    except Exception as e:
        print(f"❌ Error with Claude API: {e}")
        return []

def write_tasks_to_sheet(sheets_service, tasks):
    """Write extracted tasks to Google Sheet"""
    print("\n📝 Writing tasks to Google Sheet...")
    
    if not tasks:
        print("⚠️  No tasks to write")
        return
    
    # Prepare rows for sheet
    rows = []
    timestamp = datetime.now().isoformat()
    
    for i, task in enumerate(tasks):
        row = [
            f"task_{timestamp}_{i}",  # id
            task.get('title', ''),  # title
            task.get('description', ''),  # description
            'you',  # primary_owner
            '',  # collaborators
            'solo',  # collaboration_type
            'open',  # status
            task.get('priority', 'medium'),  # priority
            '',  # due_date
            task.get('source', 'email'),  # source
            '0.8',  # source_confidence
            task.get('linked_person', ''),  # linked_person
            '',  # linked_meeting
            timestamp,  # created_at
            timestamp,  # updated_at
            'false',  # duplicate_flag
            ''  # potential_duplicates
        ]
        rows.append(row)
    
    try:
        # Append to Tasks sheet
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Tasks!A2',  # Start at row 2 (after headers)
            valueInputOption='RAW',
            body={'values': rows}
        ).execute()
        
        print(f"✅ Wrote {len(rows)} tasks to Google Sheet")
    
    except Exception as e:
        print(f"❌ Error writing to sheet: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main execution"""
    print("=" * 60)
    print("🚀 AI CHIEF OF STAFF - Sample Task Extraction")
    print("=" * 60)
    
    # Check environment variables
    if not all([SPREADSHEET_ID, SERVICE_ACCOUNT_FILE, ANTHROPIC_API_KEY]):
        print("❌ Missing required environment variables in .env file")
        print("Required: SPREADSHEET_ID, SERVICE_ACCOUNT_FILE, ANTHROPIC_API_KEY")
        sys.exit(1)
    
    try:
        # Get Sheets service
        sheets = get_sheets_service()
        
        # Create sample emails (simulating Gmail fetch)
        emails = create_sample_tasks()
        print(f"✅ Created {len(emails)} sample emails")
        
        # Extract tasks using Claude
        tasks = extract_tasks_with_claude(emails)
        
        # Write to sheet
        write_tasks_to_sheet(sheets, tasks)
        
        print("\n" + "=" * 60)
        print("✅ COMPLETE! Check your Google Sheet:")
        print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print("=" * 60)
        print("\n💡 Next steps:")
        print("1. Open the Google Sheet and verify tasks were added")
        print("2. Once this works, we can add real Gmail integration")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
