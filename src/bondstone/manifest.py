"""Parse and schema-validate pack, bridge, preset and profile manifests."""

from __future__ import annotations

import datetime as dt
import json
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from .model import CONFIG_RULE, ERROR, Diagnostic

SCHEMA_DIR = Path(__file__).parent / "schemas"
KINDS = ("pack", "bridge", "preset", "profile")
MANIFEST_NAMES = {"pack": "pack.yaml", "bridge": "bridge.yaml", "preset": "preset.yaml"}


class ManifestError(Exception):
    """A manifest that cannot be read as YAML at all."""


def normalize(value: Any) -> Any:
    """Make YAML data JSON-like: dates become ISO strings and mapping keys become strings."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def load_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("file is not valid UTF-8") from exc
    try:
        return normalize(yaml.safe_load(text))
    except yaml.YAMLError as exc:
        detail = " ".join(str(exc).split())
        raise ManifestError(f"invalid YAML: {detail}") from exc


@cache
def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


@cache
def _validator(kind: str) -> Draft202012Validator:
    common = _schema("common")
    registry = Registry().with_resource(common["$id"], Resource.from_contents(common))
    return Draft202012Validator(_schema(kind), registry=registry)


def schema(kind: str) -> dict[str, Any]:
    """The JSON Schema shipped for one manifest kind."""
    return _schema(kind)


# bondstone: REQ-PRF-001
def validate(kind: str, data: Any) -> list[str]:
    """Schema problems of a manifest, one readable message each; empty when valid."""
    if not isinstance(data, dict):
        return ["expected a mapping at the top level"]
    errors = sorted(_validator(kind).iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])
    return [_describe(error) for error in errors]


def _location(error: ValidationError) -> str:
    parts: list[str] = []
    for part in error.absolute_path:
        if isinstance(part, int):
            parts[-1:] = [f"{parts[-1]}[{part}]"] if parts else [f"[{part}]"]
        else:
            parts.append(str(part))
    return ".".join(parts)


# bondstone: REQ-PRF-001, REQ-PRF-002
def _describe(error: ValidationError) -> str:
    location = _location(error)
    custom = error.schema.get("x-error") if isinstance(error.schema, dict) else None
    if error.validator == "additionalProperties":
        allowed = sorted((error.schema.get("properties") or {}).keys())
        extra = sorted(key for key in error.instance if key not in allowed)
        message = f"unknown key{'s' if len(extra) > 1 else ''} {', '.join(repr(k) for k in extra)}"
        if allowed:
            message += f" (allowed: {', '.join(allowed)})"
    elif error.validator == "required":
        missing = sorted(key for key in error.validator_value if key not in error.instance)
        message = f"missing required key{'s' if len(missing) > 1 else ''} {', '.join(repr(k) for k in missing)}"
    elif isinstance(error.instance, bool) and error.validator == "enum" and "ignore" in error.validator_value:
        # D3: YAML reads `off`, `no`, `on` and `yes` as booleans.
        word = "true" if error.instance else "false"
        message = (f"severity is the YAML boolean {word} (YAML reads off/no/on/yes as booleans); "
                   "write error, warn, info or ignore; `ignore` switches a rule off")
    elif custom:
        message = f"{custom}, got {json.dumps(error.instance, default=str)}"
    else:
        message = error.message
    return f"{location}: {message}" if location else message


# bondstone: REQ-PRF-001
def load_manifest(kind: str, path: Path, shown: str) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Read and validate one manifest.

    Returns the data (None when it cannot be used) and its problems. `shown` is the path
    reported in diagnostics."""
    try:
        data = load_yaml(path)
    except ManifestError as exc:
        return None, [Diagnostic(CONFIG_RULE, ERROR, str(exc), path=shown)]
    if data is None:
        data = {}
    problems = [Diagnostic(CONFIG_RULE, ERROR, message, path=shown) for message in validate(kind, data)]
    return (None if problems else data), problems
