"""Validate redacted trial records and replay confirmed evidence for route.py."""

import hashlib
import json
import re
import sys
from typing import Any, Iterable


def unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError
    return fields


def require_labels(values: Iterable[object]) -> None:
    if any(not isinstance(value, str)
           or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,79}", value)
           or value.lower().endswith((".xlsx", ".xlsm", ".xlsb", ".xls", ".xlam", ".xltx", ".xltm", ".csv"))
           for value in values):
        raise ValueError


def record(text: str) -> dict[str, Any]:
    row = json.loads(text, object_pairs_hook=unique_fields)
    fields = {
        "scope", "interface", "version", "method", "outcome", "observations",
    }
    if not isinstance(row, dict) or row.keys() - {"accounted_for", "finding"} != fields:
        raise ValueError
    outcome = row["outcome"]
    if "accounted_for" in row and (outcome != "unresolved-effects" or row["accounted_for"] is not True):
        raise ValueError
    scope = row["scope"]
    if not isinstance(scope, dict) or scope.keys() != {
        "operation", "profile", "class", "effects", "controls", "environment", "boundary", "target_kind",
    }:
        raise ValueError
    if (scope["profile"] not in ("simple", "application") or scope["class"] not in ("runtime", "save")
            or scope["target_kind"] != "synthetic"):
        raise ValueError
    require_labels(row[key] for key in ("interface", "version", "method"))
    require_labels(scope[key] for key in ("operation", "environment", "boundary"))
    for key in ("effects", "controls"):
        labels = scope[key]
        if not isinstance(labels, list):
            raise ValueError
        require_labels(labels)
        if len(labels) != len(set(labels)):
            raise ValueError
        scope[key] = sorted(labels)

    observations = row["observations"]
    if not isinstance(observations, dict) or not observations or set(observations) != set(scope["controls"]):
        raise ValueError
    if any(state not in ("pass", "fail", "unknown", "not-run") for state in observations.values()):
        raise ValueError
    states = set(observations.values())
    if outcome == "gap" or "finding" in row:
        finding = row.get("finding")
        allowed_codes = {
            "gap": ("expected-effect-observed-missing", "expected-effect-observed-different",
                    "preservation-mismatch", "required-capability-missing"),
            "not-verified": ("readback-failed",),
        }
        if (not isinstance(finding, dict) or finding.keys() != {"control", "code"}
                or not isinstance(finding["control"], str) or observations.get(finding["control"]) != "fail"
                or not isinstance(outcome, str) or finding["code"] not in allowed_codes.get(outcome, ())):
            raise ValueError
    if not ((outcome == "verified" and states == {"pass"})
            or outcome == "gap"
            or (outcome == "not-verified" and states != {"pass"})
            or (outcome == "unavailable" and states == {"not-run"})
            or outcome == "unresolved-effects"):
        raise ValueError
    return row


def canonical(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def replay(lines: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
    evidence: dict[str, dict[str, Any]] = {}
    holds = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        row = record(line)
        scope_and_method = {key: row[key] for key in ("scope", "interface", "version", "method")}
        if row["outcome"] == "unresolved-effects" and not row.get("accounted_for"):
            holds.append({**scope_and_method, "line": number})
        if row["outcome"] in ("gap", "verified"):
            digest = hashlib.sha256(canonical(row).encode("ascii")).hexdigest()
            evidence[digest] = {
                **scope_and_method,
                "outcome": "excluded" if row["outcome"] == "gap" else "verified",
                "reference": f"trial-ledger:sha256:{digest}",
            }
    return {"evidence": [evidence[digest] for digest in sorted(evidence)], "holds": holds}


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["record"]:
            print(canonical(record(sys.stdin.read())))
        elif sys.argv[1:] == ["replay"]:
            print(json.dumps(replay(sys.stdin), sort_keys=True))
        else:
            raise ValueError
    except (ValueError, TypeError, RecursionError):
        sys.exit("Invalid trial ledger input; review the redacted record format before replay or append.")
