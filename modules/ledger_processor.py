"""
Ledger processor — wraps the native Rust balance_compute module with a
pure-Python fallback for the running balance and search-filtering logic.

This replaces the inline logic in TallyBookWindow._load_account_ledger.
"""

from typing import Any


def process_and_filter_ledger(
    current_balance: int,
    transactions: list[tuple],
    search_text: str = "",
) -> list[dict[str, Any]]:
    """Process DB rows into ledger dicts with running balances and search filtering.

    Args:
        current_balance: Current account balance in cents (from DB).
        transactions: Raw rows from the DB query, each as an 8-tuple
            (tx_id, date, type_, pay_desc, item_desc, amount, count, all_desc).
        search_text: Optional search string to filter results.

    Returns:
        List of dicts with keys: tx_id, date, type, desc, amount, balance,
        raw_pay_desc, raw_item_desc, all_desc.
    """
    try:
        from balance_compute import filter_transactions, process_transactions

        # Step 1: Compute running balances
        # Cast numeric fields to int — SQLite may return them as float
        typed_transactions = [
            (int(t[0]), t[1], t[2], t[3], t[4], int(t[5]), int(t[6]), t[7])
            for t in transactions
        ]
        all_tx = process_transactions(int(current_balance), typed_transactions)

        # Step 2: Filter
        if search_text:
            return filter_transactions(all_tx, search_text)
        return all_tx

    except ImportError:
        pass

    # ---- Pure Python fallback ----
    running_balance = current_balance
    all_tx_data: list[dict[str, Any]] = []

    for tx_id, date, type_, pay_desc, item_desc, amount, count, all_desc in transactions:
        # Format description
        desc = pay_desc if pay_desc else ""
        if count == 1:
            if desc and item_desc:
                desc = f"{desc} - {item_desc}"
            elif item_desc:
                desc = item_desc
        else:
            if not desc:
                desc = f"Transaction ({count} items)"

        tx_data = {
            "tx_id": tx_id,
            "date": date,
            "type": type_,
            "desc": desc,
            "amount": amount,
            "balance": running_balance,
            "raw_pay_desc": pay_desc if pay_desc else "",
            "raw_item_desc": item_desc if item_desc else "",
            "all_desc": all_desc if all_desc else "",
        }
        all_tx_data.append(tx_data)

        if type_ in ("Payment", "Transfer Out"):
            running_balance += amount
        elif type_ in ("Receipt", "Transfer In"):
            running_balance -= amount

    if not search_text:
        return all_tx_data

    search_lower = search_text.lower()
    filtered: list[dict[str, Any]] = []

    for tx in all_tx_data:
        if "Transfer" in tx["type"]:
            if search_lower in tx["raw_item_desc"].lower():
                filtered.append(tx)
        else:
            match_pay = search_lower in tx["raw_pay_desc"].lower()
            match_items = search_lower in tx["all_desc"].lower()

            if match_pay or match_items:
                if match_items and search_lower not in tx["desc"].lower():
                    items = [i.strip() for i in tx["all_desc"].split(",")]
                    matches = [i for i in items if search_lower in i.lower()]
                    if matches:
                        matched_str = ", ".join(matches)
                        if tx["raw_pay_desc"]:
                            tx["desc"] = f"{tx['raw_pay_desc']} - {matched_str}"
                        else:
                            tx["desc"] = matched_str
                filtered.append(tx)

    return filtered