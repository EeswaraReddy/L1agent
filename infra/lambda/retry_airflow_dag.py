import json
import os
import urllib.request
import boto3
from common import parse_event, response_ok, response_error


mwaa = boto3.client("mwaa")


def handler(event, _context):
    body = parse_event(event)
    env_name = body.get("env_name") or os.environ.get("MWAA_ENV_NAME")
    dag_id = body.get("dag_id")
    run_id = body.get("run_id")

    if not env_name:
        return response_error("env_name is required", event=event)
    if not dag_id:
        return response_error("dag_id is required", event=event)

    token = mwaa.create_cli_token(Name=env_name)
    host = token["WebServerHostname"]
    cli_token = token["CliToken"]

    command = f"dags trigger {dag_id}"
    if run_id:
        command = f"{command} --run-id {run_id}"

    payload = json.dumps({"name": "dags trigger", "command": command}).encode("utf-8")
    req = urllib.request.Request(
        url=f"https://{host}/aws_mwaa/cli",
        data=payload,
        headers={"Authorization": f"Bearer {cli_token}", "Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")

    return response_ok({"status": "submitted", "dag_id": dag_id, "response": data}, event=event)
