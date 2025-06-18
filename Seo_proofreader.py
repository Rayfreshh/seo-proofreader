import os
import argparse
import pandas as pd
import re
import json
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from report_generator import generate_report

# Set OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")


def authenticate_google():
    """Authenticate with Google API using OAuth credentials."""
    # Check if credentials are stored in environment variable
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        creds_info = json.loads(creds_json)
        return Credentials.from_authorized_user_info(creds_info)

    # If not in environment, look for token file
    token_path = 'token.json'
    if os.path.exists(token_path):
        return Credentials.from_authorized_user_file(token_path)

    # If no credentials available, guide the user
    print("No credentials found. Please follow the setup instructions in the README.")
    return None


def read_document(doc_id, service):
    """Read content from a Google Doc."""
    try:
        document = service.documents().get(documentId=doc_id).execute()

        text_content = []
        for content in document.get('body').get('content'):
            if 'paragraph' in content:
                for element in content.get('paragraph').get('elements'):
                    if 'textRun' in element:
                        text_content.append(
                            element.get('textRun').get('content'))

        return ''.join(text_content)
    except Exception as e:
        print(f"Error reading Google Doc: {e}")
        return None


def read_keyword_list(sheet_id, service):
    """Read keywords from Google Sheet."""
    try:
        # Get sheet metadata to find the first sheet
        metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_name = metadata['sheets'][0]['properties']['title']

        # Read the data
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=sheet_name
        ).execute()

        values = result.get('values', [])

        if not values:
            return []

        # Try to find keyword column
        header_row = values[0]
        keyword_col_idx = None

        for idx, col_name in enumerate(header_row):
            if 'keyword' in str(col_name).lower():
                keyword_col_idx = idx
                break

        # Extract keywords
        if keyword_col_idx is not None:
            keywords = [row[keyword_col_idx] for row in values[1:]
                        if len(row) > keyword_col_idx and row[keyword_col_idx]]
        else:
            # Assume first column has keywords
            keywords = [row[0] for row in values[1:] if row and row[0]]

        return keywords

    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return []


def detect_page_type(text, keywords=None):
    """Detect if the page is a cost page or city page using OpenAI."""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an SEO content analyzer."},
                {"role": "user", "content": f"""Determine if this content is a 'cost page' or a 'city page'.
                
                Cost pages focus on pricing, costs, and financial aspects of services.
                City pages focus on local services in specific cities or locations.

                First paragraph of content:
                {text[:500]}
                
                Keywords: {', '.join(keywords[:10]) if keywords else 'No keywords provided'}
                
                Respond with ONLY 'cost' or 'city'.
                """}
            ],
            temperature=0,
            max_tokens=10
        )

        result = response.choices[0].message.content.strip().lower()

        if "cost" in result:
            return "cost"
        elif "city" in result:
            return "city"
        else:
            # Fallback to simple heuristic
            cost_indicators = sum(text.lower().count(word) for word in [
                                  "cost", "price", "pricing", "$", "affordable"])
            city_indicators = sum(text.lower().count(word) for word in [
                                  "city", "local", "area", "near", "location"])

            return "cost" if cost_indicators > city_indicators else "city"

    except Exception as e:
        print(f"Error using OpenAI for page type detection: {e}")
        # Simple fallback method
        if keywords and any("cost" in kw.lower() or "price" in kw.lower() for kw in keywords):
            return "cost"
        elif keywords and any("city" in kw.lower() or "in " in kw.lower() for kw in keywords):
            return "city"
        else:
            return "cost"  # Default to cost page


def evaluate_checklist(text, keywords, page_type):
    """Evaluate the content against the appropriate checklist."""
    if page_type == "cost":
        return evaluate_cost_page(text, keywords)
    else:
        return evaluate_city_page(text, keywords)


def evaluate_cost_page(text, keywords):
    """Evaluate a cost page against its checklist using OpenAI."""
    results = {}

    # Use OpenAI for comprehensive analysis
    try:
        # Get main analysis from OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system",
                    "content": "You are an expert SEO content analyzer for cost pages."},
                {"role": "user", "content": f"""Analyze this cost page content and provide scores (0-10) on these criteria:

                1. Grammar quality (grammatical correctness, sentence structure)
                2. Readability (reading level, clarity, flow)
                3. Keyword usage (proper keyword density, primary keyword in important places)
                4. Title quality (contains primary keyword, clear value proposition)
                5. Heading structure (logical organization, keyword in headings)
                6. Price table presence (has clear pricing information in table format)
                7. Internal linking (contains links to related content)
                8. Cost range coverage (mentions price ranges, not just single prices)
                
                Content (first 4000 characters):
                {text[:4000]}
                
                Target keywords:
                {', '.join(keywords[:10])}
                
                Respond in JSON format with scores and brief explanations:
                {{
                    "grammar_score": {{
                        "score": 0-10,
                        "details": "brief explanation"
                    }},
                    "readability_score": {{
                        "score": 0-10,
                        "details": "brief explanation"
                    }},
                    ...and so on for all criteria
                }}
                """}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        # Parse the results
        results = json.loads(response.choices[0].message.content)

    except Exception as e:
        print(f"Error using OpenAI for content evaluation: {e}")
        # Fallback to simple checks
        results = fallback_cost_page_evaluation(text, keywords)

    return results


def evaluate_city_page(text, keywords):
    """Evaluate a city page against its checklist using OpenAI."""
    results = {}

    # Use OpenAI for comprehensive analysis
    try:
        # Get main analysis from OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You are an expert SEO content analyzer for city/location pages."},
                {"role": "user", "content": f"""Analyze this city/location page content and provide scores (0-10) on these criteria:

                1. Grammar quality (grammatical correctness, sentence structure)
                2. Readability (reading level, clarity, flow)
                3. Keyword usage (proper keyword density, location keywords in important places)
                4. Title quality (contains location name, clear service offering)
                5. Local signals (mentions neighborhood names, landmarks, local terminology)
                6. Heading structure (logical organization, location in headings)
                7. Local business mentions (references to local service providers)
                
                Content (first 4000 characters):
                {text[:4000]}
                
                Target keywords:
                {', '.join(keywords[:10])}
                
                Respond in JSON format with scores and brief explanations:
                {{
                    "grammar_score": {{
                        "score": 0-10,
                        "details": "brief explanation"
                    }},
                    "readability_score": {{
                        "score": 0-10,
                        "details": "brief explanation"
                    }},
                    ...and so on for all criteria
                }}
                """}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        # Parse the results
        results = json.loads(response.choices[0].message.content)

    except Exception as e:
        print(f"Error using OpenAI for content evaluation: {e}")
        # Fallback to simple checks
        results = fallback_city_page_evaluation(text, keywords)

    return results


def fallback_cost_page_evaluation(text, keywords):
    """Simple fallback evaluation for cost pages if OpenAI fails."""
    results = {}

    # Simple keyword density check
    keyword_counts = {kw.lower(): text.lower().count(kw.lower())
                      for kw in keywords}
    total_words = len(text.split())

    # Grammar - simplistic check for common errors
    grammar_errors = len(re.findall(r'\s+[,.?!]|[,.?!][a-zA-Z]', text))

    results["grammar_score"] = {
        "score": max(0, 10 - grammar_errors//2),
        "details": f"Found approximately {grammar_errors} potential grammar issues."
    }

    # Readability - simple word/sentence length check
    sentences = re.split(r'[.!?]+', text)
    avg_words_per_sentence = sum(len(s.split())
                                 for s in sentences) / max(1, len(sentences))

    results["readability_score"] = {
        "score": 10 if 10 <= avg_words_per_sentence <= 20 else 5,
        "details": f"Average words per sentence: {avg_words_per_sentence:.1f}"
    }

    # Keyword usage
    if keyword_counts:
        primary_keyword = max(keyword_counts.items(), key=lambda x: x[1])[0]
        primary_density = keyword_counts[primary_keyword] / total_words * 100

        results["keyword_usage"] = {
            "score": 10 if 1 <= primary_density <= 3 else 5,
            "details": f"Primary keyword '{primary_keyword}' density: {primary_density:.2f}%"
        }
    else:
        results["keyword_usage"] = {
            "score": 0,
            "details": "No keywords provided to evaluate density."
        }

    # Title check
    first_line = text.strip().split('\n')[0]
    results["title_quality"] = {
        "score": sum(kw.lower() in first_line.lower() for kw in keywords[:3]) * 3,
        "details": "Title check based on first line of document."
    }

    # Price table check
    has_price_table = bool(
        re.search(r'(?i)price table|cost table|\|\s*price\s*\||\|\s*cost\s*\|', text))
    results["price_table_presence"] = {
        "score": 10 if has_price_table else 0,
        "details": "Price table detected" if has_price_table else "No price table found"
    }

    return results


def fallback_city_page_evaluation(text, keywords):
    """Simple fallback evaluation for city pages if OpenAI fails."""
    results = {}

    # Simple keyword density check
    keyword_counts = {kw.lower(): text.lower().count(kw.lower())
                      for kw in keywords}
    total_words = len(text.split())

    # Grammar - simplistic check for common errors
    grammar_errors = len(re.findall(r'\s+[,.?!]|[,.?!][a-zA-Z]', text))

    results["grammar_score"] = {
        "score": max(0, 10 - grammar_errors//2),
        "details": f"Found approximately {grammar_errors} potential grammar issues."
    }

    # Readability - simple word/sentence length check
    sentences = re.split(r'[.!?]+', text)
    avg_words_per_sentence = sum(len(s.split())
                                 for s in sentences) / max(1, len(sentences))

    results["readability_score"] = {
        "score": 10 if 10 <= avg_words_per_sentence <= 20 else 5,
        "details": f"Average words per sentence: {avg_words_per_sentence:.1f}"
    }

    # Local signals check
    local_terms = re.findall(
        r'(?i)local|nearby|in the area|around (?:the |)(?:city|town)|community', text)
    locations = re.findall(r'(?i)in [A-Z][a-z]+(?:\s[A-Z][a-z]+)?', text)
    local_signals = len(local_terms) + len(locations)

    results["local_signals"] = {
        "score": min(10, local_signals * 2),
        "details": f"Found {local_signals} local terminology references"
    }

    # Title check
    first_line = text.strip().split('\n')[0]
    has_location_in_title = bool(
        re.search(r'(?i)in [A-Z][a-z]+|near [A-Z][a-z]+', first_line))
    results["title_quality"] = {
        "score": 10 if has_location_in_title else 0,
        "details": "Title contains location" if has_location_in_title else "Location missing from title"
    }

    return results


def generate_improvement_suggestions(text, keywords, checklist_results, page_type):
    """Generate top improvement suggestions using OpenAI."""
    try:
        # Convert checklist results to a simple format for the prompt
        simple_results = []
        for item, details in checklist_results.items():
            if isinstance(details, dict) and "score" in details:
                simple_results.append(
                    f"{item}: {details['score']}/10 - {details.get('details', '')}")

        results_text = "\n".join(simple_results)

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an SEO content improvement advisor for {page_type} pages."},
                {"role": "user", "content": f"""Based on the following evaluation results, provide the top 5 most important
                actionable improvement suggestions for this {page_type} page.
                
                Content excerpt:
                {text[:1000]}...
                
                Keywords: {', '.join(keywords[:10])}
                
                Evaluation results:
                {results_text}
                
                Focus on concrete, specific suggestions that will have the biggest impact on SEO performance.
                Start each suggestion with an action verb.
                Number your suggestions 1-5.
                """}
            ],
            temperature=0.7,
            max_tokens=600
        )

        suggestions_text = response.choices[0].message.content.strip()

        # Parse numbered list
        suggestions = re.findall(
            r'\d+\.\s*(.+?)(?=\n\d+\.|\n*$)', suggestions_text, re.DOTALL)
        suggestions = [s.strip() for s in suggestions]

        return suggestions[:5]  # Limit to top 5

    except Exception as e:
        print(f"Error generating suggestions with OpenAI: {e}")
        # Fallback: generate basic suggestions based on lowest scores
        suggestions = []
        threshold = 5  # Consider items below this score as needing improvement

        for item, details in checklist_results.items():
            if isinstance(details, dict) and "score" in details and details["score"] < threshold:
                item_name = item.replace("_", " ").title()
                if "grammar" in item.lower():
                    suggestions.append(
                        f"Improve grammar and proofread the content to fix grammatical errors.")
                elif "keyword" in item.lower():
                    suggestions.append(
                        f"Increase usage of target keywords, especially the primary keyword.")
                elif "title" in item.lower():
                    suggestions.append(
                        f"Revise the title to include the primary keyword and clear value proposition.")
                elif "price" in item.lower() or "cost" in item.lower():
                    suggestions.append(
                        f"Add a clear pricing table with cost ranges.")
                elif "local" in item.lower():
                    suggestions.append(
                        f"Add more local references and location-specific information.")
                elif "heading" in item.lower():
                    suggestions.append(
                        f"Improve heading structure to include keywords and better organization.")
                elif "link" in item.lower():
                    suggestions.append(
                        f"Add internal links to related content.")

        # If we don't have 5 suggestions, add some generic ones
        generic_suggestions = [
            "Improve the introduction to clearly state the purpose of the page.",
            "Add a strong call-to-action at the end of the content.",
            "Include more specific details relevant to the target audience.",
            "Break up long paragraphs into smaller, more digestible chunks.",
            "Add bulleted lists to highlight important points."
        ]

        while len(suggestions) < 5 and generic_suggestions:
            suggestions.append(generic_suggestions.pop(0))

        return suggestions[:5]


def main():
    parser = argparse.ArgumentParser(description='SEO Proofreader Tool')
    parser.add_argument('--doc_id', required=True, help='Google Doc ID')
    parser.add_argument('--keywords_sheet', required=True,
                        help='Keywords Google Sheet ID')
    parser.add_argument('--page_type', help='Force page type (cost or city)')

    args = parser.parse_args()

    # Authenticate with Google
    credentials = authenticate_google()
    if not credentials:
        print("Authentication failed. Cannot proceed.")
        return

    # Read document and keywords
    docs_service = build('docs', 'v1', credentials=credentials)
    sheets_service = build('sheets', 'v4', credentials=credentials)

    print("Reading document content...")
    document_text = read_document(args.doc_id, docs_service)
    if not document_text:
        print("Could not read document content. Aborting.")
        return

    print("Reading keywords...")
    keywords = read_keyword_list(args.keywords_sheet, sheets_service)
    if not keywords:
        print("Warning: No keywords found or could not read keyword sheet.")

    # Detect page type if not provided
    if args.page_type and args.page_type.lower() in ['cost', 'city']:
        page_type = args.page_type.lower()
        print(f"Using specified page type: {page_type}")
    else:
        print("Detecting page type...")
        page_type = detect_page_type(document_text, keywords)
        print(f"Detected page type: {page_type}")

    # Evaluate against checklist
    print(f"Evaluating {page_type} page...")
    checklist_results = evaluate_checklist(document_text, keywords, page_type)

    # Generate improvement suggestions
    print("Generating improvement suggestions...")
    suggestions = generate_improvement_suggestions(
        document_text, keywords, checklist_results, page_type)

    # Generate and output the report
    print("Creating report...")
    report = generate_report(document_text, keywords,
                             checklist_results, suggestions, page_type)

    # Output report
    output_filename = f"report_{args.doc_id.split('/')[-1]}.md"
    with open(output_filename, "w") as f:
        f.write(report)

    print(f"Report generated and saved to {output_filename}")


if __name__ == "__main__":
    main()
