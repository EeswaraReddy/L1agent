from typing import Dict, Any
from .mcp_tools import call_gateway_tool
from .tool_registry import resolve_tool_name


DECISION_TO_STATE = {
    "auto_close": "Resolved",
    "auto_retry": "In Progress",
    "escalate": "Assigned",
    "human_review": "On Hold",
    "update_only": "In Progress",
}


def update_ticket(payload: Dict[str, Any], decision: str, rca_text: str) -> Dict[str, Any]:
    tool = resolve_tool_name("update_servicenow_ticket")
    status = DECISION_TO_STATE.get(decision, "In Progress")

    ticket_sys_id = payload.get("ticket_sys_id")
    instance_url = payload.get("instance_url")
    username = payload.get("username")
    password = payload.get("password")

    update_payload = {
        "state": status,
        "close_code": "Solved (Permanently)",
        "close_notes": rca_text,
        "work_notes": rca_text,
    }

    return call_gateway_tool(tool, {
        "instance_url": instance_url,
        "username": username,
        "password": password,
        "ticket_sys_id": ticket_sys_id,
        "payload": update_payload,
    })
