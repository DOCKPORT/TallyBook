use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Represents one processed ledger row.
#[derive(Debug, Clone)]
struct LedgerRow {
    tx_id: i64,
    date: String,
    type_: String,
    desc: String,
    amount: i64,
    balance: i64,
    raw_pay_desc: String,
    raw_item_desc: String,
    all_desc: String,
}

impl LedgerRow {
    /// Format the display description following TallyBook rules.
    fn format_description(pay_desc: &str, item_desc: &str, count: i64) -> String {
        let desc = if pay_desc.is_empty() { String::new() } else { pay_desc.to_string() };
        
        if count == 1 {
            if !desc.is_empty() && !item_desc.is_empty() {
                format!("{} - {}", desc, item_desc)
            } else if !item_desc.is_empty() {
                item_desc.to_string()
            } else {
                desc
            }
        } else {
            if desc.is_empty() {
                format!("Transaction ({} items)", count)
            } else {
                desc
            }
        }
    }

    /// Convert to a Python dict (PyDict).
    fn to_py_dict<'py>(&self, py: Python<'py>) -> Bound<'py, PyDict> {
        let dict = PyDict::new(py);
        dict.set_item("tx_id", self.tx_id).unwrap();
        dict.set_item("date", &self.date).unwrap();
        dict.set_item("type", &self.type_).unwrap();
        dict.set_item("desc", &self.desc).unwrap();
        dict.set_item("amount", self.amount).unwrap();
        dict.set_item("balance", self.balance).unwrap();
        dict.set_item("raw_pay_desc", &self.raw_pay_desc).unwrap();
        dict.set_item("raw_item_desc", &self.raw_item_desc).unwrap();
        dict.set_item("all_desc", &self.all_desc).unwrap();
        dict
    }
}

/// Process raw database rows into ledger rows with running balances computed.
///
/// Python call signature:
///     process_transactions(current_balance: int, transactions: list) -> list
///
/// Each transaction tuple from DB has 8 fields:
///   (tx_id, date, type_, pay_desc, item_desc, amount, count, all_desc)
#[pyfunction]
fn process_transactions(
    py: Python<'_>,
    current_balance: i64,
    transactions: Vec<(i64, String, String, String, String, i64, i64, String)>,
) -> PyResult<Vec<Bound<'_, PyDict>>> {
    let mut running_balance = current_balance;
    let mut result: Vec<LedgerRow> = Vec::with_capacity(transactions.len());

    for (tx_id, date, type_, pay_desc, item_desc, amount, count, all_desc) in transactions {
        let desc = LedgerRow::format_description(&pay_desc, &item_desc, count);

        let row = LedgerRow {
            tx_id,
            date,
            type_,
            desc,
            amount,
            balance: running_balance,
            raw_pay_desc: if pay_desc.is_empty() { String::new() } else { pay_desc.to_string() },
            raw_item_desc: if item_desc.is_empty() { String::new() } else { item_desc },
            all_desc: if all_desc.is_empty() { String::new() } else { all_desc },
        };

        // Update running balance for next (older) transaction
        match row.type_.as_str() {
            "Payment" | "Transfer Out" => running_balance += amount,
            "Receipt" | "Transfer In" => running_balance -= amount,
            _ => {}
        }

        result.push(row);
    }

    Ok(result.into_iter().map(|r| r.to_py_dict(py)).collect())
}

/// Filter processed ledger rows by search text.
///
/// Python call signature:
///     filter_transactions(transactions: list, search_text: str) -> list
///
/// Modifies the `desc` field in place when searching inside item descriptions
/// to show only the matching items — matching the original Python behavior.
#[pyfunction]
fn filter_transactions<'py>(
    _py: Python<'py>,
    transactions: Vec<Bound<'py, PyDict>>,
    search_text: String,
) -> PyResult<Vec<Bound<'py, PyDict>>> {
    if search_text.is_empty() {
        return Ok(transactions);
    }

    let search_lower = search_text.to_lowercase();
    let mut result: Vec<Bound<'_, PyDict>> = Vec::new();

    for dict in transactions {
        let type_: String = dict.get_item("type").unwrap().unwrap().extract()?;
        let desc: String = dict.get_item("desc").unwrap().unwrap().extract()?;
        let raw_pay_desc: String = dict.get_item("raw_pay_desc").unwrap().unwrap().extract()?;
        let raw_item_desc: String = dict.get_item("raw_item_desc").unwrap().unwrap().extract()?;
        let all_desc: String = dict.get_item("all_desc").unwrap().unwrap().extract()?;

        let desc_lower = desc.to_lowercase();

        if type_.contains("Transfer") {
            // For transfers, search in raw_item_desc only
            if raw_item_desc.to_lowercase().contains(&search_lower) {
                result.push(dict);
            }
        } else {
            let match_pay = raw_pay_desc.to_lowercase().contains(&search_lower);
            let match_items = all_desc.to_lowercase().contains(&search_lower);

            if match_pay || match_items {
                // If matched on items but search text isn't already visible in desc
                if match_items && !desc_lower.contains(&search_lower) {
                    let items: Vec<&str> = all_desc.split(',').collect();
                    let matched: Vec<&str> = items
                        .iter()
                        .map(|s| s.trim())
                        .filter(|s| s.to_lowercase().contains(&search_lower))
                        .collect();

                    if !matched.is_empty() {
                        let matched_str = matched.join(", ");
                        let new_desc = if raw_pay_desc.is_empty() {
                            matched_str
                        } else {
                            format!("{} - {}", raw_pay_desc, matched_str)
                        };
                        dict.set_item("desc", new_desc).unwrap();
                    }
                }
                result.push(dict);
            }
        }
    }

    Ok(result)
}

/// Register the module with Python.
#[pymodule]
fn balance_compute(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_transactions, m)?)?;
    m.add_function(wrap_pyfunction!(filter_transactions, m)?)?;
    Ok(())
}