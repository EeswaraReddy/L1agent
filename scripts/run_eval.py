import json
from pathlib import Path
from agents.orchestrator import handle_incident


def main() -> None:
    cases = json.loads(Path("examples/eval_cases.json").read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        result = handle_incident(case["incident"])
        decision = result.get("policy", {}).get("decision")
        ok = decision == case["expected_decision"]
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {case['name']} -> {decision}")
        if ok:
            passed += 1
    print(f"Passed {passed}/{len(cases)} cases")


if __name__ == "__main__":
    main()
