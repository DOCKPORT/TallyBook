//! Safe expression evaluator for DockPort CLI calculator.
//!
//! Tokenizes, parses, and evaluates arithmetic expressions with variables.
//! No system calls, no file I/O, no code execution — pure math only.
//!
//! # Grammar
//! ```text
//! expr     → assign
//! assign   → ident "=" expr | binary
//! binary   → term (("+" | "-") term)*
//! term     → unary (("*" | "/") unary)*
//! unary    → "-" unary | primary
//! primary  → NUMBER | ident | "(" expr ")"
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Tokenizer
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum Token {
    Number(f64),
    Ident(String),
    Plus,
    Minus,
    Star,
    Slash,
    Equals,
    LParen,
    RParen,
    End,
}

fn tokenize(input: &str) -> Result<Vec<Token>, String> {
    let mut tokens = Vec::new();
    let mut chars = input.chars().peekable();

    while let Some(&ch) = chars.peek() {
        match ch {
            ' ' | '\t' => {
                chars.next();
            }
            '+' => {
                tokens.push(Token::Plus);
                chars.next();
            }
            '-' => {
                tokens.push(Token::Minus);
                chars.next();
            }
            '*' => {
                tokens.push(Token::Star);
                chars.next();
            }
            '/' => {
                tokens.push(Token::Slash);
                chars.next();
            }
            '=' => {
                tokens.push(Token::Equals);
                chars.next();
            }
            '(' => {
                tokens.push(Token::LParen);
                chars.next();
            }
            ')' => {
                tokens.push(Token::RParen);
                chars.next();
            }
            ch if ch.is_ascii_digit() || ch == '.' => {
                let mut num_str = String::new();
                let mut dot_seen = false;
                while let Some(&c) = chars.peek() {
                    if c.is_ascii_digit() {
                        num_str.push(c);
                        chars.next();
                    } else if c == '.' && !dot_seen {
                        num_str.push(c);
                        dot_seen = true;
                        chars.next();
                    } else {
                        break;
                    }
                }
                let n: f64 = num_str
                    .parse()
                    .map_err(|_| format!("Invalid number: '{}'", num_str))?;
                tokens.push(Token::Number(n));
            }
            ch if ch.is_ascii_alphabetic() || ch == '_' => {
                let mut ident = String::new();
                while let Some(&c) = chars.peek() {
                    if c.is_ascii_alphanumeric() || c == '_' {
                        ident.push(c);
                        chars.next();
                    } else {
                        break;
                    }
                }
                tokens.push(Token::Ident(ident));
            }
            _ => {
                return Err(format!("Unexpected character: '{}'", ch));
            }
        }
    }

    tokens.push(Token::End);
    Ok(tokens)
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
enum UnaryOp {
    Negate,
}

#[derive(Debug, Clone)]
enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
}

#[derive(Debug, Clone)]
enum Node {
    Number(f64),
    Variable(String),
    Assign(String, Box<Node>),
    BinOp {
        op: BinOp,
        lhs: Box<Node>,
        rhs: Box<Node>,
    },
    UnaryOp {
        op: UnaryOp,
        node: Box<Node>,
    },
}

struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}

impl Parser {
    fn new(tokens: Vec<Token>) -> Self {
        Parser { tokens, pos: 0 }
    }

    fn peek(&self) -> &Token {
        &self.tokens[self.pos]
    }

    fn advance(&mut self) -> Token {
        let tok = self.tokens[self.pos].clone();
        self.pos += 1;
        tok
    }

    fn expect(&mut self, expected: &Token) -> Result<(), String> {
        let tok = self.advance();
        if tok != *expected {
            return Err(format!("Expected {:?}, got {:?}", expected, tok));
        }
        Ok(())
    }

    /// expr → assign
    fn parse_expr(&mut self) -> Result<Node, String> {
        self.parse_assign()
    }

    /// assign → ident "=" expr | binary
    fn parse_assign(&mut self) -> Result<Node, String> {
        // Look ahead: if we see ident followed by '=', it's an assignment.
        // Otherwise fall through to binary.
        let saved = self.pos;
        if let Token::Ident(_) = self.peek() {
            // Peek past the ident
            let _ident_pos = self.pos;
            self.pos += 1;
            let is_assign = matches!(self.peek(), Token::Equals);
            self.pos = saved; // restore

            if is_assign {
                let name = if let Token::Ident(n) = self.advance() {
                    n
                } else {
                    unreachable!()
                };
                self.expect(&Token::Equals)?;
                let value = self.parse_assign()?;
                return Ok(Node::Assign(name, Box::new(value)));
            }
        }

        self.parse_binary()
    }

    /// binary → term (("+" | "-") term)*
    fn parse_binary(&mut self) -> Result<Node, String> {
        let mut left = self.parse_term()?;

        loop {
            match self.peek() {
                Token::Plus => {
                    self.advance();
                    let right = self.parse_term()?;
                    left = Node::BinOp {
                        op: BinOp::Add,
                        lhs: Box::new(left),
                        rhs: Box::new(right),
                    };
                }
                Token::Minus => {
                    self.advance();
                    let right = self.parse_term()?;
                    left = Node::BinOp {
                        op: BinOp::Sub,
                        lhs: Box::new(left),
                        rhs: Box::new(right),
                    };
                }
                _ => break,
            }
        }

        Ok(left)
    }

    /// term → unary (("*" | "/") unary)*
    fn parse_term(&mut self) -> Result<Node, String> {
        let mut left = self.parse_unary()?;

        loop {
            match self.peek() {
                Token::Star => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = Node::BinOp {
                        op: BinOp::Mul,
                        lhs: Box::new(left),
                        rhs: Box::new(right),
                    };
                }
                Token::Slash => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = Node::BinOp {
                        op: BinOp::Div,
                        lhs: Box::new(left),
                        rhs: Box::new(right),
                    };
                }
                _ => break,
            }
        }

        Ok(left)
    }

    /// unary → "-" unary | primary
    fn parse_unary(&mut self) -> Result<Node, String> {
        if let Token::Minus = self.peek() {
            self.advance();
            let node = self.parse_unary()?;
            return Ok(Node::UnaryOp {
                op: UnaryOp::Negate,
                node: Box::new(node),
            });
        }
        self.parse_primary()
    }

    /// primary → NUMBER | ident | "(" expr ")"
    fn parse_primary(&mut self) -> Result<Node, String> {
        match self.peek() {
            Token::Number(n) => {
                let n = *n;
                self.advance();
                Ok(Node::Number(n))
            }
            Token::Ident(name) => {
                let name = name.clone();
                self.advance();
                Ok(Node::Variable(name))
            }
            Token::LParen => {
                self.advance();
                let node = self.parse_expr()?;
                self.expect(&Token::RParen)?;
                Ok(node)
            }
            _ => Err(format!("Unexpected token: {:?}", self.peek())),
        }
    }

    fn parse(mut self) -> Result<Node, String> {
        let node = self.parse_expr()?;
        if !matches!(self.peek(), Token::End) {
            return Err(format!(
                "Unexpected token after expression: {:?}",
                self.peek()
            ));
        }
        Ok(node)
    }
}

// ---------------------------------------------------------------------------
// Evaluator
// ---------------------------------------------------------------------------

fn eval_node(node: &Node, vars: &mut HashMap<String, f64>) -> Result<f64, String> {
    match node {
        Node::Number(n) => Ok(*n),
        Node::Variable(name) => vars
            .get(name)
            .copied()
            .ok_or_else(|| format!("Unknown variable: '{}'", name)),
        Node::Assign(name, value_node) => {
            let value = eval_node(value_node, vars)?;
            vars.insert(name.clone(), value);
            Ok(value)
        }
        Node::BinOp { op, lhs, rhs } => {
            let l = eval_node(lhs, vars)?;
            let r = eval_node(rhs, vars)?;
            match op {
                BinOp::Add => {
                    let result = l + r;
                    if result.is_infinite() {
                        return Err("Overflow: addition result is infinite".to_string());
                    }
                    if result.is_nan() {
                        return Err("Result is NaN".to_string());
                    }
                    Ok(result)
                }
                BinOp::Sub => {
                    let result = l - r;
                    if result.is_infinite() {
                        return Err("Overflow: subtraction result is infinite".to_string());
                    }
                    if result.is_nan() {
                        return Err("Result is NaN".to_string());
                    }
                    Ok(result)
                }
                BinOp::Mul => {
                    let result = l * r;
                    if result.is_infinite() {
                        return Err("Overflow: multiplication result is infinite".to_string());
                    }
                    if result.is_nan() {
                        return Err("Result is NaN".to_string());
                    }
                    Ok(result)
                }
                BinOp::Div => {
                    if r == 0.0 {
                        return Err("Division by zero".to_string());
                    }
                    let result = l / r;
                    if result.is_infinite() {
                        return Err("Overflow: division result is infinite".to_string());
                    }
                    if result.is_nan() {
                        return Err("Result is NaN".to_string());
                    }
                    Ok(result)
                }
            }
        }
        Node::UnaryOp { op, node } => {
            let val = eval_node(node, vars)?;
            match op {
                UnaryOp::Negate => Ok(-val),
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Public API: evaluate a single expression string
// ---------------------------------------------------------------------------

fn evaluate(expr: &str, vars: &mut HashMap<String, f64>) -> Result<f64, String> {
    let tokens = tokenize(expr)?;
    if tokens.len() <= 1 {
        return Err("Empty expression".to_string());
    }
    let parser = Parser::new(tokens);
    let ast = parser.parse()?;
    eval_node(&ast, vars)
}

// ---------------------------------------------------------------------------
// PyO3 wrapper
// ---------------------------------------------------------------------------

/// Safe expression evaluator. No system calls, no file I/O — pure math only.
///
/// Supports:
/// - Basic arithmetic: +, -, *, / with standard precedence
/// - Parentheses for grouping
/// - Variable assignment and retrieval: `x = 5`, `x + 9`
#[pyclass]
#[derive(Default)]
struct CalcEngine {
    vars: HashMap<String, f64>,
}

#[pymethods]
impl CalcEngine {
    /// Create a new CalcEngine with an empty variable store.
    #[new]
    fn new() -> Self {
        CalcEngine {
            vars: HashMap::new(),
        }
    }

    /// Evaluate a single expression string and return the result.
    ///
    /// Examples:
    ///   `500 * 1.01`      → 505.0
    ///   `x = 5`           → 5.0
    ///   `x + 9`           → 14.0
    ///   `(10 + 2) / 3`    → 4.0
    ///
    /// Raises ValueError on parse errors, unknown variables, or math errors
    /// (division by zero, overflow).
    #[pyo3(signature = (expr))]
    fn eval(&mut self, expr: &str) -> PyResult<f64> {
        evaluate(expr, &mut self.vars).map_err(|e| PyValueError::new_err(e))
    }

    /// Clear all stored variables.
    fn clear_vars(&mut self) {
        self.vars.clear();
    }

    /// Get the value of a variable, or None if not set.
    fn get_var(&self, name: &str) -> Option<f64> {
        self.vars.get(name).copied()
    }

    /// Return all variable names currently stored.
    fn list_vars(&self) -> Vec<String> {
        self.vars.keys().cloned().collect()
    }
}

/// Python module: `_calc_rs`
#[pymodule]
fn _calc_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CalcEngine>()?;
    Ok(())
}