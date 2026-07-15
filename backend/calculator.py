from datetime import date, timedelta
from typing import Optional

# ─────────────────────────────────────────────────────────────
# FUNCTION 1: calculate_safe_to_spend
# ─────────────────────────────────────────────────────────────

def calculate_safe_to_spend(
    current_balance: float,
    unpaid_commitments_total: float,
    savings_goal: float,
    days_remaining: int
) -> dict:
     #Subtract money that is already spoken for
    available_to_spend = current_balance - unpaid_commitments_total - savings_goal

    # Step 2: Spread what is left across remaining days
    if days_remaining <= 0:
        daily_safe = 0.0
    else:
        daily_safe = available_to_spend / days_remaining

    # Step 3: Determine safety status
    is_safe = available_to_spend > 0

    # Step 4: Build a warning message if relevant
    if available_to_spend <= 0:
        warning = (
            f"⚠️ You are ₹{abs(round(available_to_spend, 2))} short of meeting your "
            f"savings goal after covering all commitments. Immediate review needed."
        )
    elif daily_safe < 200:
        warning = (
            f"⚠️ You have only ₹{round(daily_safe, 2)} per day to spend safely. "
            f"Consider reducing discretionary expenses."
        )
    else:
        warning = None

    return {
        "current_balance": round(current_balance, 2),
        "unpaid_commitments_total": round(unpaid_commitments_total, 2),
        "savings_goal": round(savings_goal, 2),
        "available_to_spend": round(available_to_spend, 2),
        "days_remaining": days_remaining,
        "daily_safe_amount": round(daily_safe, 2),
        "is_safe": is_safe,
        "warning": warning
    }

# ─────────────────────────────────────────────────────────────
# FUNCTION 2: forecast_month_end_balance
# ─────────────────────────────────────────────────────────────

def forecast_month_end_balance(
    opening_balance: float,
    total_spent_so_far: float,
    total_income_added: float,
    days_elapsed: int,
    days_in_month: int,
    unpaid_commitments_total: float,
    savings_goal: float
) -> dict:
    days_remaining = days_in_month - days_elapsed
    current_balance = opening_balance - total_spent_so_far + total_income_added

    # Step 1: Calculate daily burn rate (how much being spent per day on average)
    if days_elapsed <= 0:
        burn_rate_per_day = 0.0
    else:
        burn_rate_per_day = total_spent_so_far / days_elapsed

    
    # Step 2: Project additional spend for remaining days at current rate
    projected_additional_spend = burn_rate_per_day * days_remaining

    # Step 3: Subtract projected spend AND outstanding commitments
    projected_month_end_balance = (
        current_balance
        - projected_additional_spend
        - unpaid_commitments_total
    )

    # Step 4: Will savings goal be met?
    will_meet_savings_goal = projected_month_end_balance >= savings_goal

    # Step 5: Calculate days until money runs out (if burn rate continues)
    if burn_rate_per_day > 0:
        days_until_broke = current_balance / burn_rate_per_day
    else:
        days_until_broke = float('inf')  # Not spending = never broke

    
    # Step 6: Status assessment
    if projected_month_end_balance < 0:
        status = "CRITICAL"
        status_message = (
            f"At your current burn rate of ₹{round(burn_rate_per_day, 2)}/day, "
            f"you will run out of money in approximately {round(days_until_broke)} days."
        )
    elif not will_meet_savings_goal:
        shortfall = savings_goal - projected_month_end_balance
        status = "AT_RISK"
        status_message = (
            f"You are projected to be ₹{round(shortfall, 2)} short of your "
            f"₹{savings_goal} savings goal at month end."
        )
    else:
        surplus = projected_month_end_balance - savings_goal
        status = "ON_TRACK"
        status_message = (
            f"You are on track to meet your savings goal with a "
            f"₹{round(surplus, 2)} surplus projected."
        )

    return {
        "current_balance": round(current_balance, 2),
        "burn_rate_per_day": round(burn_rate_per_day, 2),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "projected_additional_spend": round(projected_additional_spend, 2),
        "projected_month_end_balance": round(projected_month_end_balance, 2),
        "will_meet_savings_goal": will_meet_savings_goal,
        "days_until_broke": round(days_until_broke, 1) if days_until_broke != float('inf') else None,
        "status": status,
        "status_message": status_message
    }

# ─────────────────────────────────────────────────────────────
# FUNCTION 3: check_affordability
# ─────────────────────────────────────────────────────────────

def check_affordability(
    current_balance: float,
    unpaid_commitments_total: float,
    savings_goal: float,
    days_remaining: int,
    proposed_expense: float,
    proposed_expense_description: str
) -> dict:
    # Step 1: What would balance be if we make this purchase?
    balance_after_expense = current_balance - proposed_expense


    # Step 2: After the purchase, is the savings goal still achievable?
    available_after = balance_after_expense - unpaid_commitments_total - savings_goal
    can_afford = available_after >= 0


    # Step 3: Compare daily safe-to-spend before and after
    available_before = current_balance - unpaid_commitments_total - savings_goal
    if days_remaining > 0:
        daily_safe_before = available_before / days_remaining
        daily_safe_after = available_after / days_remaining
    else:
        daily_safe_before = 0.0
        daily_safe_after = 0.0


     # Step 4: Build a clear verdict
    if can_afford:
        if daily_safe_after < 100:
            verdict = (
                f"✅ You CAN afford {proposed_expense_description} (₹{proposed_expense}), "
                f"but it leaves you with only ₹{round(daily_safe_after, 2)}/day — very tight. "
                f"Proceed with caution."
            )
        else:
            verdict = (
                f"✅ Yes! You can comfortably afford {proposed_expense_description} "
                f"(₹{proposed_expense}). After this purchase you will still have "
                f"₹{round(daily_safe_after, 2)}/day to spend safely and meet your "
                f"₹{savings_goal} savings goal."
            )
    else:
        shortfall = abs(round(available_after, 2))
        verdict = (
            f"❌ No. Spending ₹{proposed_expense} on {proposed_expense_description} "
            f"would leave you ₹{shortfall} short of your ₹{savings_goal} savings goal. "
            f"Consider reducing the expense by ₹{shortfall} or adjusting your savings target."
        )

    return {
        "proposed_expense": round(proposed_expense, 2),
        "proposed_expense_description": proposed_expense_description,
        "current_balance": round(current_balance, 2),
        "balance_after_expense": round(balance_after_expense, 2),
        "unpaid_commitments_total": round(unpaid_commitments_total, 2),
        "savings_goal": round(savings_goal, 2),
        "available_after_expense": round(available_after, 2),
        "can_afford": can_afford,
        "daily_safe_before": round(daily_safe_before, 2),
        "daily_safe_after": round(daily_safe_after, 2),
        "verdict": verdict
    } 

# ─────────────────────────────────────────────────────────────
# HELPER: get days info for current month
# ─────────────────────────────────────────────────────────────

def get_month_day_info(reference_date: Optional[date] = None) -> dict:
    if reference_date is None:
        reference_date = date.today()

    first_of_month = reference_date.replace(day=1)

    # Calculate total days in this month
    if reference_date.month == 12:
        next_month = reference_date.replace(year=reference_date.year + 1, month=1, day=1)
    else:
        next_month = reference_date.replace(month=reference_date.month + 1, day=1)

    days_in_month = (next_month - first_of_month).days
    days_elapsed = (reference_date - first_of_month).days + 1
    days_remaining = days_in_month - days_elapsed

    return {
        "today": str(reference_date),
        "first_of_month": str(first_of_month),
        "days_in_month": days_in_month,
        "days_elapsed": days_elapsed,
        "days_remaining": max(days_remaining, 0)
    }

# ─────────────────────────────────────────────────────────────
# CATEGORY CONSTANTS — single source of truth
# Used by both the categorizer and the frontend for display
# ─────────────────────────────────────────────────────────────

VALID_CATEGORIES = [
    "food",           # restaurants, groceries, Zomato, Swiggy
    "transport",      # Uber, Ola, fuel, metro, bus
    "shopping",       # clothes, electronics, Amazon, Flipkart
    "entertainment",  # movies, OTT, gaming, events
    "health",         # pharmacy, doctor, gym, hospital
    "subscriptions",  # Netflix, Spotify, annual plans
    "education",      # courses, books, fees, stationery
    "utilities",      # electricity, water, internet, phone bill
    "rent",           # house rent, hostel, PG
    "transfer",       # money sent to others, bank transfers
    "income",         # salary, freelance, gift money received
    "other"           # catch-all for anything else
]

# ─────────────────────────────────────────────────────────────
# FUNCTION 4: evaluate_financial_health
# ─────────────────────────────────────────────────────────────

def evaluate_financial_health(
    current_balance: float,
    savings_goal: float,
    unpaid_commitments: float,
    burn_rate_per_day: float,
    days_remaining: int,
    projected_month_end: float
) -> dict:
    """
    Evaluates overall financial health and returns alerts.
    Used by the agent to proactively surface warnings.
    """
    alerts = []
    health_score = 100

    # Alert 1: Will miss savings goal
    if projected_month_end < savings_goal:
        shortfall = round(savings_goal - projected_month_end, 2)
        alerts.append({
            "severity": "HIGH",
            "type":     "SAVINGS_AT_RISK",
            "message":  f"At current pace you will miss your savings goal "
                        f"by {shortfall}. Cut "
                        f"{round(shortfall / max(days_remaining, 1), 2)}/day "
                        f"to get back on track."
        })
        health_score -= 40

    # Alert 2: Will go broke before month ends
    if burn_rate_per_day > 0:
        days_until_broke = current_balance / burn_rate_per_day
        if days_until_broke < days_remaining:
            alerts.append({
                "severity": "CRITICAL",
                "type":     "GOING_BROKE",
                "message":  f"At {round(burn_rate_per_day, 2)}/day burn rate "
                            f"you will run out in ~{round(days_until_broke)} days "
                            f"but {days_remaining} days remain this month."
            })
            health_score -= 50

    # Alert 3: Burn rate too high
    available = current_balance - unpaid_commitments - savings_goal
    safe_daily = available / max(days_remaining, 1)
    if burn_rate_per_day > safe_daily * 1.5 and burn_rate_per_day > 0:
        alerts.append({
            "severity": "MEDIUM",
            "type":     "HIGH_BURN_RATE",
            "message":  f"Spending {round(burn_rate_per_day, 2)}/day but only "
                        f"{round(safe_daily, 2)}/day is safe."
        })
        health_score -= 20

    # Alert 4: Large unpaid commitments
    if current_balance > 0 and unpaid_commitments > current_balance * 0.5:
        alerts.append({
            "severity": "MEDIUM",
            "type":     "HIGH_COMMITMENTS",
            "message":  f"Unpaid bills are "
                        f"{round(unpaid_commitments / current_balance * 100)}% of balance."
        })
        health_score -= 10

    health_score = max(0, health_score)

    if health_score >= 80:
        summary = "Finances look healthy."
    elif health_score >= 50:
        summary = "Some concerns — review alerts."
    else:
        summary = "Immediate action needed."

    return {
        "health_score": health_score,
        "summary":      summary,
        "alerts":       alerts,
        "alert_count":  len(alerts)
    }