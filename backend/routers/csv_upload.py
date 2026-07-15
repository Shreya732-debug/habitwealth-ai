# backend/routers/csv_upload.py
"""
CSV bank statement upload and parsing.
Accepts CSV files from any Indian bank (flexible column mapping).
Auto-categorizes every imported transaction using Gemini Flash.
Never blocks on categorization failure — falls back to 'other'.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from dependencies import get_current_user, supabase
from categorizer import categorize_transaction
from datetime import date, datetime
import pandas as pd
import io

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# Common column name variations across Indian bank CSV formats
# Maps whatever the bank calls it → our internal name
DATE_COLUMNS        = ["date", "txn date", "transaction date", "value date",
                        "posting date", "trans date", "dated"]
DESCRIPTION_COLUMNS = ["description", "narration", "particulars", "remarks",
                        "transaction details", "details", "memo"]
AMOUNT_COLUMNS      = ["amount", "transaction amount", "txn amount",
                        "withdrawal amt", "debit", "credit"]
DEBIT_COLUMNS       = ["debit", "withdrawal", "dr", "withdrawal amt", "debit amt"]
CREDIT_COLUMNS      = ["credit", "deposit", "cr", "deposit amt", "credit amt"]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes column names to lowercase and strips spaces.
    Maps bank-specific column names to standard internal names.
    """
    # Lowercase all column names and strip whitespace
    df.columns = [c.lower().strip() for c in df.columns]

    # Find date column
    date_col = next((c for c in df.columns if c in DATE_COLUMNS), None)
    if date_col:
        df = df.rename(columns={date_col: "txn_date"})

    # Find description column
    desc_col = next((c for c in df.columns if c in DESCRIPTION_COLUMNS), None)
    if desc_col:
        df = df.rename(columns={desc_col: "description"})

    # Find amount column — handle both combined and split debit/credit
    amount_col = next((c for c in df.columns if c in AMOUNT_COLUMNS
                       and c not in DEBIT_COLUMNS + CREDIT_COLUMNS), None)

    if amount_col:
        df = df.rename(columns={amount_col: "amount"})
    else:
        # Bank has separate debit and credit columns
        debit_col  = next((c for c in df.columns if c in DEBIT_COLUMNS), None)
        credit_col = next((c for c in df.columns if c in CREDIT_COLUMNS), None)

        if debit_col and credit_col:
            # Convert to numeric, fill NaN with 0
            df[debit_col]  = pd.to_numeric(df[debit_col],  errors="coerce").fillna(0)
            df[credit_col] = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
            # Combine: credits positive, debits negative
            df["amount"] = df[credit_col] - df[debit_col]
        elif debit_col:
            df["amount"] = -pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
        elif credit_col:
            df["amount"] = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)

    return df


def _parse_date(date_str: str) -> date:
    """
    Tries multiple date formats used by Indian banks.
    Returns a date object or raises ValueError.
    """
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y",
        "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d"
    ]
    date_str = str(date_str).strip()
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: '{date_str}'")


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload a bank statement CSV.
    Parses, validates, auto-categorizes, and imports all transactions.
    Returns a summary of what was imported.
    """

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted. Please export your bank "
                   "statement as CSV."
        )

    # Read file contents
    contents = await file.read()

    try:
        # Try UTF-8 first, fall back to latin-1 (common in Indian bank exports)
        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except UnicodeDecodeError:
            df = pd.read_csv(io.StringIO(contents.decode("latin-1")))

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read CSV file: {str(e)}"
        )

    # Normalize columns
    df = _normalize_columns(df)

    # Validate required columns exist after normalization
    missing = []
    if "txn_date"    not in df.columns: missing.append("date")
    if "description" not in df.columns: missing.append("description/narration")
    if "amount"      not in df.columns: missing.append("amount/debit/credit")

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Could not find these columns in your CSV: {missing}. "
                   f"Found columns: {list(df.columns)}"
        )

    # Drop rows where all key columns are NaN (blank rows at bottom of statement)
    df = df.dropna(subset=["txn_date", "amount"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["amount"])
    df = df[df["amount"] != 0]  # Skip zero-amount rows

    if len(df) == 0:
        raise HTTPException(
            status_code=422,
            detail="No valid transactions found in the CSV after parsing."
        )

    # Process each row
    imported      = []
    skipped       = []
    categories_used = {}

    for idx, row in df.iterrows():

        # Parse date
        try:
            txn_date = _parse_date(str(row["txn_date"]))
        except ValueError:
            skipped.append({
                "row": idx + 1,
                "reason": f"Invalid date format: {row['txn_date']}"
            })
            continue

        # Get description
        description = str(row.get("description", "")).strip()
        if not description or description.lower() in ["nan", "none", ""]:
            description = "Bank transaction"

        amount = float(row["amount"])

        # Auto-categorize
        category = categorize_transaction(description, amount)
        categories_used[category] = categories_used.get(category, 0) + 1

        # Insert into Supabase
        try:
            supabase.table("transactions").insert({
                "user_id":     str(user.id),
                "amount":      amount,
                "description": description,
                "category":    category,
                "txn_date":    str(txn_date),
                "source":      "csv"
            }).execute()

            imported.append({
                "date":        str(txn_date),
                "description": description[:50],
                "amount":      amount,
                "category":    category
            })

        except Exception as e:
            skipped.append({
                "row":    idx + 1,
                "reason": f"Database error: {str(e)}"
            })

    return {
        "message":         f"CSV imported successfully",
        "total_rows":      len(df),
        "imported_count":  len(imported),
        "skipped_count":   len(skipped),
        "categories_used": categories_used,
        "skipped_rows":    skipped,
        "preview":         imported[:10]  # First 10 rows as preview
    }