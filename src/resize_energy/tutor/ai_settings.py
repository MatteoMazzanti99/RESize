"""Where the AI tutor settings live. The API key is never written to a file.

The key is kept in the operating-system keyring when the user asks for it (optional
``keyring`` package), can come from an environment variable, or is held in memory only
for the current session.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from resize_energy.tutor.ai import PROVIDER_LABELS, AISettings

KEYRING_SERVICE = "RESize"
ENV_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def config_dir() -> Path:
    """Per-user configuration folder for RESize."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "RESize"


def settings_path() -> Path:
    return config_dir() / "ai_settings.json"


def load_settings(path: Path | None = None) -> AISettings:
    """Saved provider, model and address (no key). Defaults if missing or unreadable."""
    target = path or settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        provider = str(data.get("provider", "anthropic"))
        if provider not in PROVIDER_LABELS:
            provider = "anthropic"
        return AISettings(
            provider=provider,
            model=str(data.get("model", "")),
            base_url=str(data.get("base_url", "")),
        )
    except (OSError, ValueError, AttributeError):
        return AISettings()


def save_settings(settings: AISettings, path: Path | None = None) -> bool:
    """Write provider, model and address. Returns False if the file cannot be written."""
    target = path or settings_path()
    payload = {
        "provider": settings.provider,
        "model": settings.model,
        "base_url": settings.base_url,
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        return False
    return True


def _keyring(module: ModuleType | None) -> Any:
    if module is not None:
        return module
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def load_api_key(
    provider: str,
    keyring_module: ModuleType | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Key from the system keyring, else from the environment, else an empty string."""
    kr = _keyring(keyring_module)
    if kr is not None:
        try:
            stored = kr.get_password(KEYRING_SERVICE, provider)
        except Exception:
            stored = None
        if stored:
            return str(stored)
    env = environ if environ is not None else os.environ
    var = ENV_VARS.get(provider)
    return str(env.get(var, "")).strip() if var else ""


def save_api_key(provider: str, key: str, keyring_module: ModuleType | None = None) -> bool:
    """Store the key in the system keyring. False if no keyring is available."""
    kr = _keyring(keyring_module)
    if kr is None:
        return False
    try:
        kr.set_password(KEYRING_SERVICE, provider, key)
    except Exception:
        return False
    return True


def delete_api_key(provider: str, keyring_module: ModuleType | None = None) -> bool:
    kr = _keyring(keyring_module)
    if kr is None:
        return False
    try:
        kr.delete_password(KEYRING_SERVICE, provider)
    except Exception:
        return False
    return True
