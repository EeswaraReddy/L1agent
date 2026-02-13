import json
from pathlib import Path

from agents.orchestrator import handle_incident


def _case_passed(case: dict, result: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    decision = result.get("policy", {}).get("decision")
    workflow_id = result.get("workflow", {}).get("workflow_id")
    evidence_coverage = float(result.get("evaluation", {}).get("evidence_coverage", 0.0))

    if decision != case.get("expected_decision"):
        issues.append(f"decision expected={case.get('expected_decision')} actual={decision}")

    expected_workflow = case.get("expected_workflow")
    if expected_workflow and workflow_id != expected_workflow:
        issues.append(f"workflow expected={expected_workflow} actual={workflow_id}")

    min_coverage = float(case.get("min_evidence_coverage", 0.0))
    if evidence_coverage < min_coverage:
        issues.append(f"evidence_coverage expected>={min_coverage} actual={evidence_coverage}")

    return (len(issues) == 0, issues)


def main() -> None:
    cases = json.loads(Path("examples/eval_cases.json").read_text(encoding="utf-8"))
    passed = 0

    for case in cases:
        result = handle_incident(case["incident"])
        ok, issues = _case_passed(case, result)
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {case['name']}")
        if not ok:
            for issue in issues:
                print(f"  - {issue}")
        else:
            passed += 1

    print(f"Passed {passed}/{len(cases)} cases")


if __name__ == "__main__":
    main()
