from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dependencies import get_current_user, supabase
from calculator import (
    calculate_safe_to_spend,
    forecast_month_end_balance,
    check_affordability,
    get_month_day_info
)
from datetime import date
from typing import Optional

router = APIRouter(prefix="/calculate", tags=["Calculator"])


class AffordabilityRequest(BaseModel):
    proposed_expense: float
    proposed_expense_description: str


@router.get("/safe-to-spend")
async def safe_to_spend(user=Depends(get_current_user)):
    today = date.today()
    first_of_month = today.replace(day=1)

    # Fetch budget
    budget_r = supabase.table("monthly_budgets").select("*").eq("user_id", str(user.id)).eq("month", str(first_of_month)).execute()
    if not budget_r.data:
        raise HTTPException(status_code=404, detail="No budget set for this month.")
    budget = budget_r.data[0]

    # Fetch transactions
    txn_r = supabase.table("transactions").select("amount").eq("user_id", str(user.id)).gte("txn_date", str(first_of_month)).execute()
    total_spent = sum(abs(t["amount"]) for t in txn_r.data if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txn_r.data if t["amount"] > 0)
    current_balance = budget["opening_balance"] - total_spent + total_income

    # Fetch unpaid commitments
    comm_r = supabase.table("recurring_commitments").select("amount").eq("user_id", str(user.id)).eq("month", str(first_of_month)).eq("is_paid", False).execute()
    unpaid_total = sum(c["amount"] for c in comm_r.data)

    # Get day info
    day_info = get_month_day_info(today)

    return calculate_safe_to_spend(
        current_balance=current_balance,
        unpaid_commitments_total=unpaid_total,
        savings_goal=budget["savings_goal"],
        days_remaining=day_info["days_remaining"]
    )


@router.get("/forecast")
async def forecast(user=Depends(get_current_user)):
    """Projects month-end balance at current burn rate."""
    today = date.today()
    first_of_month = today.replace(day=1)

    budget_r = supabase.table("monthly_budgets").select("*").eq("user_id", str(user.id)).eq("month", str(first_of_month)).execute()
    if not budget_r.data:
        raise HTTPException(status_code=404, detail="No budget set for this month.")
    budget = budget_r.data[0]

    txn_r = supabase.table("transactions").select("amount").eq("user_id", str(user.id)).gte("txn_date", str(first_of_month)).execute()
    total_spent = sum(abs(t["amount"]) for t in txn_r.data if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txn_r.data if t["amount"] > 0)

    comm_r = supabase.table("recurring_commitments").select("amount").eq("user_id", str(user.id)).eq("month", str(first_of_month)).eq("is_paid", False).execute()
    unpaid_total = sum(c["amount"] for c in comm_r.data)

    day_info = get_month_day_info(today)

    return forecast_month_end_balance(
        opening_balance=budget["opening_balance"],
        total_spent_so_far=total_spent,
        total_income_added=total_income,
        days_elapsed=day_info["days_elapsed"],
        days_in_month=day_info["days_in_month"],
        unpaid_commitments_total=unpaid_total,
        savings_goal=budget["savings_goal"]
    )


@router.post("/can-i-afford")
async def can_i_afford(body: AffordabilityRequest, user=Depends(get_current_user)):
    today = date.today()
    first_of_month = today.replace(day=1)

    budget_r = supabase.table("monthly_budgets").select("*").eq("user_id", str(user.id)).eq("month", str(first_of_month)).execute()
    if not budget_r.data:
        raise HTTPException(status_code=404, detail="No budget set for this month.")
    budget = budget_r.data[0]

    txn_r = supabase.table("transactions").select("amount").eq("user_id", str(user.id)).gte("txn_date", str(first_of_month)).execute()
    total_spent = sum(abs(t["amount"]) for t in txn_r.data if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txn_r.data if t["amount"] > 0)
    current_balance = budget["opening_balance"] - total_spent + total_income

    comm_r = supabase.table("recurring_commitments").select("amount").eq("user_id", str(user.id)).eq("month", str(first_of_month)).eq("is_paid", False).execute()
    unpaid_total = sum(c["amount"] for c in comm_r.data)

    day_info = get_month_day_info(today)

    return check_affordability(
        current_balance=current_balance,
        unpaid_commitments_total=unpaid_total,
        savings_goal=budget["savings_goal"],
        days_remaining=day_info["days_remaining"],
        proposed_expense=body.proposed_expense,
        proposed_expense_description=body.proposed_expense_description
    )