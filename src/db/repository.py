"""
Capa de Persistencia y Auditoría: Gestión transaccional y consultas de contexto en SQLite.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.models.transaction import Transaction, EvaluationResult


class TransactionRepository:
    """Repositorio para auditar transacciones evaluadas y consultar historial de cuentas."""

    def __init__(self, db_path: str = "fraud_audit.db"):
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de auditoría transaccional
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transaction_audits (
                    transaction_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    country TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    violations_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL
                );
            """)

            # Cuentas y balances simulados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    available_balance REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE'
                );
            """)

            # Índices de auditoría temporal y por cuenta
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_account_time 
                ON transaction_audits (account_id, timestamp);
            """)
            conn.commit()

    def seed_account(self, account_id: str, balance: float) -> None:
        """Permite cargar o actualizar cuentas para pruebas y entornos locales."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO accounts (account_id, available_balance)
                VALUES (?, ?)
                ON CONFLICT(account_id) DO UPDATE SET available_balance = excluded.available_balance;
            """, (account_id, balance))
            conn.commit()

    def get_account_context(self, account_id: str, window_minutes: int = 60) -> Dict[str, Any]:
        """
        Recupera el balance disponible, última transacción y operaciones recientes
        para alimentar el contexto del motor de reglas.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Obtener balance
            cursor.execute("SELECT available_balance FROM accounts WHERE account_id = ?", (account_id,))
            acc_row = cursor.fetchone()
            balance = acc_row["available_balance"] if acc_row else 0.0

            # 2. Última transacción histórica
            cursor.execute("""
                SELECT country, timestamp FROM transaction_audits
                WHERE account_id = ?
                ORDER BY timestamp DESC LIMIT 1;
            """, (account_id,))
            last_row = cursor.fetchone()
            last_tx = None
            if last_row:
                last_tx = {
                    "country": last_row["country"],
                    "timestamp": datetime.fromisoformat(last_row["timestamp"])
                }

            # 3. Transacciones recientes en ventana temporal
            time_threshold = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
            cursor.execute("""
                SELECT timestamp, amount FROM transaction_audits
                WHERE account_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC;
            """, (account_id, time_threshold))
            recent_rows = cursor.fetchall()
            recent_txs = [
                {
                    "timestamp": datetime.fromisoformat(r["timestamp"]),
                    "amount": r["amount"]
                }
                for r in recent_rows
            ]

            return {
                "available_balance": balance,
                "last_transaction": last_tx,
                "recent_transactions": recent_txs
            }

    def save_audit(self, transaction: Transaction, result: EvaluationResult) -> None:
        """Persiste el registro inmutable de auditoría para la transacción."""
        violations_payload = json.dumps([v.model_dump() for v in result.violations])

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO transaction_audits (
                    transaction_id, account_id, amount, currency, country,
                    device_id, decision, risk_score, violations_json,
                    timestamp, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                transaction.transaction_id,
                transaction.account_id,
                transaction.amount,
                transaction.currency,
                transaction.country,
                transaction.device_id,
                result.decision.value,
                result.score,
                violations_payload,
                transaction.timestamp.isoformat(),
                result.evaluated_at.isoformat()
            ))
            conn.commit()

    def get_recent_audits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera los últimos registros de auditoría."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT transaction_id, account_id, amount, decision, risk_score, timestamp
                FROM transaction_audits
                ORDER BY evaluated_at DESC LIMIT ?;
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]