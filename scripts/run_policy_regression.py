import json
from pathlib import Path

from agents.policy import compute_policy_score


def _run_case(case: dict) -> tuple[bool, list[str], dict]:
    payload = case["input"]
    result = compute_policy_score(
        intent=payload["intent"],
        evidence=payload["evidence"],
        confidence=float(payload["confidence"]),
        workflow_profile=payload.get("workflow_profile"),
        evaluation=payload.get("evaluation"),
    ).model_dump()

    issues: list[str] = []

    expected_decision = case.get("expected_decision")
    if expected_decision and result.get("decision") != expected_decision:
        issues.append(f"decision expected={expected_decision} actual={result.get('decision')}")

    token = case.get("expected_reason_contains")
    if token:
        joined = " | ".join(result.get("reasons", []))
        if token.lower() not in joined.lower():
            issues.append(f"reason token missing='{token}'")

    return len(issues) == 0, issues, result


def main() -> None:
    cases = json.loads(Path("examples/policy_regression_cases.json").read_text(encoding="utf-8"))
    passed = 0

    for case in cases:
        ok, issues, result = _run_case(case)
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {case['name']} -> {result.get('decision')}")
        if not ok:
            for issue in issues:
                print(f"  - {issue}")
        else:
            passed += 1

    print(f"Passed {passed}/{len(cases)} cases")


if __name__ == "__main__":
    main()
