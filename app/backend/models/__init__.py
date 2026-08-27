"""ORM 表结构。表名统一 tb_*，表与字段必须带 comment。"""

from models.contract import Contract
from models.review_report import ReviewReport
from models.user import (
    AUTH_MODELS,
    AuthAudit,
    OneTimeToken,
    PURPOSE_EMAIL_VERIFY,
    PURPOSE_PASSWORD_RESET,
    RefreshToken,
    User,
)
from models.user_llm import LLM_MODELS, UserLlmModel, UserLlmProvider

DATA_MODELS = (Contract, ReviewReport) + LLM_MODELS

__all__ = [
    "User",
    "RefreshToken",
    "OneTimeToken",
    "AuthAudit",
    "AUTH_MODELS",
    "PURPOSE_EMAIL_VERIFY",
    "PURPOSE_PASSWORD_RESET",
    "Contract",
    "ReviewReport",
    "DATA_MODELS",
    "UserLlmProvider",
    "UserLlmModel",
    "LLM_MODELS",
]
