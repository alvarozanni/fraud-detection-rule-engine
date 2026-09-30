"""
Orquestador del motor de reglas: compone la cadena y calcula el veredicto de auditoría.
"""
from typing import List, Dict, Any
from src.models.transaction import Transaction, EvaluationResult, DecisionStatus, RuleViolation
from src.rules.concrete_rules import (
    HighAmountRule,
    VelocityRule,
    ImpossibleTravelRule,
    CreditLimitRule,
)


class FraudDetectionEngine:
    """Motor central que ejecuta la cadena de validaciones y puntúa el riesgo."""

    def __init__(self):
        # 1. Instanciación de reglas
        self.high_amount = HighAmountRule()
        self.velocity = VelocityRule()
        self.impossible_travel = ImpossibleTravelRule()
        self.credit_limit = CreditLimitRule()

        # 2. Configuración de la cadena (Chain of Responsibility)
        self.high_amount.set_next(self.velocity)
        self.velocity.set_next(self.impossible_travel)
        self.impossible_travel.set_next(self.credit_limit)

        self.root_rule = self.high_amount

    def evaluate(self, transaction: Transaction, context: Dict[str, Any]) -> EvaluationResult:
        """
        Pasa la transacción por la cadena y genera el resultado con score.
        """
        violations: List[RuleViolation] = []
        self.root_rule.evaluate(transaction, violations, context)

        # Cálculo determinístico del Risk Score (0 a 100)
        risk_score = 0
        has_high_severity = False

        for v in violations:
            if v.severity == "HIGH":
                risk_score += 40
                has_high_severity = True
            elif v.severity == "MEDIUM":
                risk_score += 20
            elif v.severity == "LOW":
                risk_score += 10

        risk_score = min(risk_score, 100)

        # Decisión final según puntaje y severidad
        if risk_score >= 60 or has_high_severity:
            decision = DecisionStatus.REJECTED
        elif risk_score >= 20:
            decision = DecisionStatus.FLAGGED
        else:
            decision = DecisionStatus.APPROVED

        return EvaluationResult(
            transaction_id=transaction.transaction_id,
            decision=decision,
            score=risk_score,
            violations=violations
        )