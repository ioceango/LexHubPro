"""BUG-006 回归：推理模型正文可能在 reasoning_content 而非 content。"""

import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from llm_providers.openai_compat import extract_completion_text


def _response(content=None, reasoning_content=None, reasoning=None, extra=None, finish="stop"):
    message = SimpleNamespace(
        content=content,
        reasoning_content=reasoning_content,
        reasoning=reasoning,
        model_extra=extra or {},
    )
    choice = SimpleNamespace(message=message, finish_reason=finish)
    return SimpleNamespace(choices=[choice])


def test_extract_prefers_content_field():
    # BUG-006 回归
    text = extract_completion_text(_response(content="  visible  ", reasoning_content="hidden"))
    assert text == "visible"


def test_extract_glm_reasoning_content_when_content_empty():
    # BUG-006 回归：z-ai/glm-5.3-flash 一类模型 content=null
    payload = '{"summary": "ok", "overall_score": 70}'
    text = extract_completion_text(_response(content=None, reasoning_content=payload))
    assert "overall_score" in text
    assert text.startswith("{")


def test_extract_openrouter_reasoning_field():
    # BUG-006 回归
    text = extract_completion_text(_response(content="", reasoning="the answer is 42"))
    assert text == "the answer is 42"


def test_extract_content_parts_list():
    text = extract_completion_text(
        _response(content=[{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}])
    )
    assert "hello" in text
    assert "world" in text


def test_extract_empty_when_no_text_fields():
    assert extract_completion_text(_response(content=None, finish="length")) == ""
    assert extract_completion_text(SimpleNamespace(choices=[])) == ""
