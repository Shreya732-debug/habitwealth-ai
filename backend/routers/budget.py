# backend/routers/budget.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dependencies import get_current_user, supabase
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

router = APIRouter(prefix="/budget", tags=["Budget"])


# ── Request models ────────────────────────────────────────────

class StartMonthRequest(BaseModel):
    opening_balance: Decimal    # exact decimal, not float — money precision
    savings_goal: Decimal
    month: date                 # expects "2025-08-01" format


# ── Routes ───────────────────────────────────────────────────

@router.post("/start-month")
async def start_month(
    body: StartMonthRequest,
    user = Depends(get_current_user)   # JWT verified before this runs
):
    """
    Set the opening balance and savings goal for a month.
    Uses UPSERT — safe to call again to correct a mistake.
    """
    try:
        # Ensure month is always the first day of the month
        month_start = body.month.replace(day=1)

        result = supabase.table("monthly_budgets").upsert({
            "user_id": str(user.id),
            "month": str(month_start),
            "opening_balance": float(body.opening_balance),
            "savings_goal": float(body.savings_goal)
        }).execute()

        return {
            "message": "Budget set successfully",
            "data": result.data[0]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/current")
async def get_current_budget(user = Depends(get_current_user)):
    """
    Fetch this month's budget record.
    Also computes total_spent and remaining_balance on the fly.
    """
    today = date.today()
    first_of_month = today.replace(day=1)

    # Fetch budget row
    budget_result = supabase.table("monthly_budgets") \
        .select("*") \
        .eq("user_id", str(user.id)) \
        .eq("month", str(first_of_month)) \
        .execute()

    if not budget_result.data:
        raise HTTPException(
            status_code=404,
            detail="No budget set for this month. Please call POST /budget/start-month first."
        )

    budget = budget_result.data[0]

    # Fetch all transactions this month to compute total spent
    txn_result = supabase.table("transactions") \
        .select("amount") \
        .eq("user_id", str(user.id)) \
        .gte("txn_date", str(first_of_month)) \
        .execute()

    # Sum all negative amounts (expenses)
    # Expenses are stored as negative numbers: -450 for a ₹450 expense
    total_spent = sum(
        abs(t["amount"]) for t in txn_result.data if t["amount"] < 0
    )

    total_income_added = sum(
        t["amount"] for t in txn_result.data if t["amount"] > 0
    )

    current_balance = budget["opening_balance"] - total_spent + total_income_added
    days_in_month = (first_of_month.replace(month=first_of_month.month % 12 + 1, day=1) if first_of_month.month < 12
                     else first_of_month.replace(year=first_of_month.year + 1, month=1, day=1)) - first_of_month
    days_elapsed = (today - first_of_month).days + 1
    days_remaining = days_in_month.days - days_elapsed

    return {
        "month": budget["month"],
        "opening_balance": budget["opening_balance"],
        "savings_goal": budget["savings_goal"],
        "total_spent": round(total_spent, 2),
        "total_income_added": round(total_income_added, 2),
        "current_balance": round(current_balance, 2),
        "days_elapsed": days_elapsed,
        "days_remaining": max(days_remaining, 0),
        "on_track": current_balance >= budget["savings_goal"]
    }