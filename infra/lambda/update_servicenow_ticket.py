import os
import json
import urllib.request
from common import parse_event, response_ok, response_error


def handler(event, _context):
    body = parse_event(event)
    instance_url = body.get("instance_url") or os.environ.get("SERVICENOW_INSTANCE_URL")
    username = body.get("username") or os.environ.get("SERVICENOW_USERNAME")
    password = body.get("password") or os.environ.get("SERVICENOW_PASSWORD")
    ticket_sys_id = body.get("ticket_sys_id")
    payload = body.get("payload", {})

    if not instance_url:
        return response_error("instance_url is required", event=event)
    if not username or not password:
        return response_error("username/password are required", event=event)
    if not ticket_sys_id:
        return response_error("ticket_sys_id is required", event=event)

    url = instance_url.rstrip("/") + f"/api/now/table/incident/{ticket_sys_id}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    auth = (f"{username}:{password}").encode("utf-8")
    req.add_header("Authorization", "Basic " + __import__("base64").b64encode(auth).decode("utf-8"))

    with urllib.request.urlopen(req, timeout=20) as resp:
        resp_body = resp.read().decode("utf-8")

    return response_ok({"status": "updated", "response": resp_body}, event=event)
