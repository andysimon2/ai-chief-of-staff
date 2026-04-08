# AI Chief of Staff

Personal AI operating system for automated task management, daily briefings, and relationship tracking.

## What It Does

- **Task Extraction**: Analyzes emails and extracts actionable tasks
- **Daily Briefs**: Generates morning briefs with prioritized tasks
- **Automated Scheduling**: Runs every weekday at 7am EST via GitHub Actions
- **Smart Storage**: Google Sheets database with 6 tabs

## Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud service account
- Anthropic API key
- GitHub repository

### Setup

1. Install dependencies:
pip3 install google-api-python-client google-auth anthropic python-dotenv --break-system-packages

2. Configure `.env` file with your credentials

3. Run scripts:
   - `python3 scripts/gmail_to_tasks.py` - Extract tasks
   - `python3 scripts/daily_brief.py` - Generate brief

## Links

- **Google Sheet**: https://docs.google.com/spreadsheets/d/12BS5pQmHjJcfxv92BymwsQehUwF-aiyNX2sXkaA4CEs
- **GitHub**: https://github.com/andysimon2/ai-chief-of-staff

## Architecture

- `scripts/gmail_to_tasks.py` - Email → Tasks extraction
- `scripts/daily_brief.py` - Morning brief generator
- `.github/workflows/daily-brief.yml` - Automation (7am EST weekdays)

## Roadmap

**V1 (Current):**
- ✅ Google Sheets integration
- ✅ Task extraction
- ✅ Daily brief generation
- ✅ GitHub Actions automation

**V2 (Planned):**
- Email delivery
- Real Gmail integration
- Calendar integration
- WaitingOn tracking
- Weekly summaries
