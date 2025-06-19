"""
Report Generator Module

This module generates comprehensive SEO evaluation reports in Markdown format
with visual indicators, charts, and detailed analysis results.
"""

import datetime
from typing import Dict, List, Any, Optional


# Constants
PASS_THRESHOLD = 70.0
MAX_SCORE = 10
GOOD_SCORE_THRESHOLD = 8
NEEDS_IMPROVEMENT_THRESHOLD = 5
PREVIEW_LENGTH = 300
MAX_KEYWORDS_DISPLAY = 10
CHART_BAR_LENGTH = 10
ITEM_NAME_MAX_LENGTH = 20


def generate_report(text: str, keywords: List[str], checklist_results: Dict[str, Any],
                    suggestions: List[str], page_type: str) -> str:
    """
    Generate a comprehensive report from the evaluation results.

    Args:
        text: Original content text
        keywords: List of target keywords
        checklist_results: Dictionary of evaluation results
        suggestions: List of improvement suggestions
        page_type: Type of page ('cost' or 'city')

    Returns:
        Complete markdown report as string
    """
    overall_score = _calculate_overall_score(checklist_results)
    status = "PASS" if overall_score >= PASS_THRESHOLD else "FAIL"

    report_sections = [
        _generate_header(page_type, overall_score, status),
        _generate_content_preview(text),
        _generate_keywords_section(keywords),
        _generate_score_summary_table(checklist_results),
        _generate_score_breakdown_chart(checklist_results),
        _generate_detailed_results(checklist_results),
        _generate_improvement_suggestions(suggestions)
    ]

    return "\n".join(report_sections)


def _calculate_overall_score(checklist_results: Dict[str, Any]) -> float:
    """
    Calculate overall percentage score from checklist results.

    Args:
        checklist_results: Dictionary of evaluation results

    Returns:
        Overall score as percentage
    """
    total_score = 0
    max_possible = 0

    for result in checklist_results.values():
        if isinstance(result, dict) and "score" in result:
            total_score += result["score"]
            max_possible += MAX_SCORE

    return (total_score / max_possible * 100) if max_possible > 0 else 0.0


def _generate_header(page_type: str, overall_score: float, status: str) -> str:
    """
    Generate report header section.

    Args:
        page_type: Type of page
        overall_score: Overall percentage score
        status: Pass/fail status

    Returns:
        Formatted header section
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    header_lines = [
        "# SEO Proofreader Report",
        f"Generated on: {timestamp}",
        f"Page Type: {page_type.upper()} PAGE",
        f"Overall Score: {overall_score:.1f}% ({status})",
        "\n---\n"
    ]

    return "\n".join(header_lines)


def _generate_content_preview(text: str) -> str:
    """
    Generate content preview section.

    Args:
        text: Original content text

    Returns:
        Formatted content preview section
    """
    preview_length = min(PREVIEW_LENGTH, len(text))
    preview_text = text[:preview_length]

    if len(text) > PREVIEW_LENGTH:
        preview_text += "..."

    preview_lines = [
        "## Content Preview",
        f"```\n{preview_text}\n```",
        "\n---\n"
    ]

    return "\n".join(preview_lines)


def _generate_keywords_section(keywords: List[str]) -> str:
    """
    Generate keywords section.

    Args:
        keywords: List of target keywords

    Returns:
        Formatted keywords section
    """
    keywords_lines = ["## Target Keywords"]

    # Display up to MAX_KEYWORDS_DISPLAY keywords
    display_keywords = keywords[:MAX_KEYWORDS_DISPLAY]
    for keyword in display_keywords:
        keywords_lines.append(f"- {keyword}")

    # Add count for remaining keywords if any
    if len(keywords) > MAX_KEYWORDS_DISPLAY:
        remaining_count = len(keywords) - MAX_KEYWORDS_DISPLAY
        keywords_lines.append(f"- ... and {remaining_count} more")

    keywords_lines.extend(["\n---\n"])

    return "\n".join(keywords_lines)


def _generate_score_summary_table(checklist_results: Dict[str, Any]) -> str:
    """
    Generate score summary table.

    Args:
        checklist_results: Dictionary of evaluation results

    Returns:
        Formatted score summary table
    """
    table_lines = [
        "## Score Summary",
        "| Criteria | Score | Status |",
        "|----------|-------|--------|"
    ]

    for item_name, result in checklist_results.items():
        if isinstance(result, dict) and "score" in result:
            score = result["score"]
            formatted_name = _format_item_name(item_name)
            status = _get_score_status(score)

            table_lines.append(
                f"| {formatted_name} | {score}/{MAX_SCORE} | {status} |")

    table_lines.extend(["\n---\n"])

    return "\n".join(table_lines)


def _generate_score_breakdown_chart(checklist_results: Dict[str, Any]) -> str:
    """
    Generate visual score breakdown chart.

    Args:
        checklist_results: Dictionary of evaluation results

    Returns:
        Formatted score breakdown chart
    """
    chart_lines = ["## Score Breakdown"]

    for item_name, result in checklist_results.items():
        if isinstance(result, dict) and "score" in result:
            score = result["score"]
            formatted_name = _format_item_name(
                item_name, max_length=ITEM_NAME_MAX_LENGTH)
            name_padded = formatted_name.ljust(ITEM_NAME_MAX_LENGTH)

            # Create visual progress indicator
            filled_bars = "█" * score
            empty_bars = "░" * (CHART_BAR_LENGTH - score)
            progress_indicator = filled_bars + empty_bars

            chart_lines.append(
                f"{name_padded} |{progress_indicator}| {score}/{MAX_SCORE}")

    chart_lines.extend(["\n---\n"])

    return "\n".join(chart_lines)


def _generate_detailed_results(checklist_results: Dict[str, Any]) -> str:
    """
    Generate detailed evaluation results section.

    Args:
        checklist_results: Dictionary of evaluation results

    Returns:
        Formatted detailed results section
    """
    results_lines = ["## Detailed Evaluation Results"]

    for item_name, result in checklist_results.items():
        if isinstance(result, dict) and "score" in result:
            score = result["score"]
            details = result.get("details", "No details available")

            formatted_name = _format_item_name(item_name)
            emoji = _get_score_emoji(score)

            results_lines.extend([
                f"### {emoji} {formatted_name}: {score}/{MAX_SCORE}",
                f"{details}\n"
            ])

    results_lines.extend(["\n---\n"])

    return "\n".join(results_lines)


def _generate_improvement_suggestions(suggestions: List[str]) -> str:
    """
    Generate improvement suggestions section.

    Args:
        suggestions: List of improvement suggestions

    Returns:
        Formatted suggestions section
    """
    suggestions_lines = ["## Top Improvement Suggestions"]

    if not suggestions:
        suggestions_lines.append("No specific improvements needed.")
    else:
        for i, suggestion in enumerate(suggestions, 1):
            suggestions_lines.append(f"{i}. {suggestion}")

    return "\n".join(suggestions_lines)


def _format_item_name(item_name: str, max_length: Optional[int] = None) -> str:
    """
    Format checklist item name for display.

    Args:
        item_name: Raw item name with underscores
        max_length: Optional maximum length for truncation

    Returns:
        Formatted item name
    """
    formatted_name = item_name.replace("_", " ").title()

    if max_length and len(formatted_name) > max_length:
        formatted_name = formatted_name[:max_length]

    return formatted_name


def _get_score_status(score: int) -> str:
    """
    Get status indicator for score.

    Args:
        score: Numeric score

    Returns:
        Status string with emoji
    """
    if score >= GOOD_SCORE_THRESHOLD:
        return "✅ Good"
    elif score >= NEEDS_IMPROVEMENT_THRESHOLD:
        return "⚠️ Needs Improvement"
    else:
        return "❌ Poor"


def _get_score_emoji(score: int) -> str:
    """
    Get emoji indicator for score.

    Args:
        score: Numeric score

    Returns:
        Emoji string
    """
    if score >= GOOD_SCORE_THRESHOLD:
        return "✅"
    elif score >= NEEDS_IMPROVEMENT_THRESHOLD:
        return "⚠️"
    else:
        return "❌"


def generate_summary_stats(checklist_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate summary statistics from checklist results.

    Args:
        checklist_results: Dictionary of evaluation results

    Returns:
        Dictionary containing summary statistics
    """
    scores = []
    for result in checklist_results.values():
        if isinstance(result, dict) and "score" in result:
            scores.append(result["score"])

    if not scores:
        return {
            "total_items": 0,
            "average_score": 0.0,
            "min_score": 0,
            "max_score": 0,
            "passing_items": 0,
            "failing_items": 0
        }

    average_score = sum(scores) / len(scores)
    passing_items = sum(1 for score in scores if score >=
                        NEEDS_IMPROVEMENT_THRESHOLD)
    failing_items = len(scores) - passing_items

    return {
        "total_items": len(scores),
        "average_score": average_score,
        "min_score": min(scores),
        "max_score": max(scores),
        "passing_items": passing_items,
        "failing_items": failing_items
    }


def export_results_json(checklist_results: Dict[str, Any],
                        suggestions: List[str],
                        page_type: str) -> Dict[str, Any]:
    """
    Export results in JSON format for API usage.

    Args:
        checklist_results: Dictionary of evaluation results
        suggestions: List of improvement suggestions
        page_type: Type of page

    Returns:
        Dictionary suitable for JSON serialization
    """
    overall_score = _calculate_overall_score(checklist_results)
    summary_stats = generate_summary_stats(checklist_results)

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "page_type": page_type.upper(),
        "overall_score": round(overall_score, 1),
        "status": "PASS" if overall_score >= PASS_THRESHOLD else "FAIL",
        "summary_stats": summary_stats,
        "detailed_results": checklist_results,
        "suggestions": suggestions
    }
