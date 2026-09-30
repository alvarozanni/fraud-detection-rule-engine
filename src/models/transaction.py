"""
Modelos de dominio para transacciones financieras y resultados de auditoría de fraude.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


class Transaction(BaseModel):
    """Modelo de entrada para una transacción entrante."""
    transaction_id: str = Field(..., example="tx-9821-ab")
    account_id: str = Field(..., example="acc-1049")
    amount: float = Field(..., gt=0, example=1500.0)
    currency: str = Field(default="USD", example="USD")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    country: str = Field(..., min_length=2, max_length=2, example="AR")
    device_id: str = Field(..., example="dev-mac-01")

    @field_validator("timestamp", mode="after")
    @classmethod
    def make_naive_utc(cls, v: datetime) -> datetime:
        """Remueve tzinfo para garantizar comparaciones homogéneas con la base de datos."""
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class RuleViolation(BaseModel):
    """Detalle de una regla disparada durante la evaluación."""
    rule_name: str
    severity: str  # HIGH, MEDIUM, LOW
    description: str


class EvaluationResult(BaseModel):
    """Veredicto final emitido por el motor de reglas con auditoría."""
    transaction_id: str
    decision: DecisionStatus
    score: int = Field(ge=0, le=100, description="Nivel de riesgo estimado (0 = seguro, 100 = crítico)")
    violations: List[RuleViolation] = []
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)