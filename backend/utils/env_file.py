from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

_ENV_LINE_RE = re.compile(r"^(?P<prefix>\s*(?:export\s+)?)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)$")


def choose_env_file(project_root: Path) -> Path:
    """
    Choose the preferred environment file path for persistence.

    Priority:
    1) .env (unified, recommended)
    2) .env.backend (legacy)
    3) .env (new file if none exist)
    """
    env_path = project_root / ".env"
    if env_path.exists():
        return env_path

    legacy_path = project_root / ".env.backend"
    if legacy_path.exists():
        return legacy_path

    return env_path


def _format_env_value(value: str) -> str:
    """Format a value for a .env file line, quoting if needed."""
    if value is None:
        raise ValueError("env value must not be None")

    # Preserve empty string as KEY=
    if value == "":
        return ""

    # Quote if contains whitespace or comment-ish characters
    needs_quotes = any(ch.isspace() for ch in value) or "#" in value or value.startswith('"') or value.endswith('"')
    if not needs_quotes and "\n" not in value and "\r" not in value:
        return value

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n").replace("\r", "\\r")
    return f'"{escaped}"'


def update_env_file(path: Path, updates: Mapping[str, str]) -> None:
    """
    Update (or create) a dotenv-style file with the provided key/value pairs.

    - Preserves unrelated lines (comments, blanks, other keys)
    - Replaces existing key assignments in-place when possible
    - Appends missing keys at the end
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines(keepends=True)

    updated_keys: set[str] = set()
    out_lines: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            out_lines.append(line)
            continue

        match = _ENV_LINE_RE.match(line.rstrip("\n"))
        if not match:
            out_lines.append(line)
            continue

        key = match.group("key")
        if key not in updates:
            out_lines.append(line)
            continue

        prefix = match.group("prefix") or ""
        new_value = _format_env_value(str(updates[key]))
        out_lines.append(f"{prefix or ''}{key}={new_value}\n")
        updated_keys.add(key)

    missing = [k for k in updates.keys() if k not in updated_keys]
    if missing:
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines[-1] = out_lines[-1] + "\n"
        if out_lines and out_lines[-1].strip():
            out_lines.append("\n")
        out_lines.append("# Updated by Arona UI\n")
        for key in missing:
            out_lines.append(f"{key}={_format_env_value(str(updates[key]))}\n")

    path.write_text("".join(out_lines), encoding="utf-8")

