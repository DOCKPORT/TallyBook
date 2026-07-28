import datetime
import os
import sqlite3

from PySide6.QtCore import QStandardPaths


class LedgerDB:
    """Backend module for handling all TallyBook database interactions."""

    def __init__(self):
        self.db_path = ""
        self.conn = None
        self.cursor = None
        self._init_database()

    def _init_database(self):
        """Initializes the SQLite database and creates tables if they don't exist."""
        # Use QStandardPaths to get the standard AppData location for the platform
        app_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        os.makedirs(app_dir, exist_ok=True)

        self.db_path = os.path.join(app_dir, "tallybook.db")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Enable WAL mode for crash-safe transaction durability
        self.cursor.execute("PRAGMA journal_mode=WAL")
        # Reduce the WAL autocheckpoint limit to 10 pages
        self.cursor.execute("PRAGMA wal_autocheckpoint=10")
        # synchronous=NORMAL is sufficient for durability in WAL mode
        self.cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Perform integrity check to detect corruption from previous crashes
        self.cursor.execute("PRAGMA integrity_check")
        integrity_result = self.cursor.fetchone()
        if integrity_result and integrity_result[0] != "ok":
            print(f"WARNING: Database integrity check failed: {integrity_result[0]}")
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                balance INTEGER DEFAULT 0
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                date TEXT,
                txid TEXT,
                payment_description TEXT,
                description TEXT,
                quantity REAL,
                amount INTEGER,
                type TEXT
            )
        """)
        
        # Settings Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Check for payment_description column and add if missing (Migration)
        self.cursor.execute("PRAGMA table_info(transactions)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if "payment_description" not in columns:
            self.cursor.execute("ALTER TABLE transactions ADD COLUMN payment_description TEXT")
            
        # Initialize default settings if not present
        self.ensure_setting("currency_symbol", "$")
        self.ensure_setting("currency_decimals", "2")
        self.ensure_setting("db_integer_migrated", "0")
            
        self.conn.commit()

        # Perform Migration to Integer-based system if needed
        self.cursor.execute("SELECT value FROM settings WHERE key = 'db_integer_migrated'")
        migrated = self.cursor.fetchone()
        if not migrated or migrated[0] == "0":
            try:
                # 1. Migrate Accounts Table
                self.cursor.execute("SELECT id, balance FROM accounts")
                for acc_id, bal in self.cursor.fetchall():
                    internal_bal = round(bal * 100)
                    self.cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (internal_bal, acc_id))
                
                # 2. Migrate Transactions Table
                self.cursor.execute("SELECT id, amount FROM transactions")
                for tx_id, amt in self.cursor.fetchall():
                    internal_amt = round(amt * 100)
                    self.cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (internal_amt, tx_id))
                
                # 3. Mark as Migrated
                self.cursor.execute("UPDATE settings SET value = '1' WHERE key = 'db_integer_migrated'")
                self.conn.commit()
                print("Database migrated to Integer-based precision (cents).")
            except Exception as e:
                print(f"Error during migration: {e}")
                self.conn.rollback()

    def ensure_setting(self, key, default_value):
        """Ensures a setting exists in the database, inserting the default if missing."""
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, default_value))

    def execute(self, query, params=()):
        """Wrapper for cursor.execute."""
        return self.cursor.execute(query, params)

    def fetchall(self):
        """Wrapper for cursor.fetchall."""
        return self.cursor.fetchall()

    def fetchone(self):
        """Wrapper for cursor.fetchone."""
        return self.cursor.fetchone()

    def commit(self):
        """Wrapper for conn.commit."""
        self.conn.commit()

    def rollback(self):
        """Wrapper for conn.rollback."""
        self.conn.rollback()

    def create_payment(self, account_id, date_str, payment_desc, items, txid=None):
        """Creates a payment and updates the account balance."""
        with self.conn:
            total_amount_internal = sum(item['total'] for item in items if item['total'] > 0)
            
            self.cursor.execute('SELECT balance FROM accounts WHERE id = ?', (account_id,))
            res = self.cursor.fetchone()
            if not res:
                raise ValueError('Selected account not found.')
                
            current_balance_internal = res[0]
            if current_balance_internal < total_amount_internal:
                raise ValueError('Insufficient Funds')
                
            self.cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (total_amount_internal, account_id))
            
            if not txid:
                txid = 'PAY-' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            
            for item in items:
                description = item['description']
                quantity = item['quantity']
                line_total_internal = item['total']
                if line_total_internal > 0:
                    self.cursor.execute('''
                        INSERT INTO transactions (account_id, date, txid, payment_description, description, quantity, amount, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (account_id, date_str, txid, payment_desc, description, quantity, line_total_internal, 'Payment'))
                    
        return txid

    def create_receipt(self, account_id, date_str, receipt_desc, items, txid=None):
        """Creates a receipt and updates the account balance."""
        with self.conn:
            self.cursor.execute('SELECT balance FROM accounts WHERE id = ?', (account_id,))
            res = self.cursor.fetchone()
            if not res:
                raise ValueError('Selected account not found.')
            
            total_amount_internal = sum(item['total'] for item in items if item['total'] > 0)
            
            self.cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (total_amount_internal, account_id))
            
            if not txid:
                txid = 'REC-' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            
            for item in items:
                description = item['description']
                quantity = item['quantity']
                line_total_internal = item['total']
                if line_total_internal > 0:
                    self.cursor.execute('''
                        INSERT INTO transactions (account_id, date, txid, payment_description, description, quantity, amount, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (account_id, date_str, txid, receipt_desc, description, quantity, line_total_internal, 'Receipt'))
                    
        return txid

    def create_transfer(self, from_id, to_id, amount_internal, description='', txid=None):
        """Executes a transfer between two accounts."""
        with self.conn:
            self.cursor.execute('SELECT balance FROM accounts WHERE id = ?', (from_id,))
            res = self.cursor.fetchone()
            if not res:
                raise ValueError('Source account not found.')
                
            current_balance_internal = res[0]
            if current_balance_internal < amount_internal:
                raise ValueError('Insufficient Funds for Transfer')
                
            self.cursor.execute('SELECT name FROM accounts WHERE id = ?', (from_id,))
            from_name = self.cursor.fetchone()[0]
            self.cursor.execute('SELECT name FROM accounts WHERE id = ?', (to_id,))
            to_name = self.cursor.fetchone()[0]
            
            self.cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount_internal, from_id))
            self.cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount_internal, to_id))
            
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            if not txid:
                txid = 'TRF-' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            
            self.cursor.execute('''
                INSERT INTO transactions (account_id, date, txid, payment_description, description, quantity, amount, type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (from_id, date_str, txid, f'Transfer to {to_name}', description, 1.0, amount_internal, 'Transfer Out'))
            
            self.cursor.execute('''
                INSERT INTO transactions (account_id, date, txid, payment_description, description, quantity, amount, type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (to_id, date_str, txid, f'Transfer from {from_name}', description, 1.0, amount_internal, 'Transfer In'))
            
        return txid

    def get_accounts(self):
        """Returns all accounts as a list of tuples (id, name, balance)."""
        self.cursor.execute("SELECT id, name, balance FROM accounts")
        return self.cursor.fetchall()

    def get_account(self, account_id):
        """Returns the specific account by ID as a tuple (id, name, balance)."""
        self.cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,))
        return self.cursor.fetchone()

    def create_account(self, name, balance=0):
        """Creates a new account in the database."""
        with self.conn:
            self.cursor.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
        return self.cursor.lastrowid

    def update_account_name(self, account_id, name):
        """Updates the name of an existing account."""
        with self.conn:
            self.cursor.execute("UPDATE accounts SET name = ? WHERE id = ?", (name, account_id))

    def delete_account(self, account_id):
        """Deletes an account by ID."""
        with self.conn:
            self.cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def get_setting(self, key, default=None):
        """Retrieves a setting by key."""
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row[0] if row else default

    def update_setting(self, key, value):
        """Updates a setting value."""
        with self.conn:
            self.cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))

    def close(self):
        """Closes the database connections."""
        if self.conn:
            self.conn.close()

