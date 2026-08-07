"""Typed configuration: server settings, per-game profiles, glossary, LLM.

Persisted as JSON in the user config directory; a default config is generated on
first run. Profiles let each game select its own OCR/MT engines, upscale factor,
languages and glossary.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 4404

# Order matters: first reachable wins.
LLM_PROBE_ORDER = (
    ("LM Studio", "http://localhost:1234/v1"),
    ("Ollama", "http://localhost:11434/v1"),
)

PROFILE_KEYS = (
    "mode",
    "ocr",
    "translator",
    "upscale",
    "color_isolation",
    "source_lang",
    "target_lang",
    "glossary",
)


class ConfigError(Exception):
    """Raised when a config file is unreadable or invalid."""


def config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "vgtranslate"
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "vgtranslate"


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class LLMSettings:
    base_url: str = ""
    model: str = ""
    timeout: float = 300.0
    temperature: float = 0.1
    json_mode: bool = True
    skip_reasoning: bool = False

    def to_dict(self) -> dict:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "temperature": self.temperature,
            "json_mode": self.json_mode,
            "skip_reasoning": self.skip_reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LLMSettings":
        return cls(
            base_url=str(data.get("base_url", "")),
            model=str(data.get("model", "")),
            timeout=float(data.get("timeout", 300.0)),
            temperature=float(data.get("temperature", 0.1)),
            json_mode=bool(data.get("json_mode", True)),
            skip_reasoning=bool(data.get("skip_reasoning", False)),
        )


@dataclass
class ServerSettings:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    default_target: str = "en"
    auto_unpause: bool = False

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "default_target": self.default_target,
            "auto_unpause": self.auto_unpause,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServerSettings":
        return cls(
            host=str(data.get("host", DEFAULT_HOST)),
            port=int(data.get("port", DEFAULT_PORT)),
            default_target=str(data.get("default_target", "en")),
            auto_unpause=bool(data.get("auto_unpause", False)),
        )


@dataclass
class Profile:
    name: str
    mode: str = "quality"  # "quality" (VLM read+translate) | "fast" (OCR + text MT)
    ocr: str = "rapid"
    translator: str = "openai"
    upscale: int = 2
    color_isolation: bool = False
    source_lang: str = "ja"
    target_lang: str = "en"
    glossary: str = "default"

    def validate(self) -> None:
        if self.mode not in ("quality", "fast"):
            raise ConfigError(f"profile '{self.name}': mode must be 'quality' or 'fast', got '{self.mode}'")
        if self.upscale < 1:
            raise ConfigError(f"profile '{self.name}': upscale must be >= 1")

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "ocr": self.ocr,
            "translator": self.translator,
            "upscale": self.upscale,
            "color_isolation": self.color_isolation,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "glossary": self.glossary,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Profile":
        profile = cls(
            name=name,
            mode=str(data.get("mode", "quality")),
            ocr=str(data.get("ocr", "rapid")),
            translator=str(data.get("translator", "openai")),
            upscale=int(data.get("upscale", 2)),
            color_isolation=bool(data.get("color_isolation", False)),
            source_lang=str(data.get("source_lang", "ja")),
            target_lang=str(data.get("target_lang", "en")),
            glossary=str(data.get("glossary", "default")),
        )
        profile.validate()
        return profile


@dataclass
class Config:
    server: ServerSettings = field(default_factory=ServerSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    active_profile: str = "default"
    profiles: dict[str, Profile] = field(
        default_factory=lambda: {"default": Profile(name="default")}
    )
    glossaries: dict[str, dict[str, str]] = field(default_factory=lambda: {"default": {}})

    def validate(self) -> None:
        if self.server.port < 1 or self.server.port > 65535:
            raise ConfigError(f"server port out of range: {self.server.port}")
        if self.llm.timeout <= 0:
            raise ConfigError("LLM timeout must be positive")
        for name, profile in self.profiles.items():
            if profile.name != name:
                raise ConfigError(f"profile key '{name}' does not match profile name '{profile.name}'")
            profile.validate()
            if profile.glossary not in self.glossaries:
                raise ConfigError(
                    f"profile '{name}' references missing glossary '{profile.glossary}'"
                )
        if self.active_profile not in self.profiles:
            raise ConfigError(
                f"active profile '{self.active_profile}' not found in profiles {list(self.profiles)}"
            )

    def active(self) -> Profile:
        return self.profiles[self.active_profile]

    def glossary(self) -> dict[str, str]:
        return self.glossaries.get(self.active().glossary, {})

    def to_dict(self) -> dict:
        return {
            "server": self.server.to_dict(),
            "llm": self.llm.to_dict(),
            "active_profile": self.active_profile,
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
            "glossaries": self.glossaries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        server = ServerSettings.from_dict(data.get("server", {}))
        llm = LLMSettings.from_dict(data.get("llm", {}))
        active_profile = str(data.get("active_profile", "default"))
        profiles: dict[str, Profile] = {}
        for name, raw in data.get("profiles", {}).items():
            profile = Profile.from_dict(str(name), raw)
            profiles[profile.name] = profile
        if not profiles:
            profiles["default"] = Profile(name="default")
        if active_profile not in profiles:
            active_profile = next(iter(profiles))
        glossaries = {
            str(name): {str(k): str(v) for k, v in raw.items()}
            for name, raw in data.get("glossaries", {}).items()
        }
        if "default" not in glossaries:
            glossaries["default"] = {}
        return cls(
            server=server,
            llm=llm,
            active_profile=active_profile,
            profiles=profiles,
            glossaries=glossaries,
        )


def default_config() -> Config:
    """Validate defaults so load/save never ships a broken config."""
    cfg = Config()
    cfg.validate()
    return cfg


def load_config(path: Optional[os.PathLike] = None) -> Config:
    """Load config from ``path`` (default user config dir), generating it if absent."""
    path = Path(path) if path else config_path()
    if not path.exists():
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"failed to read config {path}: {exc}") from exc
    cfg = Config.from_dict(raw)
    cfg.validate()
    return cfg


def save_config(cfg: Config, path: Optional[os.PathLike] = None) -> None:
    path = Path(path) if path else config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def detect_llm(timeout: float = 1.5) -> LLMSettings:
    """Probe known local OpenAI-compatible endpoints and return the first reachable.

    Sets only ``base_url`` (and a sensible default model name); the user picks a
    concrete model in the tray app or config. Falls back to LM Studio's address
    when nothing is reachable so manual setup is obvious.
    """
    try:
        import httpx
    except ImportError:
        return LLMSettings(base_url=LLM_PROBE_ORDER[0][1])

    for _name, base in LLM_PROBE_ORDER:
        try:
            resp = httpx.get(f"{base}/models", timeout=timeout)
            if resp.status_code == 200 and resp.json().get("data"):
                model = resp.json()["data"][0].get("id", "")
                return LLMSettings(base_url=base, model=model)
        except Exception:
            continue
    return LLMSettings(base_url=LLM_PROBE_ORDER[0][1])


def merge_llm_detected(llm: LLMSettings, detected: LLMSettings) -> LLMSettings:
    """Fill blank LLM fields with detected values, preserving manual overrides."""
    return LLMSettings(
        base_url=llm.base_url or detected.base_url,
        model=llm.model or detected.model,
        timeout=llm.timeout,
        temperature=llm.temperature,
        json_mode=llm.json_mode,
    )
