"""Catálogo curado de modelos LLM — fonte única de lista + default (ADR-288)."""

from __future__ import annotations

from dataclasses import dataclass

#: Registro de providers suportados → prefixo LiteLLM + env key.
#: ADR-288: prefixo LiteLLM do Google é "gemini/" e a env é GEMINI_API_KEY
#: (não "google/"/GOOGLE_API_KEY — erro silencioso que passa local).
SUPPORTED_PROVIDERS: dict[str, dict[str, str | None]] = {
    "anthropic": {"prefix": "anthropic/", "env_key": "ANTHROPIC_API_KEY"},
    "openai": {"prefix": "openai/", "env_key": "OPENAI_API_KEY"},
    "ollama": {"prefix": "ollama/", "env_key": None},
    "groq": {"prefix": "groq/", "env_key": "GROQ_API_KEY"},
    "deepseek": {"prefix": "deepseek/", "env_key": "DEEPSEEK_API_KEY"},
    "together_ai": {"prefix": "together_ai/", "env_key": "TOGETHERAI_API_KEY"},
    "google": {"prefix": "gemini/", "env_key": "GEMINI_API_KEY"},
    "openrouter": {"prefix": "openrouter/", "env_key": "OPENROUTER_API_KEY"},
}


@dataclass(frozen=True)
class CatalogModel:
    """Entrada curada do catálogo: id do modelo no provider + label de UI."""

    value: str
    label: str


MODELS_BY_PROVIDER: dict[str, tuple[CatalogModel, ...]] = {
    "anthropic": (
        CatalogModel("claude-opus-4-8", "Claude Opus 4.8"),
        CatalogModel("claude-opus-4-7", "Claude Opus 4.7"),
        CatalogModel("claude-opus-4-6", "Claude Opus 4.6"),
        CatalogModel("claude-sonnet-4-6", "Claude Sonnet 4.6"),
        CatalogModel("claude-haiku-4-5", "Claude Haiku 4.5"),
        CatalogModel("claude-opus-4-5", "Claude Opus 4.5"),
        CatalogModel("claude-sonnet-4-5", "Claude Sonnet 4.5"),
    ),
    "openai": (
        CatalogModel("gpt-5.5", "GPT-5.5"),
        CatalogModel("gpt-5.5-pro", "GPT-5.5 Pro"),
        CatalogModel("gpt-5.4", "GPT-5.4"),
        CatalogModel("gpt-5.4-mini", "GPT-5.4 Mini"),
        CatalogModel("gpt-5.4-nano", "GPT-5.4 Nano"),
        CatalogModel("gpt-5", "GPT-5"),
        CatalogModel("gpt-5-mini", "GPT-5 Mini"),
        CatalogModel("gpt-5-nano", "GPT-5 Nano"),
        CatalogModel("o3", "o3"),
        CatalogModel("o3-pro", "o3 Pro"),
        CatalogModel("gpt-4.1", "GPT-4.1"),
        CatalogModel("gpt-4.1-mini", "GPT-4.1 Mini"),
        CatalogModel("gpt-4o", "GPT-4o"),
        CatalogModel("gpt-4o-mini", "GPT-4o Mini"),
    ),
    "google": (
        CatalogModel("gemini-2.5-pro", "Gemini 2.5 Pro"),
        CatalogModel("gemini-2.5-flash", "Gemini 2.5 Flash"),
        CatalogModel("gemini-2.0-flash", "Gemini 2.0 Flash"),
    ),
    "groq": (
        CatalogModel("llama-3.3-70b-versatile", "Llama 3.3 70B"),
        CatalogModel("llama-3.1-8b-instant", "Llama 3.1 8B"),
        CatalogModel("mixtral-8x7b-32768", "Mixtral 8x7B"),
    ),
    "openrouter": (
        CatalogModel("anthropic/claude-opus-4-8", "Claude Opus 4.8"),
        CatalogModel("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"),
        CatalogModel("anthropic/claude-haiku-4-5", "Claude Haiku 4.5"),
        CatalogModel("openai/gpt-5.5", "GPT-5.5"),
        CatalogModel("openai/gpt-5", "GPT-5"),
        CatalogModel("openai/gpt-4o", "GPT-4o"),
        CatalogModel("google/gemini-2.5-pro", "Gemini 2.5 Pro"),
    ),
    "ollama": (
        CatalogModel("llama3.3", "Llama 3.3"),
        CatalogModel("mistral", "Mistral"),
        CatalogModel("codellama", "Code Llama"),
        CatalogModel("qwen2.5-coder", "Qwen 2.5 Coder"),
    ),
    "deepseek": (
        CatalogModel("deepseek-chat", "DeepSeek Chat"),
        CatalogModel("deepseek-reasoner", "DeepSeek Reasoner"),
    ),
    "together_ai": (
        CatalogModel("meta-llama/Llama-3.3-70B-Instruct-Turbo", "Llama 3.3 70B Turbo"),
        CatalogModel("Qwen/Qwen2.5-Coder-32B-Instruct", "Qwen 2.5 Coder 32B"),
    ),
}

#: Modelos com aposentadoria anunciada pelo provider — alimenta
#: ``model_status="deprecated"`` no LLMConfigResponse (ADR-288 §3).
DEPRECATED_MODELS: frozenset[str] = frozenset(
    {
        "claude-sonnet-4-20250514",  # Anthropic — retira 2026-06-15
        "claude-opus-4-20250514",  # Anthropic — retira 2026-06-15
        "claude-3-haiku-20240307",  # Anthropic — retira 2026-04-19
    }
)

_DEFAULT_BY_PROVIDER: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-5",
    "google": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "anthropic/claude-sonnet-4-6",
    "ollama": "llama3.3",
    "deepseek": "deepseek-chat",
    "together_ai": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
}


def default_model_for(provider: str = "anthropic") -> str:
    """Default canônico por provider — substitui literais datados (ADR-288 §5)."""
    return _DEFAULT_BY_PROVIDER.get(provider, _DEFAULT_BY_PROVIDER["anthropic"])


#: Pin PRÓPRIO do Parecer Planejador (formato LiteLLM ``provider/model``).
#: Não segue ``default_model_for``: o parecer tem golden mensal com baseline
#: versionado — mudança de modelo exige PR explícito, nunca efeito colateral
#: de bump do default global (ADR-288; paridade com lineage_debug.yaml).
PARECER_MODEL = "anthropic/claude-sonnet-4-6"
