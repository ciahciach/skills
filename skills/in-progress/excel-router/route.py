"""Pure Excel router decision step. Reads one JSON request, writes one JSON result."""

import json
import sys
from typing import Any, Iterable


def validate_labels(values: Iterable[object]) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("expected non-empty labels")


def method_key(row: dict[str, Any]) -> tuple[str, str, str]:
    key = (row["interface"], row["version"], row["method"])
    validate_labels(key)
    return key


def decide(request: dict[str, Any], exclusions: list[dict[str, str]]) -> dict[str, Any]:
    scope = request["scope"]
    validate_labels(scope[field] for field in ("operation", "environment", "boundary"))
    if (scope["class"] not in ("runtime", "save")
            or scope["profile"] not in ("unknown", "simple", "application")
            or scope["target_kind"] not in ("synthetic", "target")):
        raise ValueError("invalid scope")
    for field in ("effects", "controls"):
        if not isinstance(scope[field], list):
            raise ValueError("expected a list of labels")
        validate_labels(scope[field])
    if scope["profile"] == "unknown":
        return {"decision": "blocked", "reason": "unknown-profile",
                "human_step": "Provide a verified workbook profile or authorize bounded passive profiling."}
    if not scope["controls"]:
        return {"decision": "blocked", "reason": "missing-checks",
                "human_step": f"Define a check that verifies the expected result of {scope['operation']}."}

    authorization, attempts, limit = None, [], None
    if "trial" in request:
        trial = request["trial"]
        authorization, attempts, limit = trial["authorization"], trial["attempts"], trial["limit"]
        if (authorization not in ("decision-only", "execute") or not isinstance(attempts, list)
                or (authorization == "decision-only" and attempts)
                or (limit is not None and (type(limit) is not int or limit < 1))):
            raise ValueError("invalid qualification plan")
        if scope["target_kind"] != "synthetic":
            return {"decision": "blocked", "reason": "qualification-needs-synthetic-input",
                    "human_step": "Name and separately authorize an isolated synthetic input for this operation."}

    evidence: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in request["evidence"]:
        if row["scope"] == scope:
            if row["outcome"] not in ("excluded", "verified"):
                raise ValueError("invalid evidence outcome")
            validate_labels((row["reference"],))
            evidence.setdefault(method_key(row), {})[row["outcome"]] = row["reference"]

    trial_methods = []
    interfaces = set()
    qualified = None
    for candidate in request["candidates"]:
        interface, version = candidate["interface"], candidate["version"]
        validate_labels((interface, version))
        if interface in interfaces or not isinstance(candidate["methods"], list):
            raise ValueError("invalid candidate")
        interfaces.add(interface)
        allowed = []
        for method in dict.fromkeys(candidate["methods"]):
            choice = {"interface": interface, "version": version, "method": method}
            matching = evidence.get(method_key(choice), {})
            if "excluded" in matching:
                exclusions.append({**choice, "reference": matching["excluded"]})
                continue
            allowed.append(choice)
            if qualified is None and "verified" in matching:
                qualified = {"decision": "selected", **choice, "qualification": matching["verified"]}
        trial_methods.extend(allowed[:5])

    if qualified is not None and not attempts:
        return qualified
    if authorization is not None:
        if limit is not None and len(attempts) > limit:
            raise ValueError("attempt count exceeds operation limit")
        controls = ", ".join(scope["controls"])
        human_step = f"Provide an authorized interface and version for {scope['operation']} that can demonstrate {controls}."
        if exclusions:
            interface, version, method = method_key(exclusions[-1])
            human_step = f"Provide an approved alternative to {interface} {version} method {method}, or new evidence of changed conditions."
        for index, attempt in enumerate(attempts):
            if index >= len(trial_methods) or method_key(attempt) != method_key(trial_methods[index]):
                raise ValueError("attempt does not match planned method")
            outcome = attempt["outcome"]
            if outcome in ("verified", "unresolved-effects") and index + 1 != len(attempts):
                raise ValueError("history continued after a terminal trial result")
            if outcome == "verified":
                return {"decision": "verified", **trial_methods[index]}
            if outcome == "unresolved-effects":
                return {"decision": "blocked", "reason": "unresolved-effects",
                        "human_step": "Account for the owned process and inspect the synthetic copy before any further operation."}
            interface, version, method = method_key(attempt)
            if outcome == "unavailable":
                human_step = f"Make {interface} {version} method {method} available in an approved session."
            elif outcome in ("gap", "not-verified") and attempt["control"] in scope["controls"]:
                human_step = f"Provide an authorized method that demonstrates {attempt['control']}."
            else:
                raise ValueError("unknown trial outcome")
        if limit is not None and len(attempts) == limit < len(trial_methods):
            return {"decision": "blocked", "reason": "operation-limit", "human_step": human_step}
        if len(attempts) < len(trial_methods):
            return {"decision": "trial" if authorization == "execute" else "candidate",
                    **trial_methods[len(attempts)],
                    "qualification": "NOT_VERIFIED"}
        return {"decision": "blocked", "reason": "methods-exhausted",
                "human_step": human_step}
    return {"decision": "blocked", "reason": "no-matching-evidence",
            "human_step": "Provide matching evidence or authorize an isolated synthetic qualification."}


if __name__ == "__main__":
    try:
        exclusions: list[dict[str, str]] = []
        result = decide(json.load(sys.stdin), exclusions)
        if exclusions:
            result["excluded"] = exclusions
        print(json.dumps(result))
    except (KeyError, TypeError, ValueError):
        sys.exit("Invalid router input; stop and reconcile the scope or trial history before any operation.")
