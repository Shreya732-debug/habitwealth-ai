# backend/routers/agent.py
from rag_engine import retrieve_relevant_chunks
from google import genai
from google.genai import types
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dependencies import get_current_user, supabase
from calculator import (
    calculate_safe_to_spend,
    forecast_month_end_balance,
    check_affordability,
    get_month_day_info,
    evaluate_financial_health,
)
from datetime import date
from dotenv import load_dotenv
import os
import traceback

load_dotenv()


# ── Safe Serializer ───────────────────────────────────────────
def _safe_serialize(obj):
    """Make tool results JSON-safe for Gemini — handles float('inf') and nested dicts."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_safe_serialize(i) for i in obj]
    elif isinstance(obj, float):
        if obj == float("inf") or obj == float("-inf") or obj != obj:
            return None
        return round(obj, 2)
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)


router = APIRouter(prefix="/agent", tags=["Agent"])


class AskRequest(BaseModel):
    question: str


# ── Tool Definitions ─────────────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "check_affordability",
        "description": (
            "Checks if the user can afford a specific purchase while still "
            "meeting their monthly savings goal. Use this when the user asks "
            "'can I afford X', 'can I buy X', 'is it okay to spend X', or "
            "similar affordability questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "proposed_expense": {
                    "type": "number",
                    "description": "The amount in rupees the user wants to spend",
                },
                "proposed_expense_description": {
                    "type": "string",
                    "description": "Human-readable label for the expense e.g. 'movie + dinner'",
                },
            },
            "required": ["proposed_expense", "proposed_expense_description"],
        },
    },
    {
        "name": "get_safe_to_spend",
        "description": (
            "Returns how much money is safe to spend today without breaching "
            "savings goal or missing upcoming bill payments. Use when user asks "
            "'how much can I spend today', 'what is my daily budget', 'am I okay to spend'."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_forecast",
        "description": (
            "Projects the user's balance at month end based on current burn rate. "
            "Use when user asks 'will I run out of money', 'how am I doing this month', "
            "'am I on track', 'what is my burn rate'."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_full_financial_summary",
        "description": (
            "Returns a complete financial summary including balance, spending breakdown, "
            "savings progress, burn rate, and month-end projection. Use when user asks "
            "'give me a full summary', 'what is my financial status', 'tell me everything "
            "about my finances', 'how are my finances overall'."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_savings_advice",
        "description": (
            "Analyzes spending patterns and gives personalized savings advice based on "
            "the user's actual data. Use when user asks 'how can I save more', "
            "'where am I overspending', 'tips to save money', 'how to improve my finances', "
            "'investment suggestions', 'where should I put my money'."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]


# ── Financial Context Builder ─────────────────────────────────
async def _build_financial_context(user_id: str) -> dict:
    """Fetches all current financial data for a user from Supabase."""
    today = date.today()
    first_of_month = today.replace(day=1)

    budget_r = (
        supabase.table("monthly_budgets")
        .select("*")
        .eq("user_id", user_id)
        .eq("month", str(first_of_month))
        .execute()
    )

    if not budget_r.data:
        return None

    budget = budget_r.data[0]

    txn_r = (
        supabase.table("transactions")
        .select("amount")
        .eq("user_id", user_id)
        .gte("txn_date", str(first_of_month))
        .execute()
    )

    comm_r = (
        supabase.table("recurring_commitments")
        .select("amount, name")
        .eq("user_id", user_id)
        .eq("month", str(first_of_month))
        .eq("is_paid", False)
        .execute()
    )

    total_spent = sum(abs(t["amount"]) for t in txn_r.data if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txn_r.data if t["amount"] > 0)
    unpaid_total = sum(c["amount"] for c in comm_r.data)
    current_balance = budget["opening_balance"] - total_spent + total_income
    day_info = get_month_day_info(today)

    return {
        "opening_balance": budget["opening_balance"],
        "savings_goal": budget["savings_goal"],
        "current_balance": round(current_balance, 2),
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "unpaid_commitments": round(unpaid_total, 2),
        "unpaid_items": [c["name"] for c in comm_r.data],
        "day_info": day_info,
    }


# ── Health Alert Evaluator ────────────────────────────────────
async def _get_health_alerts(ctx: dict) -> dict:
    """Runs financial health evaluation and returns alerts."""
    day_info = ctx["day_info"]

    forecast = forecast_month_end_balance(
        opening_balance=ctx["opening_balance"],
        total_spent_so_far=ctx["total_spent"],
        total_income_added=ctx["total_income"],
        days_elapsed=day_info["days_elapsed"],
        days_in_month=day_info["days_in_month"],
        unpaid_commitments_total=ctx["unpaid_commitments"],
        savings_goal=ctx["savings_goal"],
    )

    return evaluate_financial_health(
        current_balance=ctx["current_balance"],
        savings_goal=ctx["savings_goal"],
        unpaid_commitments=ctx["unpaid_commitments"],
        burn_rate_per_day=forecast["burn_rate_per_day"],
        days_remaining=day_info["days_remaining"],
        projected_month_end=forecast["projected_month_end_balance"],
    )


# ── System Prompt Builder ─────────────────────────────────────
def _build_system_prompt(ctx: dict, health: dict, rag_chunks: list = None) -> str:
    """Builds dynamic system prompt with financial data, alerts, and RAG context."""
    unpaid_str = ", ".join(ctx["unpaid_items"]) if ctx["unpaid_items"] else "none"

    if health["alerts"]:
        alert_lines = "\n".join(
            [f"  [{a['severity']}] {a['message']}" for a in health["alerts"]]
        )
        alert_section = (
            f"\nACTIVE FINANCIAL ALERTS (mention proactively):\n{alert_lines}"
        )
    else:
        alert_section = "\nNO ACTIVE ALERTS — finances look healthy."

    # RAG section — only added when relevant document chunks found
    if rag_chunks:
        rag_lines = "\n\n".join(
            [
                f"[From '{c['source']}', page {c['page_num']}]:\n{c['text']}"
                for c in rag_chunks
            ]
        )
        rag_section = f"""

CONTENT FROM USER'S UPLOADED DOCUMENTS:
(Prioritize this over general knowledge. Always cite the document name and page.)
{rag_lines}"""
    else:
        rag_section = ""

    return f"""You are FinanceGPT — a brilliant, warm, and highly knowledgeable personal \
finance assistant built specifically for Indian users.

CURRENT USER FINANCIAL SNAPSHOT (as of today {ctx['day_info']['today']}):
  Opening Balance:        ₹{ctx['opening_balance']}
  Current Balance:        ₹{ctx['current_balance']}
  Total Spent This Month: ₹{ctx['total_spent']}
  Monthly Savings Goal:   ₹{ctx['savings_goal']}
  Unpaid Commitments:     ₹{ctx['unpaid_commitments']} ({unpaid_str})
  Days Elapsed:           {ctx['day_info']['days_elapsed']} of {ctx['day_info']['days_in_month']}
  Days Remaining:         {ctx['day_info']['days_remaining']}
  Financial Health Score: {health['health_score']}/100 — {health['summary']}
{alert_section}{rag_section}

YOUR RULES:
1. ALWAYS use the provided tools for any calculation involving this user's money — never
   compute rupee amounts yourself. Tools give exact results from real database data.

2. For GENERAL financial knowledge questions (what is SIP, how does compound interest work,
   what is the 50/30/20 rule, how to save tax, what are mutual funds, PPF, EPF, NPS,
   FD, RD, ELSS, index funds, credit score, insurance, emergency fund, etc.) — answer
   directly from your knowledge. You are a financial expert. Be factual, clear, and
   give Indian-context examples using rupees where relevant. Examples: SBI, HDFC, Zerodha,
   Groww, Paytm Money, Navi. Mention risk levels when giving investment suggestions.

3. If there are ACTIVE ALERTS above, mention the most important one at the end of your
   response — even if the user did not ask about it.

4. Be concise and friendly. Lead with the direct answer, then key numbers, then any alert.
   Never start with "Great question!" or filler phrases.

5. Always mention the savings goal when relevant — help the user stay focused on it.

6. Mix personal context with general knowledge when helpful. For example, if asked about
   SIPs, answer what SIPs are AND mention whether the user can currently afford one based
   on their balance and savings goal.

7. If DOCUMENT CONTENT is provided above, prioritize it and cite the source document and
   page number. If the document contains numbers or tables, quote them accurately.

8. For investment and savings advice, always connect it to the user's actual numbers:
   their current balance, burn rate, savings goal, and days remaining. Make advice
   actionable and specific — not generic.

9. For questions about bank accounts, UPI, credit cards, loans, or banking products —
   answer with Indian banking context (RBI regulations, Indian bank names, rupee amounts).

10. When the user seems stressed about money, acknowledge it briefly then pivot to
    solutions — give them a clear, calm next step they can take today."""


# ── Tool Executor ─────────────────────────────────────────────
def _execute_tool(tool_name: str, tool_args: dict, ctx: dict) -> dict:
    """Executes the correct Python calculator function."""
    day_info = ctx["day_info"]

    if tool_name == "check_affordability":
        return check_affordability(
            current_balance=ctx["current_balance"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
            days_remaining=day_info["days_remaining"],
            proposed_expense=float(tool_args["proposed_expense"]),
            proposed_expense_description=tool_args["proposed_expense_description"],
        )
    elif tool_name == "get_safe_to_spend":
        return calculate_safe_to_spend(
            current_balance=ctx["current_balance"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
            days_remaining=day_info["days_remaining"],
        )
    elif tool_name == "get_forecast":
        return forecast_month_end_balance(
            opening_balance=ctx["opening_balance"],
            total_spent_so_far=ctx["total_spent"],
            total_income_added=ctx["total_income"],
            days_elapsed=day_info["days_elapsed"],
            days_in_month=day_info["days_in_month"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
        )
    elif tool_name == "get_full_financial_summary":
        forecast = forecast_month_end_balance(
            opening_balance=ctx["opening_balance"],
            total_spent_so_far=ctx["total_spent"],
            total_income_added=ctx["total_income"],
            days_elapsed=ctx["day_info"]["days_elapsed"],
            days_in_month=ctx["day_info"]["days_in_month"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
        )
        safe = calculate_safe_to_spend(
            current_balance=ctx["current_balance"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
            days_remaining=ctx["day_info"]["days_remaining"],
        )
        return {
            "opening_balance": ctx["opening_balance"],
            "current_balance": ctx["current_balance"],
            "total_spent": ctx["total_spent"],
            "total_income_added": ctx["total_income"],
            "savings_goal": ctx["savings_goal"],
            "unpaid_commitments": ctx["unpaid_commitments"],
            "days_elapsed": ctx["day_info"]["days_elapsed"],
            "days_remaining": ctx["day_info"]["days_remaining"],
            "daily_safe_to_spend": safe["daily_safe_amount"],
            "is_on_track": safe["is_safe"],
            "burn_rate_per_day": forecast["burn_rate_per_day"],
            "projected_month_end": forecast["projected_month_end_balance"],
            "will_meet_savings_goal": forecast["will_meet_savings_goal"],
            "forecast_status": forecast["status"],
            "forecast_message": forecast["status_message"],
        }

    elif tool_name == "get_savings_advice":
        safe = calculate_safe_to_spend(
            current_balance=ctx["current_balance"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
            days_remaining=ctx["day_info"]["days_remaining"],
        )
        forecast = forecast_month_end_balance(
            opening_balance=ctx["opening_balance"],
            total_spent_so_far=ctx["total_spent"],
            total_income_added=ctx["total_income"],
            days_elapsed=ctx["day_info"]["days_elapsed"],
            days_in_month=ctx["day_info"]["days_in_month"],
            unpaid_commitments_total=ctx["unpaid_commitments"],
            savings_goal=ctx["savings_goal"],
        )
        savings_rate = round(
            (
                (ctx["savings_goal"] / ctx["opening_balance"] * 100)
                if ctx["opening_balance"] > 0
                else 0
            ),
            1,
        )
        return {
            "current_balance": ctx["current_balance"],
            "total_spent": ctx["total_spent"],
            "savings_goal": ctx["savings_goal"],
            "daily_safe_amount": safe["daily_safe_amount"],
            "actual_burn_rate": forecast["burn_rate_per_day"],
            "safe_burn_rate": safe["daily_safe_amount"],
            "overspending_by_per_day": round(
                max(0, forecast["burn_rate_per_day"] - safe["daily_safe_amount"]), 2
            ),
            "projected_shortfall": round(
                max(0, ctx["savings_goal"] - forecast["projected_month_end_balance"]), 2
            ),
            "savings_rate_target_pct": savings_rate,
            "days_remaining": ctx["day_info"]["days_remaining"],
            "forecast_status": forecast["status"],
        }

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ── Main Agent Route ──────────────────────────────────────────
@router.post("/ask")
async def ask_agent(body: AskRequest, user=Depends(get_current_user)):
    """Natural language question → reasoned answer via tool-calling."""

    ctx = await _build_financial_context(str(user.id))
    if ctx is None:
        print("DEBUG: _build_financial_context() returned None")
        raise HTTPException(
            status_code=404,
            detail="No budget set for this month. Please set an opening balance first.",
        )

    health = await _get_health_alerts(ctx)

    try:
        rag_chunks = retrieve_relevant_chunks(
            query=body.question, user_id=str(user.id), top_k=3
        )
    except Exception:
        rag_chunks = []

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Build tool declarations in the format the new google-genai SDK requires
    tool_declarations = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=(
                    types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            k: types.Schema(
                                type=(
                                    types.Type.STRING
                                    if v.get("type") == "string"
                                    else (
                                        types.Type.NUMBER
                                        if v.get("type") == "number"
                                        else types.Type.OBJECT
                                    )
                                ),
                                description=v.get("description", ""),
                            )
                            for k, v in t["parameters"].get("properties", {}).items()
                        },
                        required=t["parameters"].get("required", []),
                    )
                    if t["parameters"].get("properties")
                    else types.Schema(type=types.Type.OBJECT, properties={})
                ),
            )
            for t in TOOL_DEFINITIONS
        ]
    )

    # Step 1 — Send question with tools
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=body.question,
            config=types.GenerateContentConfig(
                system_instruction=_build_system_prompt(ctx, health, rag_chunks),
                tools=[tool_declarations],
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    tool_name = None
    final_text = ""

    # Step 2 — Safely check if Gemini wants to call a tool
    try:
        candidate = response.candidates[0]
        part = candidate.content.parts[0]

        has_function_call = (
            hasattr(part, "function_call")
            and part.function_call is not None
            and hasattr(part.function_call, "name")
            and part.function_call.name
            and part.function_call.name != ""
        )

    except (IndexError, AttributeError):
        try:
            final_text = response.text
        except Exception:
            final_text = "I had trouble processing that. Please try again."
        return {
            "question": body.question,
            "answer": final_text,
            "tool_used": None,
            "health": {"score": health["health_score"], "alerts": health["alerts"]},
        }

    # Step 3 — Execute tool if needed
    if has_function_call:
        try:
            func_call = part.function_call
            tool_name = func_call.name
            tool_args = dict(func_call.args) if func_call.args else {}

            tool_result = _execute_tool(tool_name, tool_args, ctx)

            # Step 4 — Send tool result back to Gemini
            follow_up = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[
                    types.Content(role="user", parts=[types.Part(text=body.question)]),
                    types.Content(
                        role="model",
                        parts=[
                            part
                        ],  # reuse the actual part from the first response — carries thought_signature
                    ),
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=tool_name,
                                    response=_safe_serialize(tool_result),
                                )
                            )
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=_build_system_prompt(ctx, health, rag_chunks),
                    tools=[tool_declarations],
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )
            final_text = follow_up.text

        except Exception as e:
            traceback.print_exc()
            print(f"[agent] Tool execution error: {e}")
            final_text = (
                f"I understood your question but hit a technical issue. "
                f"Your current balance is ₹{ctx['current_balance']:,.0f} "
                f"and savings goal is ₹{ctx['savings_goal']:,.0f}. "
                f"Please try again."
            )
    else:
        try:
            final_text = (
                part.text if hasattr(part, "text") and part.text else response.text
            )
        except Exception:
            final_text = "I couldn't generate a response. Please try again."

    return {
        "question": body.question,
        "answer": final_text,
        "tool_used": tool_name,
        "health": {"score": health["health_score"], "alerts": health["alerts"]},
    }


# ── Health Check Route ────────────────────────────────────────
@router.get("/health-check")
async def financial_health_check(user=Depends(get_current_user)):
    """Returns financial health score and all active alerts."""
    ctx = await _build_financial_context(str(user.id))
    if ctx is None:
        print("DEBUG: _build_financial_context() returned None")
        raise HTTPException(
            status_code=404,
            detail="No budget set for this month. Please set an opening balance first.",
        )

    health = await _get_health_alerts(ctx)

    return {
        "health_score": health["health_score"],
        "summary": health["summary"],
        "alerts": health["alerts"],
        "alert_count": health["alert_count"],
        "context": {
            "current_balance": ctx["current_balance"],
            "savings_goal": ctx["savings_goal"],
            "days_remaining": ctx["day_info"]["days_remaining"],
            "unpaid_commitments": ctx["unpaid_commitments"],
        },
    }
