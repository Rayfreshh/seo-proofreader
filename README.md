# SEO Proofreader Tool

An automated tool that analyzes SEO content (cost pages and city pages) against predefined checklists and provides improvement suggestions.

## Overview

This SEO Proofreader tool evaluates content for SEO compliance, differentiating between cost pages (focusing on pricing information) and city pages (focusing on local services). It reads content from Google Docs, extracts keywords from Google Sheets, and generates a comprehensive report with scores and improvement suggestions.

## Features

- Google Docs and Google Sheets integration
- Automatic detection of page type (cost or city)
- SEO checklist evaluation using OpenAI's API
- Fallback evaluation methods when API is unavailable
- Detailed scoring and improvement suggestions
- Comprehensive Markdown report generation

## Requirements

- Python 3.8+
- Google API credentials with access to Google Docs and Sheets APIs
- OpenAI API key

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/seo-proofreader.git
   cd seo-proofreader
   ```

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

Go to Google Cloud Console
Create a new project
Enable the Google Docs API and Google Sheets API
Create OAuth credentials (Desktop app)
Download the credentials JSON file
Either set the environment variable:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
   or place the JSON file in the project directory.

## Usage
Run the proofreader with a Google Document ID and its corresponding keyword sheet:
Run the proofreader with a Google Document ID and its corresponding keyword sheet:
```bash
python Seo_proofreader.py --doc_id DOCUMENT_ID --keywords_sheet SHEET_ID
```
Optionally specify the page type:
```bash
python Seo_proofreader.py --doc_id DOCUMENT_ID --keywords_sheet SHEET_ID --page_type cost
```

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
The repository includes sample reports generated for the test documents:

- `report_cost_page_1.md`
- `report_cost_page_2.md`
- `report_city_page_1.md`
- `report_city_page_2.md`