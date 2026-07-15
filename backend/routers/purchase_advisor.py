# backend/routers/purchase_advisor.py
"""
Smart Purchase Advisor — compares user-provided prices across sources,
generates structured ratings, and ties the decision to real budget data.

Design: User provides prices (no scraping needed — user-fed comparison).
        Gemini generates ratings from general knowledge, clearly framed as guidance.
        check_affordability() ties it to real budget — deterministic, not LLM math.
"""

from google import genai
from google.genai import types
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dependencies import get_current_user, supabase
from calculator import check_affordability, get_month_day_info
from datetime import date
from dotenv import load_dotenv
import os
import json

load_dotenv()

router = APIRouter(prefix="/advisor", tags=["Purchase Advisor"])


# ── Request Models ────────────────────────────────────────────

class PriceOption(BaseModel):
    source: str       # e.g. "Amazon", "Flipkart", "Local store"
    price: float      # Price in rupees


class PurchaseAdvisorRequest(BaseModel):
    product_name: str
    price_options: List[PriceOption]   # Min 1, ideally 2-3
    intended_use: Optional[str] = None # e.g. "daily commute", "gaming"


# ── Financial Context Helper ──────────────────────────────────

async def _get_budget_context(user_id: str) -> dict:
    """Fetches minimal budget context needed for affordability check."""
    today = date.today()
    first_of_month = today.replace(day=1)

    budget_r = supabase.table("monthly_budgets") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("month", str(first_of_month)) \
        .execute()

    if not budget_r.data:
        return None

    budget = budget_r.data[0]

    txn_r = supabase.table("transactions") \
        .select("amount") \
        .eq("user_id", user_id) \
        .gte("txn_date", str(first_of_month)) \
        .execute()

    comm_r = supabase.table("recurring_commitments") \
        .select("amount") \
        .eq("user_id", user_id) \
        .eq("month", str(first_of_month)) \
        .eq("is_paid", False) \
        .execute()

    total_spent  = sum(abs(t["amount"]) for t in txn_r.data if t["amount"] < 0)
    total_income = sum(t["amount"]      for t in txn_r.data if t["amount"] > 0)
    unpaid_total = sum(c["amount"]      for c in comm_r.data)
    current_balance = budget["opening_balance"] - total_spent + total_income

    return {
        "current_balance":    round(current_balance, 2),
        "savings_goal":       budget["savings_goal"],
        "unpaid_commitments": round(unpaid_total, 2),
        "day_info":           get_month_day_info(today)
    }


# ── Star Rating Generator ─────────────────────────────────────

def _generate_ratings(
    product_name: str,
    intended_use: Optional[str]
) -> dict:
    """
    Generates structured 1-5 star ratings using Gemini.
    Framed as general guidance from training knowledge — not live reviews.
    Returns strict JSON with 5 rating dimensions.
    """

    use_context = f" for {intended_use}" if intended_use else ""

    prompt = (
        f"You are a product advisor. Rate '{product_name}'{use_context} "
        f"based on your general knowledge.\n\n"
        f"Return ONLY this JSON with integer scores 1-5:\n"
        f'{{"quality": 0, "durability": 0, "value_for_money": 0, '
        f'"ease_of_use": 0, "overall": 0, '
        f'"one_line_summary": "brief summary here", '
        f'"buy_recommendation": "yes/no/wait"}}\n\n'
        f"Scoring guide:\n"
        f"5 = excellent, 4 = good, 3 = average, 2 = below average, 1 = poor\n"
        f"buy_recommendation: yes=buy now, no=avoid, wait=wait for sale/better option\n"
        f"Return ONLY the JSON, no explanation."
    )

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=300,
            )
        )

        raw = response.text.strip()

        # Clean markdown fences
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        ratings = json.loads(raw)

        # Validate all required fields exist
        required = ["quality", "durability", "value_for_money",
                    "ease_of_use", "overall", "one_line_summary",
                    "buy_recommendation"]
        for field in required:
            if field not in ratings:
                ratings[field] = 3 if field not in [
                    "one_line_summary", "buy_recommendation"
                ] else "insufficient data"

        # Clamp scores to 1-5
        for score_field in ["quality", "durability", "value_for_money",
                            "ease_of_use", "overall"]:
            ratings[score_field] = max(1, min(5, int(ratings[score_field])))

        return {"success": True, "ratings": ratings}

    except Exception as e:
        # Fallback ratings if Gemini fails
        print(f"[advisor] Rating generation failed: {e}")
        return {
            "success": False,
            "ratings": {
                "quality": 3, "durability": 3, "value_for_money": 3,
                "ease_of_use": 3, "overall": 3,
                "one_line_summary": "Rating unavailable — general guidance only.",
                "buy_recommendation": "wait"
            }
        }


# ── Price Comparison Logic ────────────────────────────────────

def _compare_prices(price_options: List[PriceOption]) -> dict:
    """
    Pure Python price comparison — no LLM needed.
    Deterministic: finds cheapest, most expensive, savings amount.
    """
    if not price_options:
        return {}

    sorted_options = sorted(price_options, key=lambda x: x.price)
    cheapest   = sorted_options[0]
    most_exp   = sorted_options[-1]
    max_saving = round(most_exp.price - cheapest.price, 2)

    return {
        "cheapest_option":    {"source": cheapest.source,  "price": cheapest.price},
        "most_expensive":     {"source": most_exp.source,  "price": most_exp.price},
        "max_savings":        max_saving,
        "all_options_sorted": [
            {"source": o.source, "price": o.price}
            for o in sorted_options
        ],
        "recommendation": (
            f"Buy from {cheapest.source} — saves ₹{max_saving} "
            f"vs {most_exp.source}."
            if len(price_options) > 1
            else f"Only one price provided: ₹{cheapest.price} from {cheapest.source}."
        )
    }


# ── Main Advisor Route ────────────────────────────────────────

@router.post("/analyze")
async def analyze_purchase(
    body: PurchaseAdvisorRequest,
    user=Depends(get_current_user)
):
    """
    Full purchase analysis:
    1. Price comparison across user-provided sources (deterministic)
    2. Structured star ratings from Gemini general knowledge
    3. Affordability check against real budget data
    4. Final buy/wait/skip recommendation
    """

    # Validate inputs
    if not body.price_options:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one price option."
        )

    # Step 1: Compare prices (pure Python — no LLM)
    price_comparison = _compare_prices(body.price_options)
    cheapest_price   = price_comparison["cheapest_option"]["price"]

    # Step 2: Generate star ratings (Gemini)
    rating_result = _generate_ratings(body.product_name, body.intended_use)
    ratings = rating_result["ratings"]

    # Step 3: Check affordability against real budget
    budget_ctx = await _get_budget_context(str(user.id))

    if budget_ctx:
        affordability = check_affordability(
            current_balance=budget_ctx["current_balance"],
            unpaid_commitments_total=budget_ctx["unpaid_commitments"],
            savings_goal=budget_ctx["savings_goal"],
            days_remaining=budget_ctx["day_info"]["days_remaining"],
            proposed_expense=cheapest_price,
            proposed_expense_description=body.product_name
        )
    else:
        # No budget set — skip affordability check
        affordability = {
            "can_afford":  None,
            "verdict":     "No budget set. Call POST /budget/start-month to enable affordability checks.",
            "daily_safe_after": None
        }

    # Step 4: Build final recommendation
    can_afford      = affordability.get("can_afford")
    buy_rec         = ratings.get("buy_recommendation", "wait")
    overall_score   = ratings.get("overall", 3)

    if can_afford is True and buy_rec == "yes" and overall_score >= 4:
        final_verdict = "✅ BUY NOW — Good product, good price, within budget."
    elif can_afford is True and buy_rec in ["yes", "wait"] and overall_score >= 3:
        final_verdict = "✅ OKAY TO BUY — Budget allows it, product is decent."
    elif can_afford is False:
        final_verdict = "❌ SKIP FOR NOW — This purchase would affect your savings goal."
    elif buy_rec == "no":
        final_verdict = "⚠️ AVOID — Product not recommended regardless of budget."
    else:
        final_verdict = "⏳ WAIT — Consider waiting for a sale or better alternative."

    return {
        "product":          body.product_name,
        "intended_use":     body.intended_use,
        "price_comparison": price_comparison,
        "ratings": {
            "note":    "General guidance based on AI training knowledge — not live reviews.",
            "scores":  ratings,
            "stars": {
                "quality":         f"{'⭐' * ratings['quality']}{'☆' * (5 - ratings['quality'])}",
                "durability":      f"{'⭐' * ratings['durability']}{'☆' * (5 - ratings['durability'])}",
                "value_for_money": f"{'⭐' * ratings['value_for_money']}{'☆' * (5 - ratings['value_for_money'])}",
                "ease_of_use":     f"{'⭐' * ratings['ease_of_use']}{'☆' * (5 - ratings['ease_of_use'])}",
                "overall":         f"{'⭐' * ratings['overall']}{'☆' * (5 - ratings['overall'])}",
            }
        },
        "affordability":    affordability,
        "final_verdict":    final_verdict,
        "summary": (
            f"{body.product_name} — best price at "
            f"{price_comparison['cheapest_option']['source']} "
            f"(₹{cheapest_price}). "
            f"Overall rating: {ratings['overall']}/5. "
            f"{final_verdict}"
        )
    }


# ── Quick Affordability Only Route ────────────────────────────

@router.post("/can-i-buy")
async def can_i_buy(
    body: PurchaseAdvisorRequest,
    user=Depends(get_current_user)
):
    """
    Lightweight version — just affordability check, no ratings.
    Faster response when user only wants budget verdict.
    """
    if not body.price_options:
        raise HTTPException(status_code=400, detail="Provide at least one price.")

    cheapest_price = min(o.price for o in body.price_options)
    cheapest_source = min(body.price_options, key=lambda x: x.price).source

    budget_ctx = await _get_budget_context(str(user.id))

    if not budget_ctx:
        raise HTTPException(
            status_code=404,
            detail="No budget set. Call POST /budget/start-month first."
        )

    result = check_affordability(
        current_balance=budget_ctx["current_balance"],
        unpaid_commitments_total=budget_ctx["unpaid_commitments"],
        savings_goal=budget_ctx["savings_goal"],
        days_remaining=budget_ctx["day_info"]["days_remaining"],
        proposed_expense=cheapest_price,
        proposed_expense_description=f"{body.product_name} from {cheapest_source}"
    )

    return {
        "product":        body.product_name,
        "cheapest_price": cheapest_price,
        "cheapest_from":  cheapest_source,
        "can_afford":     result["can_afford"],
        "verdict":        result["verdict"],
        "daily_safe_after": result["daily_safe_after"]
    }