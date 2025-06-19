"""
SEO Proofreader Tool with AI Integration

This module provides automated SEO content evaluation for cost pages and city pages
using AI-powered analysis with rule-based fallbacks.
"""

import os
import re
import json
import argparse
from typing import Dict, List, Optional, Tuple, Any

import openai
from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from report_generator import generate_report

# Constants
DEFAULT_SCORE = 5
MAX_SCORE = 10
PASS_THRESHOLD = 0.7
KEYWORD_DENSITY_MIN = 1
KEYWORD_DENSITY_MAX = 3
MAX_SENTENCE_LENGTH = 15
ACCEPTABLE_SENTENCE_LENGTH = 20
MIN_CONTENT_LENGTH = 400
GOOD_CONTENT_LENGTH = 800

# With:
client = None


def get_openai_client():
    """Get OpenAI client, initializing if needed."""
    global client
    if client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            client = openai.OpenAI(api_key=api_key)
    return client


class SEOEvaluationError(Exception):
    """Custom exception for SEO evaluation errors."""


def authenticate_google() -> Tuple[Optional[Any], Optional[Any]]:
    """
    Authenticate with Google API using OAuth credentials.

    Returns:
        Tuple of (docs_service, sheets_service) or (None, None) if authentication fails.
    """
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')

    if creds_json:
        try:
            creds_data = json.loads(creds_json)
            creds = Credentials.from_authorized_user_info(creds_data)
        except json.JSONDecodeError as e:
            print(f"Error parsing Google credentials: {e}")
            return None, None
    else:
        # Try to load from token.json file
        try:
            with open('token.json', 'r', encoding='utf-8') as token_file:
                creds_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(creds_data)
        except FileNotFoundError:
            print("Error: No credentials found. Please set up token.json or "
                  "GOOGLE_CREDENTIALS environment variable.")
            return None, None
        except json.JSONDecodeError as e:
            print(f"Error parsing token.json: {e}")
            return None, None

    try:
        docs_service = build('docs', 'v1', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        return docs_service, sheets_service
    except (GoogleAuthError, HttpError) as e:
        print(f"Error building Google services: {e}")
        return None, None


def read_document(doc_id: str, service: Any) -> Optional[str]:
    """
    Read content from Google Doc.

    Args:
        doc_id: Google Document ID
        service: Google Docs service instance

    Returns:
        Document text content or None if error occurs
    """
    try:
        document = service.documents().get(documentId=doc_id).execute()
        text_content = []

        body_content = document.get('body', {}).get('content', [])
        for content in body_content:
            if 'paragraph' in content:
                elements = content.get('paragraph', {}).get('elements', [])
                for element in elements:
                    if 'textRun' in element:
                        text_run = element.get('textRun', {})
                        text_content.append(text_run.get('content', ''))

        return ''.join(text_content)
    except (GoogleAuthError, HttpError) as e:
        print(f"Error reading Google Doc: {e}")
        return None


def read_keyword_list(sheet_id: str, service: Any) -> List[str]:
    """
    Read keywords from Google Sheet.

    Args:
        sheet_id: Google Sheet ID
        service: Google Sheets service instance

    Returns:
        List of keywords or empty list if error occurs
    """
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
            keywords = [
                row[keyword_col_idx] for row in values[1:]
                if (len(row) > keyword_col_idx and
                    row[keyword_col_idx].strip())
            ]
            return keywords
        else:
            # If no keyword column found, assume first column contains keywords
            keywords = [
                row[0] for row in values[1:]
                if len(row) > 0 and row[0].strip()
            ]
            return keywords

    except (GoogleAuthError, HttpError) as e:
        print(f"Error reading keyword list: {e}")
        return []


def call_openai_evaluation(text: str, keywords: List[str], evaluation_type: str,
                           page_type: str, city_name: Optional[str] = None) -> Optional[str]:
    """
    Use OpenAI to evaluate content with fallback to rule-based approach.

    Args:
        text: Content to evaluate
        keywords: List of target keywords
        evaluation_type: Type of evaluation to perform
        page_type: Type of page (cost or city)
        city_name: Name of target city for city pages

    Returns:
        OpenAI response or None if API unavailable
    """
    client = get_openai_client()
    if not client or not client.api_key:
        print(
            f"OpenAI API key not found, using fallback for {evaluation_type}")
        return None

    try:
        prompt = _construct_evaluation_prompt(
            text, keywords, evaluation_type, page_type, city_name
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": ("You are an expert SEO content evaluator. "
                                "Provide scores (1-10) and detailed explanations.")
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )

        return response.choices[0].message.content
    except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
        print(f"OpenAI API error for {evaluation_type}: {e}")
        return None


def _construct_evaluation_prompt(text: str, keywords: List[str], evaluation_type: str,
                                 page_type: str, city_name: Optional[str] = None) -> str:
    """
    Construct specific prompts for different evaluation types.

    Args:
        text: Content to evaluate
        keywords: List of target keywords
        evaluation_type: Type of evaluation
        page_type: Type of page
        city_name: Name of target city

    Returns:
        Formatted prompt string
    """
    base_info = f"Content Type: {page_type.upper()} PAGE\n"
    base_info += f"Target Keywords: {', '.join(keywords[:5])}\n"

    if city_name:
        base_info += f"Target City: {city_name}\n"

    base_info += f"Content to evaluate (first 1000 chars): {text[:1000]}...\n\n"

    prompts = {
        "grammar_spelling": (
            f"{base_info}Evaluate this content for grammar and spelling quality. "
            "Score 1-10 and provide specific examples of issues found."
        ),
        "readability": (
            f"{base_info}Evaluate readability and flow. Consider sentence length, "
            "paragraph structure, and clarity. Score 1-10 with explanation."
        ),
        "keyword_usage": (
            f"{base_info}Analyze keyword usage and density. Are keywords naturally "
            "integrated? Is there keyword stuffing? Score 1-10."
        ),
        "content_structure": (
            f"{base_info}Evaluate heading structure and content organization. "
            "Are headings logical and SEO-friendly? Score 1-10."
        ),
        "seo_quality": (
            f"{base_info}Overall SEO quality assessment. Consider title optimization, "
            "meta-worthy content, and search intent matching. Score 1-10."
        ),
        "local_relevance": (
            f"{base_info}For this city page, evaluate local relevance and "
            "city-specific information quality. Score 1-10."
        ),
        "pricing_focus": (
            f"{base_info}For this cost page, evaluate how well it focuses on "
            "pricing information and cost-related content. Score 1-10."
        )
    }

    return prompts.get(
        evaluation_type,
        f"{base_info}Evaluate this content for {evaluation_type}. "
        "Score 1-10 with explanation."
    )


def detect_page_type_ai(text: str, keywords: Optional[List[str]] = None) -> str:
    """
    Use AI to detect page type with fallback to rule-based detection.

    Args:
        text: Content to analyze
        keywords: Optional list of keywords

    Returns:
        Page type ('cost' or 'city')
    """
    client = get_openai_client()
    if not client or not client.api_key:
        return _detect_page_type_fallback(text, keywords)

    try:
        keyword_text = ', '.join(keywords[:10]) if keywords else 'None'
        prompt = (
            "Analyze this content and determine if it's a COST page (focused on pricing) "
            "or CITY page (focused on local services).\n\n"
            f"Keywords: {keyword_text}\n"
            f"Content (first 800 chars): {text[:800]}...\n\n"
            "Respond with exactly one word: either 'cost' or 'city' followed by your reasoning."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at classifying web content types."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.1
        )

        result = response.choices[0].message.content.lower()
        if "cost" in result:
            return "cost"
        elif "city" in result:
            return "city"
        else:
            return _detect_page_type_fallback(text, keywords)

    except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
        print(f"AI page type detection failed: {e}, using fallback")
        return _detect_page_type_fallback(text, keywords)


def _detect_page_type_fallback(text: str, keywords: Optional[List[str]] = None) -> str:
    """
    Fallback rule-based page type detection.

    Args:
        text: Content to analyze
        keywords: Optional list of keywords

    Returns:
        Page type ('cost' or 'city')
    """
    text_lower = text.lower()

    cost_indicators = [
        'price', 'cost', 'fee', 'expense', 'tariff', '€', '$', 'kosten', 'prijs'
    ]
    city_indicators = [
        'city', 'local', 'area', 'region', 'district', 'neighborhood'
    ]

    cost_score = sum(
        1 for indicator in cost_indicators if indicator in text_lower)
    city_score = sum(
        1 for indicator in city_indicators if indicator in text_lower)

    if keywords:
        keyword_text = ' '.join(keywords).lower()
        cost_score += sum(1 for indicator in cost_indicators if indicator in keyword_text)
        city_score += sum(1 for indicator in city_indicators if indicator in keyword_text)

    return "cost" if cost_score > city_score else "city"


def evaluate_with_ai_fallback(text: str, keywords: List[str], evaluation_type: str,
                              page_type: str, city_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluate using AI first, then fallback to rule-based if needed.

    Args:
        text: Content to evaluate
        keywords: List of keywords
        evaluation_type: Type of evaluation
        page_type: Page type
        city_name: City name for city pages

    Returns:
        Dictionary with score, details, and method used
    """
    # Try AI evaluation first
    ai_result = call_openai_evaluation(
        text, keywords, evaluation_type, page_type, city_name)

    if ai_result:
        score, details = _parse_ai_response(ai_result)
        return {
            "score": score,
            "details": f"AI: {details}",
            "method": "AI"
        }

    # Fallback to rule-based evaluation
    return _evaluate_rule_based(text, keywords, evaluation_type, page_type, city_name)


def _parse_ai_response(ai_response: str) -> Tuple[int, str]:
    """
    Parse AI response to extract score and explanation.

    Args:
        ai_response: Response from OpenAI API

    Returns:
        Tuple of (score, details)
    """
    try:
        # Look for score patterns
        score_patterns = [
            r'(?:score|rating):\s*(\d+)',
            r'(\d+)\/10',
            r'(\d+)\s*out\s*of\s*10'
        ]

        score = DEFAULT_SCORE
        for pattern in score_patterns:
            match = re.search(pattern, ai_response.lower())
            if match:
                score = min(int(match.group(1)), MAX_SCORE)
                break

        # Clean up the response for details
        details = ai_response.replace('\n', ' ').strip()[:200]
        return score, details

    except (ValueError, AttributeError) as e:
        print(f"Error parsing AI response: {e}")
        return DEFAULT_SCORE, ai_response[:100]


def _evaluate_rule_based(text: str, keywords: List[str], evaluation_type: str,
                         page_type: str, city_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Rule-based evaluation as fallback.

    Args:
        text: Content to evaluate
        keywords: List of keywords
        evaluation_type: Type of evaluation
        page_type: Page type
        city_name: City name for city pages

    Returns:
        Dictionary with score, details, and method
    """
    evaluation_map = {
        "grammar_spelling": _evaluate_grammar_spelling_fallback,
        "readability": _evaluate_readability_fallback,
        "keyword_usage": lambda t, k, *args: _evaluate_keyword_usage_fallback(t, k),
        "content_structure": lambda t, *args: _evaluate_structure_fallback(t),
        "local_relevance": lambda t, k, pt, cn: _evaluate_local_relevance_fallback(t, cn),
        "pricing_focus": lambda t, *args: _evaluate_pricing_focus_fallback(t)
    }

    if evaluation_type in evaluation_map:
        return evaluation_map[evaluation_type](text, keywords, page_type, city_name)

    return {
        "score": DEFAULT_SCORE,
        "details": "Fallback evaluation",
        "method": "Rule-based"
    }


def _evaluate_grammar_spelling_fallback(text: str, keywords: List[str],
                                        page_type: str, city_name: Optional[str]) -> Dict[str, Any]:
    """Fallback grammar evaluation."""
    _ = keywords, page_type, city_name

    issues = 0
    issues += text.count('  ')
    issues += len(re.findall(r'[a-z]\.[A-Z]', text))
    issues += len(re.findall(r'\s+[,.!?]', text))

    score = max(1, MAX_SCORE - issues)
    return {
        "score": score,
        "details": f"Rule-based: Found {issues} potential grammar/spacing issues",
        "method": "Rule-based"
    }


def _evaluate_readability_fallback(text: str, keywords: List[str],
                                   page_type: str, city_name: Optional[str]) -> Dict[str, Any]:
    """Fallback readability evaluation."""
    _ = keywords, page_type, city_name

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    avg_sentence_length = (
        sum(len(s.split()) for s in sentences) / len(sentences)
        if sentences else 0
    )

    if avg_sentence_length <= MAX_SENTENCE_LENGTH:
        score = 9
        details = "Excellent sentence length for readability"
    elif avg_sentence_length <= ACCEPTABLE_SENTENCE_LENGTH:
        score = 7
        details = "Good sentence length"
    else:
        score = 4
        details = "Sentences too long for optimal readability"

    return {
        "score": score,
        "details": (f"Rule-based: {details} "
                    f"(avg: {avg_sentence_length:.1f} words/sentence)"),
        "method": "Rule-based"
    }


def _evaluate_keyword_usage_fallback(text: str, keywords: List[str]) -> Dict[str, Any]:
    """Fallback keyword evaluation."""
    if not keywords:
        return {
            "score": DEFAULT_SCORE,
            "details": "No keywords provided",
            "method": "Rule-based"
        }

    keyword_density = _calculate_keyword_density(text, keywords)

    if KEYWORD_DENSITY_MIN <= keyword_density <= KEYWORD_DENSITY_MAX:
        score = 8
        details = "Good keyword density"
    elif keyword_density < KEYWORD_DENSITY_MIN:
        score = 4
        details = "Keyword density too low"
    else:
        score = 3
        details = "Possible keyword stuffing"

    return {
        "score": score,
        "details": f"Rule-based: {details} ({keyword_density:.1f}%)",
        "method": "Rule-based"
    }


def _evaluate_structure_fallback(text: str) -> Dict[str, Any]:
    """Fallback structure evaluation."""
    h1_count = len(re.findall(r'<h1[^>]*>', text, re.IGNORECASE))
    h2_count = len(re.findall(r'<h2[^>]*>', text, re.IGNORECASE))
    h3_count = len(re.findall(r'<h3[^>]*>', text, re.IGNORECASE))

    score = DEFAULT_SCORE
    details = []

    if h1_count == 1:
        score += 2
        details.append("Good H1 usage")
    elif h1_count == 0:
        details.append("Missing H1")
    else:
        details.append("Multiple H1s found")

    if h2_count >= 2:
        score += 2
        details.append("Good H2 structure")

    if h3_count > 0:
        score += 1
        details.append("Has H3 subheadings")

    return {
        "score": min(score, MAX_SCORE),
        "details": f"Rule-based: {'; '.join(details)}",
        "method": "Rule-based"
    }


def _evaluate_local_relevance_fallback(text: str, city_name: Optional[str]) -> Dict[str, Any]:
    """Fallback local relevance evaluation."""
    if not city_name or city_name == "Unknown City":
        return {
            "score": 3,
            "details": "City name not identified",
            "method": "Rule-based"
        }

    city_mentions = text.lower().count(city_name.lower())
    local_terms = ['local', 'nearby', 'area', 'district', 'region']
    local_score = sum(1 for term in local_terms if term in text.lower())

    score = min(MAX_SCORE, city_mentions + local_score)

    return {
        "score": score,
        "details": (f"Rule-based: {city_mentions} city mentions, "
                    f"{local_score} local terms"),
        "method": "Rule-based"
    }


def _evaluate_pricing_focus_fallback(text: str) -> Dict[str, Any]:
    """Fallback pricing focus evaluation."""
    price_terms = ['cost', 'price', 'fee', 'expense', '€', '$']
    price_score = sum(1 for term in price_terms if term in text.lower())

    price_patterns = [r'€\s*\d+', r'\$\s*\d+', r'price.*\d+']
    pattern_matches = sum(
        1 for pattern in price_patterns
        if re.search(pattern, text, re.IGNORECASE)
    )

    score = min(MAX_SCORE, price_score + pattern_matches)

    return {
        "score": score,
        "details": (f"Rule-based: {price_score} price terms, "
                    f"{pattern_matches} price patterns"),
        "method": "Rule-based"
    }


def extract_city_name(text: str, keywords: List[str]) -> str:
    """Extract city name from keywords or text."""
    for keyword in keywords:
        city_match = re.search(
            r'\b(?:in|te)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            keyword
        )
        if city_match:
            return city_match.group(1)

    city_patterns = [
        r'\b(?:in|te)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:area|region|city)'
    ]

    for pattern in city_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return "Unknown City"


def evaluate_checklist(text: str, keywords: List[str], page_type: str) -> Dict[str, Any]:
    """Evaluate content against the appropriate checklist."""
    if page_type == "cost":
        return _evaluate_cost_page(text, keywords)
    else:
        city_name = extract_city_name(text, keywords)
        return _evaluate_city_page(text, keywords, city_name)


def _evaluate_cost_page(text: str, keywords: List[str]) -> Dict[str, Any]:
    """Evaluate a cost page using AI with fallbacks."""
    results = {}

    evaluation_types = [
        "grammar_spelling", "readability", "keyword_usage",
        "content_structure", "seo_quality", "pricing_focus"
    ]

    for eval_type in evaluation_types:
        results[eval_type] = evaluate_with_ai_fallback(
            text, keywords, eval_type, "cost"
        )

    results["internal_linking"] = _evaluate_internal_linking(text)
    results["formatting"] = _evaluate_formatting(text)

    return results


def _evaluate_city_page(text: str, keywords: List[str], city_name: str) -> Dict[str, Any]:
    """Evaluate a city page using AI with fallbacks."""
    results = {}

    evaluation_types = [
        "grammar_spelling", "readability", "keyword_usage",
        "content_structure", "seo_quality", "local_relevance"
    ]

    for eval_type in evaluation_types:
        results[eval_type] = evaluate_with_ai_fallback(
            text, keywords, eval_type, "city", city_name
        )

    results["internal_linking"] = _evaluate_internal_linking(text)
    results["formatting"] = _evaluate_formatting(text)

    return results


def _evaluate_internal_linking(text: str) -> Dict[str, Any]:
    """Evaluate internal linking strategy."""
    score = 0
    details = []

    link_pattern = re.compile(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        re.IGNORECASE
    )
    links = link_pattern.findall(text)

    top10_links = sum(
        1 for _, link_text in links
        if "top 10" in link_text.lower() or "top ten" in link_text.lower()
    )
    cost_links = sum(
        1 for _, link_text in links
        if any(word in link_text.lower()
               for word in ["cost", "price", "kosten", "prijs"])
    )

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

    nearby_links = sum(
        1 for _, link_text in links
        if any(word in link_text.lower()
               for word in ["nearby", "other cities", "region"])
    )
    if nearby_links > 0:
        score += 2
        details.append("✓ Links to nearby locations")

    if len(links) >= 5:
        score += 1
        details.append("✓ Good internal linking quantity")

    return {
        "score": min(score, MAX_SCORE),
        "details": "; ".join(details)
    }


def _evaluate_formatting(text: str) -> Dict[str, Any]:
    """Evaluate formatting and specific guidelines."""
    score = DEFAULT_SCORE
    details = []

    price_patterns = [r'€\s*\d+,-', r'€\s*\d+\.\d+,-', r'€\s*\d+,\d+']
    correct_prices = sum(
        1 for pattern in price_patterns
        if re.search(pattern, text)
    )
    if correct_prices > 0:
        score += 2
        details.append("✓ Correct price formatting")

    if re.search(r'\d+%', text):
        score += 1
        details.append("✓ Correct percentage formatting")

    score += 1
    details.append("✓ Assuming correct number formatting")

    bullet_patterns = [r'^\s*[-•*]\s+', r'^\s*\d+\.\s+']
    if any(re.search(pattern, text, re.MULTILINE) for pattern in bullet_patterns):
        score += 1
        details.append("✓ Has formatted bullet points")

    return {
        "score": min(score, MAX_SCORE),
        "details": "; ".join(details)
    }


def _calculate_keyword_density(text: str, keywords: List[str]) -> float:
    """Calculate keyword density percentage."""
    if not keywords:
        return 0.0

    word_count = len(text.split())
    keyword_count = sum(
        text.lower().count(keyword.lower())
        for keyword in keywords
    )

    return (keyword_count / word_count * 100) if word_count > 0 else 0.0


def generate_ai_suggestions(text: str, keywords: List[str],
                            checklist_results: Dict[str, Any],
                            page_type: str) -> List[str]:
    """Generate improvement suggestions using AI."""
    client = get_openai_client()
    if not client or not client.api_key:
        return _generate_improvement_suggestions_fallback(checklist_results, page_type)

    try:
        low_scores = [
            (item, result["score"])
            for item, result in checklist_results.items()
            if isinstance(result, dict)
            and "score" in result
            and result["score"] < 7
        ]

        problem_areas = [
            item.replace("_", " ")
            for item, score in low_scores
        ]

        prompt = (
            f"Based on this SEO evaluation of a {page_type} page, provide exactly 5 "
            "specific, actionable improvement suggestions.\n\n"
            f"Problem areas identified: {', '.join(problem_areas)}\n"
            f"Keywords: {', '.join(keywords[:5])}\n"
            f"Content sample: {text[:500]}...\n\n"
            "Provide 5 numbered suggestions that are:\n"
            "1. Specific and actionable\n"
            "2. Focused on the lowest-scoring areas\n"
            "3. SEO-focused\n"
            "4. Realistic to implement\n\n"
            "Format as:\n1. [suggestion]\n2. [suggestion]\n...etc"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": ("You are an expert SEO consultant providing "
                                "actionable improvement advice.")
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.5
        )

        suggestions_text = response.choices[0].message.content
        suggestions = []

        for line in suggestions_text.split('\n'):
            if re.match(r'^\d+\.', line.strip()):
                suggestion = re.sub(r'^\d+\.\s*', '', line.strip())
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions[:5]

    except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
        print(f"AI suggestion generation failed: {e}, using fallback")
        return _generate_improvement_suggestions_fallback(checklist_results, page_type)


def _generate_improvement_suggestions_fallback(checklist_results: Dict[str, Any],
                                               _page_type: str) -> List[str]:
    """Fallback suggestion generation."""
    suggestions = []

    low_scores = [
        (item, result) for item, result in checklist_results.items()
        if isinstance(result, dict) and "score" in result and result["score"] < 7
    ]

    low_scores.sort(key=lambda x: x[1]["score"])

    suggestion_map = {
        "grammar_spelling": ("Review and correct grammar and spelling errors "
                             "throughout the content"),
        "readability": ("Improve readability by using shorter sentences "
                        "and simpler language"),
        "keyword_usage": ("Optimize keyword placement and density "
                          "for better SEO performance"),
        "content_structure": "Improve heading structure and content organization",
        "seo_quality": ("Enhance overall SEO elements including title "
                        "and meta descriptions"),
        "local_relevance": ("Add more city-specific information "
                            "and local business advantages"),
        "pricing_focus": ("Strengthen focus on pricing information "
                          "and cost-related content")
    }

    for item, result in low_scores[:5]:
        if item in suggestion_map:
            suggestions.append(suggestion_map[item])

    return suggestions


def main() -> None:
    """Main function to run the SEO proofreader."""
    parser = argparse.ArgumentParser(
        description='SEO Proofreader Tool with AI')
    parser.add_argument('--doc_id', required=True, help='Google Doc ID')
    parser.add_argument(
        '--keywords_sheet',
        required=True,
        help='Google Sheet ID with keywords'
    )
    parser.add_argument(
        '--page_type',
        choices=['cost', 'city'],
        help='Force page type (optional)'
    )

    args = parser.parse_args()

    client = get_openai_client()
    if client and client.api_key:
        print("✓ OpenAI API key found - using AI-powered evaluation")
    else:
        print("⚠ OpenAI API key not found - using rule-based fallbacks")

    docs_service, sheets_service = authenticate_google()
    if not docs_service or not sheets_service:
        return

    try:
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

        page_type = args.page_type or detect_page_type_ai(text, keywords)
        print(f"Page type detected: {page_type}")

        print("Evaluating content with AI...")
        checklist_results = evaluate_checklist(text, keywords, page_type)

        print("Generating AI-powered suggestions...")
        suggestions = generate_ai_suggestions(
            text, keywords, checklist_results, page_type)

        print("Generating report...")
        report = generate_report(
            text, keywords, checklist_results, suggestions, page_type)

        output_filename = f"report_{args.doc_id}.md"
        with open(output_filename, 'w', encoding='utf-8') as output_file:
            output_file.write(report)

        print(f"Report saved as {output_filename}")

    except Exception as e:
        print(f"Error during execution: {e}")
        raise SEOEvaluationError(
            f"Failed to complete SEO evaluation: {e}") from e


if __name__ == "__main__":
    main()
