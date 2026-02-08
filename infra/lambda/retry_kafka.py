from common import parse_event, response_ok


def handler(event, _context):
    body = parse_event(event)
    return response_ok({
        "status": "manual_required",
        "details": "Kafka retries typically require replay from a DLQ or reprocessing job. Provide a runbook action.",
        "input": body,
    }, event=event)
