# backend/routers/transactions.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dependencies import get_current_user, supabase
from datetime import date
from decimal import Decimal
from typing import Optional
from categorizer import categorize_transaction  # NEW import

router = APIRouter(prefix="/transactions", tags=["Transactions"])


class AddTransactionRequest(BaseModel):
    amount: Decimal
    description: str
    category: Optional[str] = None   # User can still override manually
    txn_date: date


@router.post("/add")
async def add_transaction(
    body: AddTransactionRequest,
    user=Depends(get_current_user)
):
    """
    Add a manual transaction.
    If category is not provided, auto-categorizes using Gemini Flash.
    """

    # Auto-categorize if user didn't manually specify a category
    if body.category is None or body.category.strip() == "":
        # This is the AI call — fast, cheap, falls back to "other" on failure
        auto_category = categorize_transaction(
            description=body.description,
            amount=float(body.amount)
        )
        final_category = auto_category
    else:
        # User specified a category manually — respect that, skip AI call
        final_category = body.category.lower().strip()

    result = supabase.table("transactions").insert({
        "user_id":     str(user.id),
        "amount":      float(body.amount),
        "description": body.description,
        "category":    final_category,
        "txn_date":    str(body.txn_date),
        "source":      "manual"
    }).execute()

    return {
        "message":             "Transaction added successfully",
        "category_assigned":   final_category,
        "category_was_auto":   body.category is None,
        "data":                result.data[0]
    }


@router.get("/")
async def list_transactions(user=Depends(get_current_user)):
    """List all transactions for current month with category summary."""
    today = date.today()
    first_of_month = today.replace(day=1)

    result = supabase.table("transactions") \
        .select("*") \
        .eq("user_id", str(user.id)) \
        .gte("txn_date", str(first_of_month)) \
        .order("txn_date", desc=True) \
        .execute()

    expenses = [t for t in result.data if t["amount"] < 0]
    income   = [t for t in result.data if t["amount"] > 0]

    # Build category breakdown — how much spent per category
    category_totals = {}
    for t in expenses:
        cat = t.get("category") or "other"
        category_totals[cat] = round(
            category_totals.get(cat, 0) + abs(t["amount"]), 2
        )

    return {
        "transactions": result.data,
        "count":        len(result.data),
        "summary": {
            "total_expenses":   round(sum(abs(t["amount"]) for t in expenses), 2),
            "total_income":     round(sum(t["amount"]      for t in income),   2),
            "expense_count":    len(expenses),
            "income_count":     len(income),
            "by_category":      category_totals   # NEW — category breakdown
        }
    }


@router.get("/categories")
async def list_categories():
    """Returns all valid categories — used by frontend dropdown."""
    from calculator import VALID_CATEGORIES
    return {"categories": VALID_CATEGORIES}