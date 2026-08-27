"""FEAT-009 回归：Atoms 脚手架模块已移除。"""

import inspect

import pytest

from services.ai_invoker import AIConfigurationError, AIInvoker
from schemas.chat import ChatMessage, GenTxtRequest


@pytest.mark.parametrize(
    "module_name",
    [
        "services.payment",
        "services.aihub",
        "services.mock_data",
        "api.aihub",
        "api.settings",
        "core.enums",
        "core.mask_crypto",
        "models.base",
        "lambda_handler",
    ],
)
def test_scaffold_modules_are_gone(module_name):
    # FEAT-009 回归
    with pytest.raises(ModuleNotFoundError):
        __import__(module_name)


def test_core_auth_has_no_oidc():
    # FEAT-009 回归
    import core.auth as auth

    source = inspect.getsource(auth)
    lowered = source.lower()
    assert "oidc" not in lowered
    assert "jwks" not in lowered
    assert "pkce" not in lowered
    assert hasattr(auth, "create_access_token")
    assert hasattr(auth, "decode_access_token")


@pytest.mark.asyncio
async def test_invoker_without_chat_does_not_use_ai_hub():
    # FEAT-009 回归：未注入用户模型客户端时不得回落到平台 Hub
    invoker = AIInvoker()
    request = GenTxtRequest(
        messages=[ChatMessage(role="user", content="hi")],
        model="test",
    )
    with pytest.raises(AIConfigurationError):
        await invoker.gentxt(request, stage="review")
