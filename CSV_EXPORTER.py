"""
CSV export utilities for TallyBook.

Provides a pure function to export account balances and transaction
history to a CSV file.  No Qt imports, no UI -- takes a file path and
a database connection, returns a (success, message) tuple.
"""

import csv
import sqlite3


def export_data_as_csv(file_path: str, db_conn: sqlite3.Connection) -> tuple[bool, str]:
    """Export account balances and transaction history to a CSV file.

    The CSV contains two sections:
        1. CURRENT ACCOUNT BALANCES — account name + balance columns
        2. TRANSACTION HISTORY — date, type, account, description, amount

    Args:
        file_path: Absolute path to the output .csv file.
        db_conn: An active sqlite3.Connection to the TallyBook database.

    Returns:
        (True, success_message) on success,
        (False, error_message) on failure.
    """
    try:
        cursor = db_conn.cursor()

        # --- Account balances ---
        cursor.execute("SELECT name, balance FROM accounts ORDER BY name ASC")
        account_data = cursor.fetchall()

        total_balance = sum(row[1] for row in account_data)
        account_balances = [(row[0], f"{row[1] / 100.0:.2f}") for row in account_data]

        # --- Transactions ---
        cursor.execute("""
            SELECT t.date, t.type, a.name, t.description, printf('%.2f', t.amount / 100.0)
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            ORDER BY t.date DESC
        """)
        transaction_rows = cursor.fetchall()

        # --- Write CSV ---
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            writer.writerow(["CURRENT ACCOUNT BALANCES"])
            writer.writerow(["Account Name", "Current Balance"])
            writer.writerows(account_balances)
            writer.writerow(["TOTAL BALANCE", f"{total_balance / 100.0:.2f}"])

            writer.writerow([])  # separator

            writer.writerow(["TRANSACTION HISTORY"])
            writer.writerow(["Date", "Type", "Account", "Description", "Amount"])
            writer.writerows(transaction_rows)

        return (True, f"Data exported successfully to:\n{file_path}")

    except Exception as e:
        return (False, f"Failed to export data: {e}")