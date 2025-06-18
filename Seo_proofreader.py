import os
import re
import json
import argparse
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
        creds_data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(creds_data)
    else:
        # Try to load from token.json file
        try:
            with open('token.json', 'r') as token_file:
                creds_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(creds_data)
        except FileNotFoundError:
            print("Error: No credentials found. Please set up token.json or GOOGLE_CREDENTIALS environment variable.")
            return None, None

    # Build services
    docs_service = build('docs', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    return docs_service, sheets_service


def read_document(doc_id, service):
    """Read content from Google Doc."""
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
            keywords = [row[keyword_col_idx] for row in values[1:] if len(
                row) > keyword_col_idx and row[keyword_col_idx].strip()]
            return keywords
        else:
            # If no keyword column found, assume first column contains keywords
            keywords = [row[0]
                        for row in values[1:] if len(row) > 0 and row[0].strip()]
            return keywords

    except Exception as e:
        print(f"Error reading keyword list: {e}")
        return []


def detect_page_type(text, keywords=None):
    """Detect if the page is a cost page or city page."""
    text_lower = text.lower()

    # Cost page indicators
    cost_indicators = ['price', 'cost', 'fee',
                       'expense', 'tariff', '€', '$', 'kosten', 'prijs']
    cost_score = sum(
        1 for indicator in cost_indicators if indicator in text_lower)

    # City page indicators
    city_indicators = ['city', 'local', 'area',
                       'region', 'district', 'neighborhood']
    city_score = sum(
        1 for indicator in city_indicators if indicator in text_lower)

    # Check keywords for additional context
    if keywords:
        keyword_text = ' '.join(keywords).lower()
        cost_score += sum(1 for indicator in cost_indicators if indicator in keyword_text)
        city_score += sum(1 for indicator in city_indicators if indicator in keyword_text)

    return "cost" if cost_score > city_score else "city"


def evaluate_checklist(text, keywords, page_type):
    """Evaluate content against the appropriate checklist."""
    if page_type == "cost":
        return evaluate_cost_page(text, keywords)
    else:
        # Extract city name for city pages
        city_name = extract_city_name(text, keywords)
        return evaluate_city_page(text, keywords, city_name)


def extract_city_name(text, keywords):
    """Extract city name from keywords or text."""
    # Try to find city name in keywords first
    for keyword in keywords:
        # Look for patterns like "service in CityName"
        city_match = re.search(
            r'\b(?:in|te)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', keyword)
        if city_match:
            return city_match.group(1)

    # Fallback: look in text for common patterns
    city_patterns = [
        r'\b(?:in|te)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:area|region|city)'
    ]

    for pattern in city_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return "Unknown City"


def evaluate_cost_page(text, keywords):
    """Evaluate a cost page against the cost-specific SEO checklist."""
    results = {}

    # 1. Page Title and Meta Description
    results["page_title_meta"] = evaluate_title_meta(text, keywords)

    # 2. Headings and Keywords
    results["headings_keywords"] = evaluate_headings_keywords_cost(
        text, keywords)

    # 3. Internal Linking
    results["internal_linking"] = evaluate_internal_linking(text)

    # 4. General Quality
    results["general_quality"] = evaluate_general_quality(text)

    # 5. Tone and Readability
    results["tone_readability"] = evaluate_tone_readability(text)

    # 6. Formatting Guidelines
    results["formatting"] = evaluate_formatting(text)

    # 7. Cost Page Specific
    results["cost_specific"] = evaluate_cost_specific_features(text)

    # 8. FAQ Section
    results["faq_section"] = evaluate_faq_section(text)

    return results


def evaluate_city_page(text, keywords, city_name):
    """Evaluate a city page against the city-specific SEO checklist."""
    results = {}

    # 1. Headings and Keywords (City-specific)
    results["headings_keywords"] = evaluate_headings_keywords_city(
        text, keywords, city_name)

    # 2. Internal Linking
    results["internal_linking"] = evaluate_internal_linking(text)

    # 3. General Quality (City-specific)
    results["general_quality"] = evaluate_general_quality_city(text, city_name)

    # 4. Tone and Readability
    results["tone_readability"] = evaluate_tone_readability(text)

    # 5. Formatting Guidelines
    results["formatting"] = evaluate_formatting(text)

    # 6. City-Specific Features
    results["city_specific"] = evaluate_city_specific_features(text, city_name)

    return results


def evaluate_title_meta(text, keywords):
    """Evaluate page title and meta description."""
    score = 5  # Base score
    details = []

    # Extract title (simplified - assumes first line or H1)
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1)
        main_keyword = keywords[0] if keywords else ""

        if main_keyword.lower() in title.lower():
            score += 3
            details.append("✓ Main keyword found in title")
        else:
            details.append("✗ Main keyword missing from title")

        if '|' in title:
            score += 2
            details.append("✓ Good title structure with separators")
    else:
        details.append("✗ No H1 title found")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_headings_keywords_cost(text, keywords):
    """Evaluate headings and keywords for cost pages."""
    score = 0
    details = []

    # Extract headings
    h1_pattern = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE)
    h2_pattern = re.compile(r'<h2[^>]*>(.*?)</h2>', re.IGNORECASE)
    h3_pattern = re.compile(r'<h3[^>]*>(.*?)</h3>', re.IGNORECASE)

    h1_tags = h1_pattern.findall(text)
    h2_tags = h2_pattern.findall(text)
    h3_tags = h3_pattern.findall(text)

    main_keyword = keywords[0] if keywords else ""

    # Check H1 matches main keyword exactly
    if h1_tags and main_keyword.lower() in h1_tags[0].lower():
        score += 3
        details.append("✓ H1 contains main keyword")
    else:
        details.append("✗ H1 should match main keyword exactly")

    # Check keyword placement naturalness
    keyword_density = calculate_keyword_density(text, keywords)
    if 1 <= keyword_density <= 3:
        score += 2
        details.append("✓ Natural keyword placement")
    else:
        details.append("✗ Keyword density issues (should be 1-3%)")

    # Check subtopic coverage
    if len(h2_tags) >= 3:
        score += 2
        details.append("✓ Good subtopic coverage with H2s")

    # Check FAQ coverage
    faq_keywords = [kw for kw in keywords if any(
        q in kw.lower() for q in ['what', 'how', 'why', 'when', 'where'])]
    if len(faq_keywords) > 0:
        score += 2
        details.append("✓ FAQ-style keywords present")

    # Check spelling priorities
    score += 1
    details.append("✓ Assuming correct spelling used")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_headings_keywords_city(text, keywords, city_name):
    """Evaluate headings and keywords for city pages."""
    score = 0
    details = []

    # Extract headings
    h2_pattern = re.compile(r'<h2[^>]*>(.*?)</h2>', re.IGNORECASE)
    h2_tags = h2_pattern.findall(text)

    # Check H2s include city and CTA
    h2_with_city = sum(1 for h2 in h2_tags if city_name.lower() in h2.lower())
    cta_words = ['find', 'compare', 'discover',
                 'best', 'top', 'reliable', 'professional']
    h2_with_cta = sum(1 for h2 in h2_tags if any(
        cta in h2.lower() for cta in cta_words))

    if h2_with_city > 0 and h2_with_cta > 0:
        score += 3
        details.append("✓ H2s include city name and CTA language")
    elif h2_with_city > 0:
        score += 2
        details.append("△ H2s include city but need more CTA language")
    else:
        details.append("✗ H2s should include city name and action words")

    # Check city-focused keywords
    city_focused_keywords = sum(
        1 for kw in keywords if city_name.lower() in kw.lower())
    if city_focused_keywords >= len(keywords) * 0.7:
        score += 2
        details.append("✓ Most keywords are city-focused")
    else:
        details.append("✗ More keywords should be city-specific")

    # Check keyword placement
    keyword_density = calculate_keyword_density(text, keywords)
    if 1 <= keyword_density <= 3:
        score += 2
        details.append("✓ Natural keyword placement")
    else:
        details.append("✗ Keyword density issues")

    # Check subtopic coverage
    if len(h2_tags) >= 3:
        score += 2
        details.append("✓ Good subtopic structure")

    # Check logical heading structure
    score += 1
    details.append("✓ Assuming logical heading flow")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_internal_linking(text):
    """Evaluate internal linking strategy."""
    score = 0
    details = []

    # Extract links
    link_pattern = re.compile(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE)
    links = link_pattern.findall(text)

    # Count different types of links
    top10_links = sum(1 for _, link_text in links if "top 10" in link_text.lower(
    ) or "top ten" in link_text.lower())
    cost_links = sum(1 for _, link_text in links if any(
        word in link_text.lower() for word in ["cost", "price", "kosten", "prijs"]))

    if top10_links >= 2:
        score += 4
        details.append("✓ Multiple Top 10 page links")
    elif top10_links >= 1:
        score += 2
        details.append("△ Has Top 10 links but could add more")
    else:
        details.append("✗ Missing Top 10 page links")

    if cost_links >= 1:
        score += 3
        details.append("✓ Links to cost pages")
    else:
        details.append("✗ Should link to relevant cost pages")

    # Check for nearby cities (city pages)
    nearby_links = sum(1 for _, link_text in links if any(
        word in link_text.lower() for word in ["nearby", "other cities", "region"]))
    if nearby_links > 0:
        score += 2
        details.append("✓ Links to nearby locations")

    # General link quantity
    if len(links) >= 5:
        score += 1
        details.append("✓ Good internal linking quantity")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_general_quality(text):
    """Evaluate general content quality."""
    score = 0
    details = []

    # Check introduction length
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs and len(paragraphs[0].split('.')) <= 3:
        score += 1
        details.append("✓ Concise introduction")
    else:
        details.append("✗ Introduction should be one paragraph")

    # Check for redundancy (simplified)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    unique_ratio = len(set(sentences)) / len(sentences) if sentences else 0
    if unique_ratio > 0.9:
        score += 2
        details.append("✓ No redundant information")
    else:
        details.append("△ Some content may be redundant")

    # Check content value (word count as proxy)
    word_count = len(text.split())
    if word_count >= 800:
        score += 2
        details.append("✓ Comprehensive content")
    elif word_count >= 400:
        score += 1
        details.append("△ Adequate content length")
    else:
        details.append("✗ Content too brief")

    # Check for CTAs
    cta_patterns = ['compare', 'contact', 'get quote', 'find', 'choose']
    cta_count = sum(1 for pattern in cta_patterns if pattern in text.lower())
    if cta_count >= 2:
        score += 2
        details.append("✓ Good CTA usage")
    elif cta_count >= 1:
        score += 1
        details.append("△ Has CTAs but could add more")

    # Check Trustoo/Trustlocal value proposition
    brand_value = any(term in text.lower() for term in [
                      'trustoo', 'trustlocal', 'verified', 'checked', 'quality marks'])
    if brand_value:
        score += 2
        details.append("✓ Brand value proposition present")
    else:
        details.append("✗ Should emphasize Trustoo/Trustlocal value")

    # General quality assumption
    score += 1
    details.append("✓ Assuming good spelling and grammar")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_general_quality_city(text, city_name):
    """Evaluate general quality for city pages with city-specific checks."""
    result = evaluate_general_quality(text)

    # Add city-specific quality checks
    score = result["score"]
    details = result["details"].split("; ")

    # Check for local business advantages
    local_advantages = any(term in text.lower() for term in [
                           "local", "nearby", "travel expense", "quick response", "familiar with area"])
    if local_advantages:
        score = min(score + 1, 10)
        details.append("✓ Emphasizes local business advantages")
    else:
        details.append("✗ Should emphasize local business advantages")

    # Check for city districts
    districts_mentioned = any(term in text.lower() for term in [
                              "district", "area", "neighborhood", "region", city_name.lower()])
    if districts_mentioned:
        score = min(score + 1, 10)
        details.append("✓ Mentions city areas/districts")
    else:
        details.append("✗ Should mention city districts naturally")

    # Check for cost paragraph
    cost_paragraph = any(para for para in text.split('\n\n') if any(
        term in para.lower() for term in ["cost", "price", "fee"]))
    if cost_paragraph:
        score = min(score + 1, 10)
        details.append("✓ Includes cost information")
    else:
        details.append("✗ Should include cost paragraph")

    return {
        "score": score,
        "details": "; ".join(details)
    }


def evaluate_tone_readability(text):
    """Evaluate tone of voice and readability."""
    score = 0
    details = []

    # Check sentence length
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    avg_sentence_length = sum(len(s.split())
                              for s in sentences) / len(sentences) if sentences else 0

    if avg_sentence_length <= 15:
        score += 3
        details.append("✓ Good sentence length")
    elif avg_sentence_length <= 20:
        score += 2
        details.append("△ Acceptable sentence length")
    else:
        details.append("✗ Sentences too long")

    # Check for exclamation marks
    exclamation_count = text.count("!")
    if exclamation_count == 0:
        score += 2
        details.append("✓ No exclamation marks")
    elif exclamation_count <= 2:
        score += 1
        details.append("△ Few exclamation marks")
    else:
        details.append("✗ Too many exclamation marks")

    # Check for bold formatting
    bold_count = len(re.findall(
        r'<(strong|b)[^>]*>.*?</(strong|b)>', text, re.IGNORECASE))
    if bold_count >= 3:
        score += 2
        details.append("✓ Good use of bold formatting")
    elif bold_count >= 1:
        score += 1
        details.append("△ Some bold formatting")
    else:
        details.append("✗ Should use bold for key information")

    # Check paragraph length
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    avg_paragraph_length = sum(
        len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
    if avg_paragraph_length <= 50:
        score += 2
        details.append("✓ Short, scannable paragraphs")
    elif avg_paragraph_length <= 80:
        score += 1
        details.append("△ Acceptable paragraph length")

    # Check for tentative words
    tentative_words = ['maybe', 'perhaps', 'possibly', 'might']
    tentative_count = sum(
        1 for word in tentative_words if word in text.lower())
    if tentative_count == 0:
        score += 1
        details.append("✓ No tentative language")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_formatting(text):
    """Evaluate formatting and specific guidelines."""
    score = 5  # Base score
    details = []

    # Check price formatting
    price_patterns = [r'€\s*\d+,-', r'€\s*\d+\.\d+,-', r'€\s*\d+,\d+']
    correct_prices = sum(
        1 for pattern in price_patterns if re.search(pattern, text))
    if correct_prices > 0:
        score += 2
        details.append("✓ Correct price formatting")

    # Check percentage formatting
    if re.search(r'\d+%', text):
        score += 1
        details.append("✓ Correct percentage formatting")

    # Check number formatting (simplified)
    # This would need more sophisticated checking in practice
    score += 1
    details.append("✓ Assuming correct number formatting")

    # Check bullet point formatting
    bullet_patterns = [r'^\s*[-•*]\s+', r'^\s*\d+\.\s+']
    if any(re.search(pattern, text, re.MULTILINE) for pattern in bullet_patterns):
        score += 1
        details.append("✓ Has formatted bullet points")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_cost_specific_features(text):
    """Evaluate cost page specific features."""
    score = 0
    details = []

    # Check for tables
    table_indicators = ['<table', '|', 'cost', 'price', 'service']
    table_score = sum(
        1 for indicator in table_indicators if indicator in text.lower())
    if table_score >= 3:
        score += 3
        details.append("✓ Contains cost tables")
    elif table_score >= 1:
        score += 1
        details.append("△ Some table elements present")
    else:
        details.append("✗ Should include cost tables")

    # Check price realism (simplified - checks for reasonable ranges)
    price_matches = re.findall(r'€\s*(\d+)', text)
    if price_matches:
        prices = [int(p) for p in price_matches]
        if all(10 <= p <= 10000 for p in prices):
            score += 2
            details.append("✓ Realistic price ranges")
        else:
            details.append("△ Check price realism")

    # Check pricing focus
    pricing_keywords = ['cost', 'price', 'fee', 'tariff', 'rate', 'expense']
    pricing_focus = sum(
        1 for keyword in pricing_keywords if keyword in text.lower())
    if pricing_focus >= 5:
        score += 3
        details.append("✓ Strong pricing focus")
    elif pricing_focus >= 2:
        score += 2
        details.append("△ Some pricing focus")

    # Check CTA button considerations
    cta_buttons = re.findall(
        r'<button[^>]*>(.*?)</button>', text, re.IGNORECASE)
    short_ctas = [cta for cta in cta_buttons if len(cta) <= 20]
    if len(short_ctas) >= len(cta_buttons) * 0.8:
        score += 2
        details.append("✓ Mobile-friendly CTA buttons")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_faq_section(text):
    """Evaluate FAQ section quality."""
    score = 0
    details = []

    # Check for FAQ presence
    faq_indicators = ['faq', 'frequently asked',
                      'questions', 'what is', 'how to', 'why']
    faq_count = sum(
        1 for indicator in faq_indicators if indicator in text.lower())

    if faq_count >= 3:
        score += 3
        details.append("✓ FAQ section present")

        # Check for specific headings
        generic_faq = text.lower().count('faq')
        if generic_faq <= 1:
            score += 2
            details.append("✓ Specific FAQ headings")
        else:
            details.append("△ Avoid generic 'FAQ' titles")

        # Check for intro text
        if 'questions' in text.lower() and 'answers' in text.lower():
            score += 2
            details.append("✓ FAQ introduction present")

        # Check for question format
        question_patterns = [r'what\s+is', r'how\s+to',
                             r'why\s+', r'when\s+', r'where\s+']
        question_count = sum(1 for pattern in question_patterns if re.search(
            pattern, text, re.IGNORECASE))
        if question_count >= 3:
            score += 3
            details.append("✓ Good question variety")
        elif question_count >= 1:
            score += 1
            details.append("△ Some questions present")
    else:
        details.append("✗ FAQ section missing or minimal")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def evaluate_city_specific_features(text, city_name):
    """Evaluate city-specific features."""
    score = 0
    details = []

    # Check city name frequency
    city_mentions = text.lower().count(city_name.lower())
    text_length = len(text.split())
    city_density = (city_mentions / text_length *
                    100) if text_length > 0 else 0

    if 0.5 <= city_density <= 2:
        score += 3
        details.append("✓ Good city name frequency")
    elif city_mentions > 0:
        score += 1
        details.append("△ City mentioned but check frequency")
    else:
        details.append("✗ City name rarely mentioned")

    # Check for local advantages
    local_terms = ['local', 'nearby', 'close',
                   'area', 'region', 'travel', 'quick response']
    local_score = sum(1 for term in local_terms if term in text.lower())
    if local_score >= 3:
        score += 2
        details.append("✓ Emphasizes local advantages")
    elif local_score >= 1:
        score += 1
        details.append("△ Some local advantages mentioned")

    # Check for professional/city-specific information
    professional_terms = ['specialized', 'familiar',
                          'experienced', 'local expertise', 'regulations']
    prof_score = sum(1 for term in professional_terms if term in text.lower())
    if prof_score >= 2:
        score += 2
        details.append("✓ Professional city-specific info")

    # Check for districts/areas
    area_terms = ['district', 'neighborhood', 'area', 'zone', 'sector']
    area_score = sum(1 for term in area_terms if term in text.lower())
    if area_score >= 1:
        score += 2
        details.append("✓ Mentions city areas/districts")
    else:
        details.append("✗ Should mention city districts")

    # Check for cost information
    cost_terms = ['cost', 'price', 'fee', 'expense']
    cost_mentions = sum(1 for term in cost_terms if term in text.lower())
    if cost_mentions >= 2:
        score += 1
        details.append("✓ Includes cost information")

    return {
        "score": min(score, 10),
        "details": "; ".join(details)
    }


def calculate_keyword_density(text, keywords):
    """Calculate keyword density percentage."""
    if not keywords:
        return 0

    word_count = len(text.split())
    keyword_count = sum(text.lower().count(keyword.lower())
                        for keyword in keywords)

    return (keyword_count / word_count * 100) if word_count > 0 else 0


def generate_improvement_suggestions(text, keywords, checklist_results, page_type):
    """Generate improvement suggestions based on evaluation results."""
    suggestions = []

    # Find lowest scoring items
    low_scores = [(item, result) for item, result in checklist_results.items()
                  if isinstance(result, dict) and "score" in result and result["score"] < 7]

    # Sort by lowest score first
    low_scores.sort(key=lambda x: x[1]["score"])

    # Generate targeted suggestions
    for item, result in low_scores[:5]:  # Top 5 lowest scores
        if item == "headings_keywords":
            if page_type == "city":
                suggestions.append(
                    f"Improve H2 headings by including action words like 'Find' or 'Compare' along with location-specific keywords.")
            else:
                suggestions.append(
                    "Ensure H1 matches the main keyword exactly and use high-volume keywords naturally in subheadings.")

        elif item == "internal_linking":
            suggestions.append(
                "Add more internal links to Top 10 pages and relevant cost pages to improve navigation and SEO value.")

        elif item == "general_quality":
            suggestions.append(
                "Improve content quality by making the introduction more concise and ensuring each paragraph adds unique value.")

        elif item == "tone_readability":
            suggestions.append(
                "Improve readability by using shorter sentences, avoiding exclamation marks, and using bold formatting for key information.")

        elif item == "formatting":
            suggestions.append(
                "Follow formatting guidelines: use € 150,- for prices, write numbers up to 20 in words, and format bullet points correctly.")

        elif item == "cost_specific":
            suggestions.append(
                "Add cost tables at the top of sections with realistic prices and ensure all information relates to pricing.")

        elif item == "city_specific":
            suggestions.append(
                "Include more city-specific information such as local business advantages and mentions of city districts.")

        elif item == "faq_section":
            suggestions.append(
                "Add a comprehensive FAQ section with specific headings and high search volume questions.")

    # Fill remaining slots with general suggestions if needed
    general_suggestions = [
        "Optimize keyword density to 1-3% for natural placement without stuffing.",
        "Include more CTAs encouraging users to compare multiple service providers.",
        "Emphasize the added value of Trustoo/Trustlocal platform features.",
        "Ensure content answers all questions a user might have about the topic.",
        "Compare with top Google search results to ensure competitive content quality."
    ]

    for suggestion in general_suggestions:
        if len(suggestions) < 5 and suggestion not in suggestions:
            suggestions.append(suggestion)

    return suggestions[:5]


def main():
    parser = argparse.ArgumentParser(description='SEO Proofreader Tool')
    parser.add_argument('--doc_id', required=True, help='Google Doc ID')
    parser.add_argument('--keywords_sheet', required=True,
                        help='Google Sheet ID with keywords')
    parser.add_argument(
        '--page_type', choices=['cost', 'city'], help='Force page type (optional)')

    args = parser.parse_args()

    # Authenticate with Google
    docs_service, sheets_service = authenticate_google()
    if not docs_service or not sheets_service:
        return

    # Read document and keywords
    print("Reading document...")
    text = read_document(args.doc_id, docs_service)
    if not text:
        print("Failed to read document")
        return

    print("Reading keywords...")
    keywords = read_keyword_list(args.keywords_sheet, sheets_service)
    if not keywords:
        print("Failed to read keywords")
        return

    # Detect or use specified page type
    page_type = args.page_type or detect_page_type(text, keywords)
    print(f"Page type: {page_type}")

    # Evaluate content
    print("Evaluating content...")
    checklist_results = evaluate_checklist(text, keywords, page_type)

    # Generate suggestions
    print("Generating suggestions...")
    suggestions = generate_improvement_suggestions(
        text, keywords, checklist_results, page_type)

    # Generate report
    print("Generating report...")
    report = generate_report(
        text, keywords, checklist_results, suggestions, page_type)

    # Save report
    output_filename = f"report_{args.doc_id}.md"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report saved as {output_filename}")


if __name__ == "__main__":
    main()
