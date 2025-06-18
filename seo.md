# SEO Proofreader Tool

A tool to evaluate SEO content against predefined checklists for cost pages and city pages.

## Setup

### Prerequisites

- Python 3.8 or higher
- Google account with access to the Google Drive documents
- OpenAI API key

### Installation

1. Clone this repository:
git clone https://github.com/yourusername/seo-proofreader.git cd seo-proofreader
2. Install dependencies:
 pip install -r requirements.txt


3. Set up API credentials:

a. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

b. Google Drive API setup:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Docs API and Google Sheets API
   - Create OAuth credentials (Desktop app)
   - Download the credentials JSON file
   - Either set the environment variable:
     ```
     export GOOGLE_CREDENTIALS=$(cat /path/to/credentials.json)
     ```
     Or rename the file to `token.json` and place it in the project root directory.

## Usage

Run the proofreader with a Google Document ID and its corresponding keyword sheet:

python app.py --doc_id DOCUMENT_ID --keywords_sheet SHEET_ID


Optionally specify the page type:

python app.py --doc_id DOCUMENT_ID --keywords_sheet SHEET_ID --page_type cost
### Parameters

- `--doc_id`: The ID of the Google Doc to analyze (required)
- `--keywords_sheet`: The ID of the Google Sheet containing keywords (required)
- `--page_type`: Force the page type - either "cost" or "city" (optional, auto-detected if not provided)

## Output

The tool will:

1. Generate a Markdown report with the checklist scores
2. Provide up to 5 improvement suggestions
3. Save the report to a file named `report_DOCUMENT_ID.md`

## Test Documents

The repository includes sample reports generated for the test documents:

- `report_cost_page_1.md`
- `report_cost_page_2.md`
- `report_city_page_1.md`
- `report_city_page_2.md`