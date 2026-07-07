"""Regressão: mensagem multimodal (imagem) usa formato OpenAI, não Anthropic-nativo.

``LLMService.call`` chama ``litellm.completion`` (via ``instructor.from_litellm``), cujo
validator (``litellm.utils.validate_chat_completion_user_messages``) só aceita content
blocks no formato OpenAI (``type: image_url``) e rejeita o formato nativo do Anthropic
(``type: image`` / ``source``) com "Invalid user message at index N" — mesmo quando o
provider configurado é anthropic. Bug real: todo documento de imagem (.jpg/.png) enviado
via extract_with_llm falhava com esse erro (produção, 2026-07-07).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from pydantic import BaseModel

from pipeline.llm.litellm_client import LLMConfig, LLMService


class _Out(BaseModel):
    value: str


def _build_svc_with_mock_client(create_mock: MagicMock) -> LLMService:
    svc = LLMService(LLMConfig(provider="anthropic", api_key="sk-test", model_name="claude-test"))
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create_mock
    return svc


def _fake_response() -> MagicMock:
    response = MagicMock()
    response._raw_response = None
    return response


def _call_multimodal_and_capture_user_content() -> list:
    create_mock = MagicMock(return_value=_fake_response())
    svc = _build_svc_with_mock_client(create_mock)
    svc.call(
        system_prompt="sys",
        user_prompt="usr",
        output_schema=_Out,
        image_bytes=b"fake-jpeg-bytes",
        image_media_type="image/jpeg",
    )
    return create_mock.call_args.kwargs["messages"][1]["content"]


def test_multimodal_call_uses_openai_image_url_format() -> None:
    user_content = _call_multimodal_and_capture_user_content()
    assert isinstance(user_content, list)

    image_blocks = [b for b in user_content if b.get("type") == "image_url"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    # Formato Anthropic-nativo (rejeitado pelo validator do litellm) não pode reaparecer.
    assert not any(b.get("type") == "image" for b in user_content)
    assert not any("source" in b for b in user_content)
