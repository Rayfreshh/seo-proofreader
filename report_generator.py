import datetime


def generate_report(text, keywords, checklist_results, suggestions, page_type):
    """Generate a comprehensive report from the evaluation results."""

    # Calculate overall score
    total_score = 0
    max_possible = 0

    for item, result in checklist_results.items():
        if isinstance(result, dict) and "score" in result:
            total_score += result["score"]
            max_possible += 10

    if max_possible > 0:
        percentage = (total_score / max_possible) * 100
    else:
        percentage = 0

    # Determine pass/fail
    status = "PASS" if percentage >= 70 else "FAIL"

    # Create report
    report = []

    # Header
    report.append("# SEO Proofreader Report")
    report.append(
        f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Page Type: {page_type.upper()} PAGE")
    report.append(f"Overall Score: {percentage:.1f}% ({status})")
    report.append("\n---\n")

    # Keywords section
    report.append("## Target Keywords")
    for keyword in keywords[:10]:  # Show top 10 keywords
        report.append(f"- {keyword}")
    if len(keywords) > 10:
        report.append(f"- ... and {len(keywords) - 10} more")
    report.append("\n---\n")

    # Checklist Results
    report.append("## Evaluation Results")

    for item, result in checklist_results.items():
        if isinstance(result, dict) and "score" in result:
            score = result["score"]
            details = result.get("details", "")

            # Format checklist item name
            item_name = item.replace("_", " ").title()

            # Score emoji
            if score >= 8:
                emoji = "✅"
            elif score >= 5:
                emoji = "⚠️"
            else:
                emoji = "❌"

            report.append(f"### {emoji} {item_name}: {score}/10")
            report.append(f"{details}\n")

    report.append("\n---\n")

    # Improvement Suggestions
    report.append("## Top Improvement Suggestions")

    if not suggestions:
        report.append("No specific improvements needed.")
    else:
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"{i}. {suggestion}")

    # Join all sections
    return "\n".join(report)
