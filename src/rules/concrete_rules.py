"""
Reglas concretas de detección de fraude y validación crediticia.
"""
from datetime import datetime, timedelta
from typing import List
from src.rules.base import BaseRule
from src.models.transaction import Transaction, RuleViolation


class HighAmountRule(BaseRule):
    """Evalúa si el monto supera umbrales críticos absolutos o relativos."""

    def __init__(self, critical_threshold: float = 10000.0, suspicious_threshold: float = 3000.0):
        super().__init__()
        self.critical_threshold = critical_threshold
        self.suspicious_threshold = suspicious_threshold

    def apply(self, transaction: Transaction, violations: List[RuleViolation], context: dict) -> None:
        if transaction.amount >= self.critical_threshold:
            violations.append(RuleViolation(
                rule_name="HIGH_AMOUNT_CRITICAL",
                severity="HIGH",
                description=f"El monto (${transaction.amount}) supera el umbral crítico de ${self.critical_threshold}."
            ))
        elif transaction.amount >= self.suspicious_threshold:
            violations.append(RuleViolation(
                rule_name="HIGH_AMOUNT_SUSPICIOUS",
                severity="MEDIUM",
                description=f"El monto (${transaction.amount}) supera el umbral de advertencia de ${self.suspicious_threshold}."
            ))


class VelocityRule(BaseRule):
    """Detecta ráfagas anómalas de transacciones en períodos cortos."""

    def __init__(self, max_allowed_in_window: int = 3, window_minutes: int = 5):
        super().__init__()
        self.max_allowed = max_allowed_in_window
        self.window_minutes = window_minutes

    def apply(self, transaction: Transaction, violations: List[RuleViolation], context: dict) -> None:
        recent_txs = context.get("recent_transactions", [])
        window_start = transaction.timestamp - timedelta(minutes=self.window_minutes)

        # Contar operaciones de la misma cuenta dentro de la ventana de tiempo
        in_window_count = sum(
            1 for tx in recent_txs 
            if tx.get("timestamp") >= window_start
        )

        if in_window_count >= self.max_allowed:
            violations.append(RuleViolation(
                rule_name="VELOCITY_LIMIT_EXCEEDED",
                severity="HIGH",
                description=f"Se detectaron {in_window_count + 1} transacciones en menos de {self.window_minutes} minutos."
            ))


class ImpossibleTravelRule(BaseRule):
    """Detecta operaciones en distintas ubicaciones geográficas en lapsos temporalmente imposibles."""

    def __init__(self, min_hours_between_countries: float = 2.0):
        super().__init__()
        self.min_hours = min_hours_between_countries

    def apply(self, transaction: Transaction, violations: List[RuleViolation], context: dict) -> None:
        last_tx = context.get("last_transaction")
        if not last_tx:
            return

        last_country = last_tx.get("country")
        last_time = last_tx.get("timestamp")

        if last_country and last_country != transaction.country:
            time_delta_hours = abs((transaction.timestamp - last_time).total_seconds()) / 3600.0
            if time_delta_hours < self.min_hours:
                violations.append(RuleViolation(
                    rule_name="IMPOSSIBLE_TRAVEL_DETECTED",
                    severity="HIGH",
                    description=(
                        f"Transacción originada en '{transaction.country}' a solo "
                        f"{time_delta_hours:.2f}hs de la previa en '{last_country}'."
                    )
                ))


class CreditLimitRule(BaseRule):
    """Valida la suficiencia de fondos o crédito disponible para la cuenta."""

    def apply(self, transaction: Transaction, violations: List[RuleViolation], context: dict) -> None:
        available_balance = context.get("available_balance", float("inf"))
        if transaction.amount > available_balance:
            violations.append(RuleViolation(
                rule_name="INSUFFICIENT_FUNDS_OR_LIMIT",
                severity="HIGH",
                description=(
                    f"Monto requerido (${transaction.amount}) excede "
                    f"el balance/límite disponible (${available_balance})."
                )
            ))