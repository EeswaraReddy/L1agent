import boto3
from common import parse_event, response_ok, response_error


glue = boto3.client("glue")


def handler(event, _context):
    body = parse_event(event)
    job_name = body.get("job_name")
    arguments = body.get("arguments", {})
    timeout = body.get("timeout")

    if not job_name:
        return response_error("job_name is required", event=event)

    kwargs = {"JobName": job_name, "Arguments": arguments}
    if timeout:
        kwargs["Timeout"] = int(timeout)

    resp = glue.start_job_run(**kwargs)
    return response_ok({"status": "submitted", "job_name": job_name, "job_run_id": resp.get("JobRunId")}, event=event)
