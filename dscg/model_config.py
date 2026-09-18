"""Provider-agnostic configuration for OpenAI-compatible model APIs.

The project originally created one DashScope client in each pipeline.  This
module keeps that setup as a backwards-compatible default for Qwen models,
while making the endpoint and credential explicit for every other provider.
No API key is ever included in ``public_dict`` or log-friendly descriptions.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ModelConfigurationError(ValueError):
    """Raised when a model cannot be configured safely."""


@dataclass(frozen=True)
class ProviderPreset:
    """Defaults for a provider exposing an OpenAI-compatible endpoint."""

    name: str
    base_url: str | None
    api_key_env: str | None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "models.local.toml"
ROLE_CONFIG_SECTIONS = {
    "DSCG_MAIN": ("main",),
    "DSCG_SEC": ("security", "sec", "audit"),
}
DEFAULT_MAIN_MODEL_ID = "qwen-flash-2025-07-28"
DEEPSEEK_MODEL_IDS = ("deepseek-flash", "deepseek-v4-pro")


@dataclass(frozen=True)
class ModelConfig:
    """Resolved model configuration used to construct an API client."""

    model_id: str
    api_key: str
    base_url: str | None
    provider: str
    api_key_env: str | None = None

    def client_kwargs(self) -> dict[str, str]:
        """Return arguments accepted by ``openai.OpenAI``."""

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return kwargs

    def public_dict(self) -> dict[str, str | None]:
        """Return safe metadata suitable for experiment results and logs."""

        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
        }


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "dashscope": ProviderPreset(
        name="dashscope",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
    ),
    "qwen": ProviderPreset(
        name="dashscope",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
    ),
    "deepseek": ProviderPreset(
        name="deepseek",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
    ),
    "openai": ProviderPreset(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    ),
    "moonshot": ProviderPreset(
        name="moonshot",
        base_url="https://api.moonshot.cn/v1",
        api_key_env="MOONSHOT_API_KEY",
    ),
    "kimi": ProviderPreset(
        name="moonshot",
        base_url="https://api.moonshot.cn/v1",
        api_key_env="MOONSHOT_API_KEY",
    ),
    "zhipu": ProviderPreset(
        name="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="ZHIPUAI_API_KEY",
    ),
    "glm": ProviderPreset(
        name="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="ZHIPUAI_API_KEY",
    ),
    "siliconflow": ProviderPreset(
        name="siliconflow",
        base_url="https://api.siliconflow.cn/v1",
        api_key_env="SILICONFLOW_API_KEY",
    ),
    "groq": ProviderPreset(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
    ),
    "ollama": ProviderPreset(
        name="ollama",
        base_url="http://localhost:11434/v1",
        # Ollama ignores the key, but the OpenAI client requires a value.
        api_key_env=None,
    ),
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _normalise_provider(provider: str | None) -> str | None:
    provider = _clean(provider)
    return provider.lower() if provider else None


def _normalise_base_url(base_url: str | None) -> str | None:
    base_url = _clean(base_url)
    if base_url:
        return base_url.rstrip("/")
    return None


def infer_provider(model_id: str, base_url: str | None = None) -> str:
    """Infer a useful preset name without preventing custom endpoints."""

    text = f"{model_id} {base_url or ''}".lower()
    if "dashscope" in text or "qwen" in text:
        return "dashscope"
    if "deepseek" in text:
        return "deepseek"
    if "moonshot" in text or "kimi" in text:
        return "moonshot"
    if "bigmodel" in text or "zhipu" in text or "glm-" in text:
        return "zhipu"
    if "siliconflow" in text:
        return "siliconflow"
    if "groq" in text:
        return "groq"
    if "localhost:11434" in text or "ollama" in text:
        return "ollama"
    return "openai"


def _env(mapping: Mapping[str, str], name: str | None) -> str | None:
    return _clean(mapping.get(name)) if name else None


def _resolve_config_path(
    config_path: str | os.PathLike[str] | None,
    env: Mapping[str, str],
) -> Path:
    configured_path = _clean(os.fspath(config_path)) if config_path else _env(
        env, "DSCG_MODEL_CONFIG"
    )
    path = Path(configured_path).expanduser() if configured_path else DEFAULT_MODEL_CONFIG_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_model_settings(
    config_path: str | os.PathLike[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Load ignored local model settings from TOML if the file exists."""

    environ = os.environ if env is None else env
    path = _resolve_config_path(config_path, environ)
    if not path.exists():
        return {}

    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception as exc:
        raise ModelConfigurationError(f"Failed to load model config {path}: {exc}") from exc

    if not isinstance(data, Mapping):
        raise ModelConfigurationError(f"Model config {path} must contain TOML tables.")
    return dict(data)


def _section_names(prefix: str) -> tuple[str, ...]:
    normalized = prefix.upper().rstrip("_")
    if normalized in ROLE_CONFIG_SECTIONS:
        return ROLE_CONFIG_SECTIONS[normalized]
    return (normalized.lower().removeprefix("dscg_"),)


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ModelConfigurationError(f"Model config section '{label}' must be a TOML table.")
    return value


def _role_config(settings: Mapping[str, Any], prefix: str) -> Mapping[str, Any]:
    for name in _section_names(prefix):
        section = settings.get(name)
        if section is not None:
            return _as_mapping(section, name)
    return {}


def _provider_config(settings: Mapping[str, Any], provider: str | None) -> Mapping[str, Any]:
    if not provider:
        return {}
    providers = _as_mapping(settings.get("providers"), "providers")
    return _as_mapping(providers.get(provider), f"providers.{provider}")


def _config_value(section: Mapping[str, Any], key: str) -> str | None:
    value = section.get(key)
    if value is None:
        return None
    return _clean(str(value))


def resolve_model_config(
    model_id: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
    api_key_env: str | None = None,
    prefix: str = "DSCG_MAIN",
    env: Mapping[str, str] | None = None,
    config_path: str | os.PathLike[str] | None = None,
    local_settings: Mapping[str, Any] | None = None,
    fallback: ModelConfig | None = None,
) -> ModelConfig:
    """Resolve explicit values, environment variables and provider presets.

    Precedence for each field is explicit argument, ``<prefix>_*`` variable,
    ``config/models.local.toml`` (or ``DSCG_MODEL_CONFIG``), provider preset,
    and finally compatibility defaults. ``fallback`` is used for a secondary
    model when it intentionally shares the primary endpoint.
    """

    environ = os.environ if env is None else env
    prefix = prefix.upper().rstrip("_")
    settings = (
        dict(local_settings)
        if local_settings is not None
        else load_model_settings(config_path, env=environ)
    )
    role_settings = _role_config(settings, prefix)

    local_model_id = _config_value(role_settings, "model_id")
    local_base_url = _normalise_base_url(_config_value(role_settings, "base_url"))
    local_provider = _normalise_provider(_config_value(role_settings, "provider"))
    local_api_key_env = _config_value(role_settings, "api_key_env")
    local_api_key = _config_value(role_settings, "api_key")

    resolved_model_id = _clean(model_id) or _env(environ, f"{prefix}_MODEL_ID") or local_model_id
    if not resolved_model_id and fallback:
        resolved_model_id = fallback.model_id
    if not resolved_model_id and prefix == "DSCG_MAIN":
        resolved_model_id = DEFAULT_MAIN_MODEL_ID
    if not resolved_model_id:
        raise ModelConfigurationError(
            f"Missing model id. Pass model_id or set {prefix}_MODEL_ID."
        )

    resolved_base_url = _normalise_base_url(base_url) or _normalise_base_url(
        _env(environ, f"{prefix}_BASE_URL")
    ) or local_base_url
    resolved_provider = _normalise_provider(provider) or _normalise_provider(
        _env(environ, f"{prefix}_PROVIDER")
    ) or local_provider
    if not resolved_provider:
        resolved_provider = infer_provider(resolved_model_id, resolved_base_url)

    # A missing secondary configuration means "reuse the primary endpoint".
    # Apply this before provider presets so a custom primary URL is not
    # accidentally replaced by the default OpenAI endpoint.
    if (
        fallback
        and resolved_model_id == fallback.model_id
        and resolved_base_url is None
        and not _env(environ, f"{prefix}_BASE_URL")
        and local_base_url is None
        and not _env(environ, f"{prefix}_PROVIDER")
        and local_provider is None
        and provider is None
    ):
        resolved_base_url = fallback.base_url
        resolved_provider = fallback.provider

    preset = PROVIDER_PRESETS.get(resolved_provider)
    provider_settings = _provider_config(settings, resolved_provider)
    if not provider_settings and preset:
        provider_settings = _provider_config(settings, preset.name)

    if preset:
        resolved_provider = preset.name
    if resolved_base_url is None:
        resolved_base_url = _normalise_base_url(
            _config_value(provider_settings, "base_url")
        )
    if resolved_base_url is None and preset:
        resolved_base_url = preset.base_url

    # A model-specific endpoint is more authoritative than a name-based guess.
    resolved_key_env = _clean(api_key_env) or _env(
        environ, f"{prefix}_API_KEY_ENV"
    ) or local_api_key_env or _config_value(provider_settings, "api_key_env")
    if resolved_key_env is None and preset:
        resolved_key_env = preset.api_key_env
    if resolved_key_env is None and fallback and resolved_model_id == fallback.model_id:
        resolved_key_env = fallback.api_key_env

    resolved_api_key = _clean(api_key) or _env(environ, f"{prefix}_API_KEY")
    if resolved_api_key is None:
        resolved_api_key = _env(environ, resolved_key_env)
    if resolved_api_key is None:
        resolved_api_key = local_api_key or _config_value(provider_settings, "api_key")
    if resolved_api_key is None and fallback and resolved_model_id == fallback.model_id:
        resolved_api_key = fallback.api_key

    # The local Ollama OpenAI-compatible server does not authenticate.
    if resolved_api_key is None and resolved_provider == "ollama":
        resolved_api_key = "ollama"

    if resolved_api_key is None:
        key_hint = resolved_key_env or f"{prefix}_API_KEY"
        raise ModelConfigurationError(
            f"Missing API key for model '{resolved_model_id}'. Pass api_key or "
            f"set {key_hint}. Provider '{resolved_provider}' uses endpoint "
            f"'{resolved_base_url or 'OpenAI default'}'."
        )

    return ModelConfig(
        model_id=resolved_model_id,
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        provider=resolved_provider,
        api_key_env=resolved_key_env,
    )


def create_openai_client(config: ModelConfig):
    """Create an OpenAI-compatible client lazily after dependencies are loaded."""

    import openai

    return openai.OpenAI(**config.client_kwargs())
