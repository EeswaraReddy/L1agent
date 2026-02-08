import boto3
from common import parse_event, response_ok, response_error


cloudwatch = boto3.client("cloudwatch")


def handler(event, _context):
    body = parse_event(event)
    alarm_name = body.get("alarm_name")

    if not alarm_name:
        return response_error("alarm_name is required", event=event)

    resp = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
    alarms = resp.get("MetricAlarms", [])
    if not alarms:
        return response_ok({"alarm_name": alarm_name, "status": "not_found"}, event=event)

    alarm = alarms[0]
    return response_ok({
        "alarm_name": alarm_name,
        "state": alarm.get("StateValue"),
        "reason": alarm.get("StateReason"),
        "updated": alarm.get("StateUpdatedTimestamp").isoformat() if alarm.get("StateUpdatedTimestamp") else "",
    }, event=event)
