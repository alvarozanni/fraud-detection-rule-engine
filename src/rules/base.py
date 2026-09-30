"""
Contrato base para el encadenamiento de reglas de fraude (Chain of Responsibility).
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from src.models.transaction import Transaction, RuleViolation


class BaseRule(ABC):
    """Clase abstracta base para cualquier regla de detección o crédito."""

    def __init__(self):
        self._next_rule: Optional["BaseRule"] = None

    def set_next(self, rule: "BaseRule") -> "BaseRule":
        """Define la siguiente regla en la cadena."""
        self._next_rule = rule
        return rule

    def evaluate(self, transaction: Transaction, violations: List[RuleViolation], context: dict) -> None:
        """
        Ejecuta la regla actual y delega en la siguiente de la cadena si existe.
        """
        self.apply(transaction, violations, context)
        if self._next_rule:
            self._next_rule.evaluate(transaction, violations, context)

    @abstractmethod
    def apply(self, transaction: Transaction, violations: List[RuleViolation], context: dict) -> None:
        """Lógica de evaluación específica que debe implementar cada regla concreta."""
        pass