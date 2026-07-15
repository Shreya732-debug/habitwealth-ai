from calculator import (
    calculate_safe_to_spend,
    forecast_month_end_balance,
    check_affordability,
    get_month_day_info
)
from datetime import date

# ── Test tracking ─────────────────────────────────────────────
passed = 0
failed = 0

def check(test_name: str, condition: bool, actual=None, expected=None):
    global passed, failed
    if condition:
        print(f"  ✅ PASS — {test_name}")
        passed += 1
    else:
        print(f"  ❌ FAIL — {test_name}")
        if actual is not None:
            print(f"     Expected: {expected}")
            print(f"     Got:      {actual}")
        failed += 1

# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("FUNCTION 1: calculate_safe_to_spend")
print("="*60)

# Test 1A — Standard healthy budget
# Balance=25000, Commitments=5000, Goal=3000, Days=20
# Available = 25000 - 5000 - 3000 = 17000
# Daily safe = 17000 / 20 = 850
r = calculate_safe_to_spend(25000, 5000, 3000, 20)
check("Available to spend = 17000", r["available_to_spend"] == 17000.0,
      r["available_to_spend"], 17000.0)
check("Daily safe = 850", r["daily_safe_amount"] == 850.0,
      r["daily_safe_amount"], 850.0)
check("Is safe = True", r["is_safe"] == True)
check("No warning on healthy budget", r["warning"] is None)

# Test 1B — Budget already breached
# Balance=8000, Commitments=6000, Goal=5000, Days=15
# Available = 8000 - 6000 - 5000 = -3000 (negative!)
r = calculate_safe_to_spend(8000, 6000, 5000, 15)
check("Available = -3000 (breached)", r["available_to_spend"] == -3000.0,
      r["available_to_spend"], -3000.0)
check("Is safe = False when breached", r["is_safe"] == False)
check("Warning present when breached", r["warning"] is not None)

# Test 1C — Zero days remaining
r = calculate_safe_to_spend(5000, 1000, 1000, 0)
check("Daily safe = 0 when no days left", r["daily_safe_amount"] == 0.0,
      r["daily_safe_amount"], 0.0)

# Test 1D — Exact match (just enough)
# Balance=10000, Commitments=3000, Goal=2000, Days=10
# Available = 5000, Daily = 500
r = calculate_safe_to_spend(10000, 3000, 2000, 10)
check("Available = 5000 (exact)", r["available_to_spend"] == 5000.0,
      r["available_to_spend"], 5000.0)
check("Daily safe = 500", r["daily_safe_amount"] == 500.0,
      r["daily_safe_amount"], 500.0)

# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("FUNCTION 2: forecast_month_end_balance")
print("="*60)

# Test 2A — On track scenario
# Opening=30000, Spent=6000, Days elapsed=10 (of 31)
# Burn rate = 6000/10 = 600/day
# Days remaining = 21
# Projected additional spend = 600 * 21 = 12600
# Current balance = 30000 - 6000 = 24000
# Projected month end = 24000 - 12600 - 2000(commitments) = 9400
# Goal=5000, so on track (9400 > 5000)
r = forecast_month_end_balance(
    opening_balance=30000,
    total_spent_so_far=6000,
    total_income_added=0,
    days_elapsed=10,
    days_in_month=31,
    unpaid_commitments_total=2000,
    savings_goal=5000
)

check("Burn rate = 600/day", r["burn_rate_per_day"] == 600.0,
      r["burn_rate_per_day"], 600.0)
check("Projected month end = 9400", r["projected_month_end_balance"] == 9400.0,
      r["projected_month_end_balance"], 9400.0)
check("Will meet savings goal = True", r["will_meet_savings_goal"] == True)
check("Status = ON_TRACK", r["status"] == "ON_TRACK",
      r["status"], "ON_TRACK")

# Test 2B — At risk scenario
# Opening=15000, Spent=9000, Days elapsed=10 (of 30)
# Burn rate = 9000/10 = 900/day
# Days remaining = 20
# Projected additional spend = 900 * 20 = 18000
# Current balance = 15000 - 9000 = 6000
# Projected month end = 6000 - 18000 - 1000 = -13000 (CRITICAL)
r = forecast_month_end_balance(
    opening_balance=15000,
    total_spent_so_far=9000,
    total_income_added=0,
    days_elapsed=10,
    days_in_month=30,
    unpaid_commitments_total=1000,
    savings_goal=2000
)

check("Burn rate = 900/day (high)", r["burn_rate_per_day"] == 900.0,
      r["burn_rate_per_day"], 900.0)
check("Projected month end = -13000 (critical)", r["projected_month_end_balance"] == -13000.0,
      r["projected_month_end_balance"], -13000.0)
check("Status = CRITICAL", r["status"] == "CRITICAL",
      r["status"], "CRITICAL")
check("Will NOT meet savings goal", r["will_meet_savings_goal"] == False)

# Test 2C — Extra income added
# Same as 2A but with ₹5000 bonus income added
r = forecast_month_end_balance(
    opening_balance=30000,
    total_spent_so_far=6000,
    total_income_added=5000,
    days_elapsed=10,
    days_in_month=31,
    unpaid_commitments_total=2000,
    savings_goal=5000
)
check("Extra income increases projected balance", r["projected_month_end_balance"] == 14400.0,
      r["projected_month_end_balance"], 14400.0)

# Test 2D — Zero days elapsed edge case
r = forecast_month_end_balance(30000, 0, 0, 0, 31, 2000, 5000)
check("Burn rate = 0 when no days elapsed", r["burn_rate_per_day"] == 0.0,
      r["burn_rate_per_day"], 0.0)


# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("FUNCTION 3: check_affordability")
print("="*60)


# Test 3A — Can afford comfortably
# Balance=20000, Commitments=3000, Goal=2000
# Available = 20000 - 3000 - 2000 = 15000
# After spending 1500 (movie+dinner): available = 15000 - 1500 = 13500 > 0
r = check_affordability(20000, 3000, 2000, 20, 1500, "movie + dinner")
check("Can afford movie+dinner = True", r["can_afford"] == True)
check("Balance after = 18500", r["balance_after_expense"] == 18500.0,
      r["balance_after_expense"], 18500.0)
check("Available after = 13500", r["available_after_expense"] == 13500.0,
      r["available_after_expense"], 13500.0)
check("Verdict contains checkmark", "✅" in r["verdict"])

# Test 3B — Cannot afford (savings goal at risk)
# Balance=5000, Commitments=2000, Goal=2000
# Available = 5000 - 2000 - 2000 = 1000
# After spending 1500: available = 1000 - 1500 = -500 (can't afford!)
r = check_affordability(5000, 2000, 2000, 10, 1500, "new headphones")
check("Cannot afford when savings goal at risk", r["can_afford"] == False)
check("Available after = -500", r["available_after_expense"] == -500.0,
      r["available_after_expense"], -500.0)
check("Verdict contains X mark", "❌" in r["verdict"])

# Test 3C — The flagship question: "movie + dinner + still save ₹700"
# Balance=5000, No commitments, Goal=700, Days=10
# Available = 5000 - 0 - 700 = 4300
# Proposed expense = 1200 (movie ₹500 + dinner ₹700)
# Available after = 4300 - 1200 = 3100 > 0 → CAN afford
r = check_affordability(5000, 0, 700, 10, 1200, "movie ticket + dinner")
check("Flagship question — can afford and save ₹700", r["can_afford"] == True)
check("Daily safe after = (4300-1200)/10 = 310", r["daily_safe_after"] == 310.0,
      r["daily_safe_after"], 310.0)

# Test 3D — Exactly at the limit (zero available after)
# Balance=6000, Commitments=2000, Goal=2000, Expense=2000
# Available before = 2000, Available after = 0 (exactly zero — still affordable)
r = check_affordability(6000, 2000, 2000, 10, 2000, "exactly at limit")
check("Exactly at limit = still affordable", r["can_afford"] == True)
check("Available after = 0 (exactly)", r["available_after_expense"] == 0.0,
      r["available_after_expense"], 0.0)

# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("HELPER: get_month_day_info")
print("="*60)

# Test using a known date — July 15, 2026
r = get_month_day_info(date(2026, 7, 15))
check("July has 31 days", r["days_in_month"] == 31,
      r["days_in_month"], 31)
check("July 15 = day 15 elapsed", r["days_elapsed"] == 15,
      r["days_elapsed"], 15)
check("July 15 → 16 days remaining", r["days_remaining"] == 16,
      r["days_remaining"], 16)

# Test December (month boundary)
r = get_month_day_info(date(2026, 12, 1))
check("December has 31 days", r["days_in_month"] == 31,
      r["days_in_month"], 31)

# Test February non-leap year
r = get_month_day_info(date(2026, 2, 1))
check("Feb 2026 has 28 days (non-leap)", r["days_in_month"] == 28,
      r["days_in_month"], 28)


# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
print("="*60)

if failed == 0:
    print("🎉 All tests passed! Calculation engine is ready for Day 4.")
else:
    print(f"⚠️  {failed} test(s) failed. Fix calculator.py before proceeding to Day 4.")
print()

