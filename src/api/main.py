"""
API REST: Endpoints para evaluación de transacciones en tiempo real y auditoría de fraude.
"""
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.models.transaction import Transaction, EvaluationResult
from src.rules.engine import FraudDetectionEngine
from src.db.repository import TransactionRepository

app = FastAPI(
    title="FraudGuard: Transaction & Credit Rule Engine",
    description="Motor de evaluación de fraude transaccional y reglas de crédito basado en Chain of Responsibility.",
    version="1.0.0"
)

# Instancias compartidas de infraestructura y dominio
repo = TransactionRepository("fraud_audit.db")
engine = FraudDetectionEngine()


class AccountSeedRequest(BaseModel):
    account_id: str = Field(..., example="acc-1049")
    initial_balance: float = Field(..., gt=0, example=5000.0)


class AuditRecord(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    decision: str
    risk_score: int
    timestamp: str


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "FraudGuard Engine",
        "docs_url": "/docs"
    }


@app.post("/api/v1/accounts/seed", tags=["Admin / Setup"], status_code=status.HTTP_201_CREATED)
def seed_account(payload: AccountSeedRequest):
    """Inicializa o fondea una cuenta para posibilitar pruebas transaccionales."""
    repo.seed_account(payload.account_id, payload.initial_balance)
    return {
        "status": "success",
        "account_id": payload.account_id,
        "available_balance": payload.initial_balance
    }


@app.post("/api/v1/transactions/evaluate", response_model=EvaluationResult, tags=["Fraud Evaluation"])
def evaluate_transaction(transaction: Transaction):
    """
    Evalúa una transacción financiera contra la cadena de reglas de fraude y audita el veredicto.
    """
    try:
        # 1. Recuperar contexto histórico de la cuenta
        context = repo.get_account_context(account_id=transaction.account_id)

        # 2. Ejecutar motor de reglas
        result = engine.evaluate(transaction=transaction, context=context)

        # 3. Persistir auditoría inmutable
        repo.save_audit(transaction=transaction, result=result)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la evaluación de la transacción: {str(e)}"
        )


@app.get("/api/v1/audits", response_model=List[AuditRecord], tags=["Audit Trail"])
def get_recent_audits(limit: int = 20):
    """Recupera los últimos registros de transacciones auditadas."""
    return repo.get_recent_audits(limit=limit)