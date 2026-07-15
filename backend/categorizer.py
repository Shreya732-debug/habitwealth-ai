# backend/categorizer.py
from google import genai
from dotenv import load_dotenv
import os
from calculator import VALID_CATEGORIES

# Add this dictionary at the top of categorizer.py after VALID_CATEGORIES import

KEYWORD_RULES = {
    "food": [
        "zomato",
        "swiggy",
        "restaurant",
        "biryani",
        "food",
        "cafe",
        "pizza",
        "burger",
        "lunch",
        "dinner",
        "breakfast",
    ],
    "transport": [
        "uber",
        "ola",
        "rapido",
        "metro",
        "bus",
        "fuel",
        "petrol",
        "cab",
        "auto",
    ],
    "subscriptions": [
        "netflix",
        "spotify",
        "prime",
        "hotstar",
        "subscription",
        "renewal",
    ],
    "shopping": ["amazon", "flipkart", "myntra", "shopping", "purchase", "mall"],
    "health": ["pharmacy", "medical", "doctor", "hospital", "clinic", "medicine"],
    "utilities": [
        "electricity",
        "water",
        "internet",
        "wifi",
        "phone bill",
        "recharge",
        "broadband",
    ],
    "rent": ["rent", "house", "pg", "hostel", "accommodation"],
    "transfer": [
        "transfer",
        "sent to",
        "neft",
        "imps",
        "upi",
        "gpay",
        "phonepe",
        "paytm",
    ],
    "education": ["course", "udemy", "coursera", "fee", "book", "stationery"],
    "entertainment": ["movie", "cinema", "pvr", "inox", "gaming", "concert"],
}


def _rule_based_category(description: str) -> str:
    """Fast keyword-based fallback — no API call needed."""
    desc_lower = description.lower()
    for category, keywords in KEYWORD_RULES.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "other"


load_dotenv()


def categorize_transaction(description: str, amount: float) -> str:
    """
    Categorizes a transaction using Gemini Flash.
    Returns a category from VALID_CATEGORIES.
    Falls back to 'other' on any error.
    """

    # Positive amount = income, no LLM needed
    if amount > 0:
        return "income"

    if not description or not description.strip():
        return "other"

    categories_str = ", ".join(VALID_CATEGORIES)

    prompt = (
        f"You are categorizing Indian bank transactions.\n"
        f"Transaction description: '{description}'\n"
        f"Pick exactly one category from this list: {categories_str}\n"
        f"Rules:\n"
        f"- Netflix, Spotify, Amazon Prime = subscriptions\n"
        f"- Zomato, Swiggy, restaurant = food\n"
        f"- Uber, Ola, fuel, metro = transport\n"
        f"- Electricity, water, internet, phone bill = utilities\n"
        f"- Pharmacy, doctor, hospital = health\n"
        f"- Sent to person, transferred = transfer\n"
        f"- Salary, freelance received = income\n"
        f"Reply with only one word — the category name."
    )

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            # No GenerateContentConfig — let the model use defaults
        )

        # Safety check before accessing text
        if not response.candidates:
            return "other"

        candidate = response.candidates[0]

        # Check finish reason — STOP=1 is normal
        if str(candidate.finish_reason) not in ["FinishReason.STOP", "1", "STOP"]:
            print(f"[categorizer] finish_reason={candidate.finish_reason}")
            return "other"

        raw = response.text.strip().lower()
        raw = raw.replace(".", "").replace(",", "").replace('"', "").strip()

        if raw in VALID_CATEGORIES:
            return raw

        # Partial match fallback
        for cat in VALID_CATEGORIES:
            if cat in raw:
                return cat

        print(f"[categorizer] Unknown: '{raw}'")
        return "other"

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            # Rate limited — use fast keyword fallback instead
            fallback = _rule_based_category(description)
            print(f"[categorizer] Rate limited — using keyword fallback: '{fallback}'")
            return fallback
        print(f"[categorizer] Error: {e}")
        return "other"
