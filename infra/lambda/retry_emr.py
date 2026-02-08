import boto3
from common import parse_event, response_ok, response_error


emr = boto3.client("emr")


def handler(event, _context):
    body = parse_event(event)
    cluster_id = body.get("cluster_id")
    steps = body.get("steps", [])
    dry_run = bool(body.get("dry_run", False))

    if not cluster_id:
        return response_error("cluster_id is required", event=event)
    if not steps:
        return response_error("steps is required", event=event)

    if dry_run:
        return response_ok({"status": "dry_run", "cluster_id": cluster_id, "steps": steps}, event=event)

    resp = emr.add_job_flow_steps(JobFlowId=cluster_id, Steps=steps)
    return response_ok({"status": "submitted", "cluster_id": cluster_id, "step_ids": resp.get("StepIds", [])}, event=event)
