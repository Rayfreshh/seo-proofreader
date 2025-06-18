# SEO Proofreader Tool

An automated tool that analyzes SEO content (cost pages and city pages) against comprehensive predefined checklists and provides actionable improvement suggestions.

## Overview

This SEO Proofreader tool evaluates content for SEO compliance using detailed checklists specifically designed for cost pages (focusing on pricing information) and city pages (focusing on local services). It reads content from Google Docs, extracts keywords from Google Sheets, and generates comprehensive reports with scores and targeted improvement suggestions to replace manual proofreading workflows.

## Features

- **Comprehensive Evaluation**: Evaluates 30+ checklist items across multiple categories
- **Google Integration**: Seamless Google Docs and Sheets integration
- **Intelligent Page Detection**: Automatic detection of page type (cost or city)
- **Detailed Scoring**: 10-point scoring system for each checklist item
- **Visual Reports**: Markdown reports with tables, charts, and visual indicators
- **Targeted Suggestions**: Up to 5 specific improvement recommendations
- **Professional Checklists**: Based on real SEO team workflows and requirements

## Evaluation Categories

### Cost Pages
- Page Title & Meta Description optimization
- Headings & Keyword Research compliance
- Internal Linking strategy
- General Quality checks
- Tone of Voice & Readability assessment
- Formatting & Specific Guidelines adherence
- Cost Page Specific features (tables, pricing focus)
- FAQ Section quality

### City Pages
- City-specific Headings & Keywords
- Local Internal Linking
- City-focused General Quality
- Local Business Advantages
- City-Specific Information
- District/Area mentions
- Cost Information inclusion

## Requirements

- Python 3.8+
- Google API credentials with access to Google Docs and Sheets APIs
- OpenAI API key (optional - fallback methods available)

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/seo-proofreader.git
   cd seo-proofreader

2. Install the required packages
   ```bash   
   pip install -r requirements.txt
   ```

3. Set up Google API credentials
   ```bash
   OPENAI_API_KEY="your-openai-api-key"
   GOOGLE_CREDENTIALS='{"client_id":"...","client_secret":"...","refresh_token":"..."}'
   ```

4. Google Drive API setup:

Configure Google API credentials:

Go to Google Cloud Console
Create a new project
Enable the Google Docs API and Google Sheets API
Create OAuth credentials (Desktop app)
Download the credentials JSON file
Save as token.json in the project directory:
```bash
{
  "client_id": "YOUR_CLIENT_ID_HERE",
  "client_secret": "YOUR_CLIENT_SECRET_HERE",
  "refresh_token": "YOUR_REFRESH_TOKEN_HERE",
  "token_uri": "https://oauth2.googleapis.com/token",
  "scopes": ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/spreadsheets.readonly"]
}
```

## Usage
Run the proofreader with a Google Document ID and its corresponding keyword sheet:

```bash
python Seo_proofreader.py --doc_id DOCUMENT_ID --keywords_sheet SHEET_ID
```
Optionally specify the page type:
```bash
python Seo_proofreader.py --doc_id DOCUMENT_ID --keywords_sheet SHEET_ID --page_type cost
```

Finding Document and Sheet IDs
Google Docs: Extract from URL https://docs.google.com/document/d/[DOCUMENT_ID]/edit
Google Sheets: Extract from URL https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit

## Parameters
- `--doc_id`: The ID of the Google Doc to analyze (required)
- `--keywords_sheet`: The ID of the Google Sheet containing keywords (required)
- `--page_type`: Force the page type - either "cost" or "city" (optional, auto-detected if not provided)

## Output
The tool will:

- Generate a Markdown report with the checklist scores
- Provide up to 5 improvement suggestions
- Save the report to a file named `report_DOCUMENT_ID.md`

## Test Documents
The repository includes google sheets for testing purposes:
