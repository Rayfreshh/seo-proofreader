from seo_proofreader import detect_page_type_ai, evaluate_checklist, generate_ai_suggestions
from report_generator import generate_report
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Sample content (no API key here!)
sample_text = """
Professional House Cleaning Services in Amsterdam - Competitive Prices

Welcome to our comprehensive cost analysis for house cleaning services in Amsterdam. 
Our professional cleaning team offers competitive rates starting at €25 per hour.

Price Structure:
- Basic cleaning: €25-30 per hour
- Deep cleaning: €35-40 per hour  
- One-time cleaning: €75-150 depending on house size
- Weekly service: 15% discount on hourly rates

We provide transparent pricing with no hidden fees. Our experienced cleaners use eco-friendly products and guarantee satisfaction. Contact us today for a free quote tailored to your specific cleaning needs.

Service Areas:
We serve all districts of Amsterdam including city center, Noord, Zuid, and surrounding areas.
"""

sample_keywords = [
    "house cleaning Amsterdam",
    "cleaning service cost Amsterdam",
    "professional cleaning prices",
    "cleaning rates Amsterdam",
    "house cleaning cost"
]


def test_ai_seo_tool():
    # Check if API key is loaded from .env
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in .env file!")
        print("💡 Make sure you have a .env file with: OPENAI_API_KEY=your-key-here")
        return

    print("🤖 Testing AI-Powered SEO Proofreader")
    print("=" * 50)

    # Test page type detection with AI
    print("1. AI Page Type Detection...")
    page_type = detect_page_type_ai(sample_text, sample_keywords)
    print(f"   ✅ Page type detected: {page_type}")

    # Continue with rest of tests...


if __name__ == "__main__":
    test_ai_seo_tool()
