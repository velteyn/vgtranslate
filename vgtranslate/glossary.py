"""Glossary: per-profile term dictionaries injected into prompts and MT output.

A glossary maps source-language tokens (usually names or jargon) to fixed
translations. It is applied two ways:

1. **Prompt injection** — for frame-capable (VLM) translation the terms are
   listed in the system prompt so the model uses them.
2. **Post-processing** — for text MT engines the term pairs are patched into
   the translation afterward so names always come out consistent.
"""

from __future__ import annotations

from typing import Iterable


class Glossary:
    def __init__(self, entries: dict[str, str] | None = None) -> None:
        self.entries: dict[str, str] = dict(entries or {})

    def __len__(self) -> int:
        return len(self.entries)

    def __bool__(self) -> bool:
        return bool(self.entries)

    def __getitem__(self, key: str) -> str:
        return self.entries[key]

    def __setitem__(self, key: str, value: str) -> None:
        self.entries[key] = value

    def add(self, source: str, target: str) -> None:
        source = source.strip()
        target = target.strip()
        if source:
            self.entries[source] = target

    def prompt_guidance(self) -> str:
        """Render glossary terms as lines for an LLM system prompt."""
        if not self.entries:
            return ""
        lines = ["Use these fixed translations for the following terms:"]
        for source, target in self.entries.items():
            lines.append(f"- {source} => {target}")
        return "\n".join(lines)

    def apply_post(self, text: str) -> str:
        """Patch translations into ``text`` (longest match first)."""
        if not self.entries or not text:
            return text
        result = text
        for source in sorted(self.entries, key=len, reverse=True):
            target = self.entries[source]
            if not source:
                continue
            result = result.replace(source, target)
        return result


def from_dict(data: dict[str, str]) -> Glossary:
    return Glossary({str(k).strip(): str(v) for k, v in data.items() if str(k).strip()})


def merge(glossaries: Iterable[Glossary]) -> Glossary:
    merged: dict[str, str] = {}
    for glossary in glossaries:
        merged.update(glossary.entries)
    return Glossary(merged)
