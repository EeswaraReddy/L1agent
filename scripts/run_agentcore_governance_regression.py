import json
import os
from pathlib import Path


os.environ["AGENTCORE_POLICY_ENABLED"] = "1"
os.environ["AGENTCORE_POLICY_STRICT"] = "1"
os.environ["AGENTCORE_EVALUATION_ENABLED"] = "1"
os.environ["AGENTCORE_EVALUATION_STRICT"] = "1"
os.environ.setdefault("AGENTCORE_MIN_EVAL_SCORE", "0.7")

from agents.agentcore_governance import enforce_governance_outcome  # noqa: E402


def _run_case(case: dict) -> tuple[bool, list[str], str, str]:
    decision, reasons = enforce_governance_outcome(
        decision=case["decision"],
        policy_context=case["policy_context"],
        evaluation_context=case["evaluation_context"],
    )

    issues: list[str] = []
    if decision != case["expected_decision"]:
        issues.append(f"decision expected={case['expected_decision']} actual={decision}")

    token = case.get("reason_token", "")
    joined = " | ".join(reasons)
    if token and token.lower() not in joined.lower():
        issues.append(f"reason token missing='{token}'")

    return len(issues) == 0, issues, decision, joined


def main() -> None:
    cases = json.loads(Path("examples/agentcore_governance_cases.json").read_text(encoding="utf-8"))
    passed = 0

    for case in cases:
        ok, issues, decision, _ = _run_case(case)
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {case['name']} -> {decision}")
        if not ok:
            for issue in issues:
                print(f"  - {issue}")
        else:
            passed += 1

    print(f"Passed {passed}/{len(cases)} cases")


if __name__ == "__main__":
    main()
