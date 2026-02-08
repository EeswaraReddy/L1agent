import argparse
import json
import sys
from bedrock_agentcore import BedrockAgentCoreApp
from .orchestrator import handle_incident


app = BedrockAgentCoreApp()


@app.entrypoint
def handler(payload, _context=None):
    return handle_incident(payload)


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to JSON incident payload")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = json.load(sys.stdin)

    result = handle_incident(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _cli()
    else:
        app.run()
