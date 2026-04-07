#!/usr/bin/env python3
"""
Daily Brief Generator
Reads tasks from Google Sheets and generates a morning brief
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Configuration
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    """Authenticate and return Sheets service"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=credentials)

def read_tasks(sheets_service):
    """Read all tasks from the Tasks sheet"""
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Tasks!A2:Q'  # All columns, starting from row 2
        ).execute()
        
        rows = result.get('values', [])
        
        # Parse into task objects
        tasks = []
        for row in rows:
            # Pad row to ensure we have all 17 columns
            row = row + [''] * (17 - len(row))
            
            task = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'primary_owner': row[3],
                'collaborators': row[4],
                'collaboration_type': row[5],
                'status': row[6],
                'priority': row[7],
                'due_date': row[8],
                'source': row[9],
                'source_confidence': row[10],
                'linked_person': row[11],
                'linked_meeting': row[12],
                'created_at': row[13],
                'updated_at': row[14],
                'duplicate_flag': row[15],
                'potential_duplicates': row[16]
            }
            tasks.append(task)
        
        return tasks
    
    except Exception as e:
        print(f"❌ Error reading tasks: {e}")
        return []

def generate_brief(tasks):
    """Generate the daily brief from tasks"""
    
    # Get current date
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    
    # Filter tasks
    open_tasks = [t for t in tasks if t['status'] == 'open']
    high_priority = [t for t in open_tasks if t['priority'] == 'high']
    medium_priority = [t for t in open_tasks if t['priority'] == 'medium']
    
    # Build the brief
    brief = []
    brief.append("=" * 60)
    brief.append(f"📅 DAILY BRIEF - {date_str}")
    brief.append("=" * 60)
    brief.append("")
    
    # Top Tasks Section
    brief.append("🎯 TOP TASKS")
    brief.append("")
    
    if high_priority:
        brief.append("High Priority:")
        for i, task in enumerate(high_priority, 1):
            person = f" (from {task['linked_person']})" if task['linked_person'] else ""
            brief.append(f"  {i}. {task['title']}{person}")
        brief.append("")
    
    if medium_priority:
        brief.append("Medium Priority:")
        for i, task in enumerate(medium_priority[:3], 1):  # Show max 3
            person = f" (from {task['linked_person']})" if task['linked_person'] else ""
            brief.append(f"  {i}. {task['title']}{person}")
        brief.append("")
    
    if not high_priority and not medium_priority:
        brief.append("  ✅ No open tasks! You're all caught up.")
        brief.append("")
    
    # Summary Stats
    brief.append("📊 SUMMARY")
    brief.append("")
    brief.append(f"  • Total open tasks: {len(open_tasks)}")
    brief.append(f"  • High priority: {len(high_priority)}")
    brief.append(f"  • Medium priority: {len(medium_priority)}")
    brief.append("")
    
    # Tasks by Person
    people = {}
    for task in open_tasks:
        person = task['linked_person'] or 'Unknown'
        if person not in people:
            people[person] = []
        people[person].append(task['title'])
    
    if len(people) > 1:  # Only show if multiple people
        brief.append("👥 TASKS BY PERSON")
        brief.append("")
        for person, task_list in sorted(people.items()):
            if person != 'Unknown':
                brief.append(f"  • {person}: {len(task_list)} task(s)")
        brief.append("")
    
    # Footer
    brief.append("=" * 60)
    brief.append("💡 View full sheet:")
    brief.append(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    brief.append("=" * 60)
    
    return "\n".join(brief)

def main():
    """Main execution"""
    
    # Check environment variables
    if not all([SPREADSHEET_ID, SERVICE_ACCOUNT_FILE]):
        print("❌ Missing required environment variables")
        sys.exit(1)
    
    try:
        # Get Sheets service
        sheets = get_sheets_service()
        
        # Read tasks
        print("📖 Reading tasks from Google Sheets...")
        tasks = read_tasks(sheets)
        
        if not tasks:
            print("⚠️  No tasks found in sheet")
            print("\n📧 DAILY BRIEF - No tasks to show")
            return
        
        print(f"✅ Found {len(tasks)} total tasks\n")
        
        # Generate and display brief
        brief = generate_brief(tasks)
        print(brief)
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
