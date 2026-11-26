"""Read-only input check for the adjacent reconstruction scenario."""

import argparse
import hashlib
import json
import re
from pathlib import Path


REQUIRED_SOURCES = ("README.md", "SourceTokens.m", "TokenTotals.m", "Reconstruction.bas", "Desk.vba")


def blocked(reason):
    print(f"BLOCKED: {reason}; desktop NOT_RUN")
    return 1


def safe_component(value):
    # Reject Win32 aliases rather than resolving a different file or device.
    return (
        isinstance(value, str) and not value.endswith(".")
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", value) is not None
        and re.fullmatch(r"CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]", value.split(".", 1)[0].upper()) is None
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companions", type=Path, help="Local directory holding pinned companions")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        manifest = json.loads((root / "inputs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return blocked("missing or unreadable inputs.json")
    if not isinstance(manifest, dict):
        return blocked("invalid inputs.json")
    companions = manifest.get("companions")
    if not isinstance(companions, list):
        return blocked("invalid companion list in inputs.json")

    for name in REQUIRED_SOURCES:
        try:
            present = bool((root / name).read_text(encoding="utf-8").strip())
        except (OSError, UnicodeError):
            present = False
        if not present:
            return blocked(f"missing, unreadable or empty source {name}")

    for companion in companions:
        if not isinstance(companion, dict):
            return blocked("invalid companion pin in inputs.json")
        name, version = companion.get("name"), companion.get("version")
        sha256, obtain = companion.get("sha256"), companion.get("obtain")
        if not (
            safe_component(name) and safe_component(version)
            and isinstance(sha256, str) and re.fullmatch(r"[a-f0-9]{64}", sha256)
            and isinstance(obtain, str) and obtain.strip()
        ):
            return blocked("invalid companion pin in inputs.json")
        pin = f"{name}@{version}"
        if args.companions is None:
            return blocked(f"no local companion directory supplied for {pin}")
        path = args.companions / version / name
        try:
            if not path.is_file():
                return blocked(f"missing or unreadable companion {pin}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return blocked(f"missing or unreadable companion {pin}")
        if digest != sha256:
            return blocked(f"SHA-256 mismatch for companion {pin}")

    print("READY: inputs only; desktop NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
