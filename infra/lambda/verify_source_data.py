import os
import boto3
from common import parse_event, response_ok, response_error


s3 = boto3.client("s3")


def handler(event, _context):
    body = parse_event(event)
    bucket = body.get("bucket") or os.environ.get("SOURCE_DATA_BUCKET")
    prefix = body.get("prefix", "")
    min_objects = int(body.get("min_objects", 1))
    min_total_bytes = int(body.get("min_total_bytes", 1))

    if not bucket:
        return response_error("bucket is required", event=event)

    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = resp.get("Contents", [])
    total_bytes = sum(obj.get("Size", 0) for obj in contents)
    zero_objects = [obj["Key"] for obj in contents if obj.get("Size", 0) == 0]

    status = "ok"
    if len(contents) < min_objects:
        status = "missing_data"
    elif total_bytes < min_total_bytes:
        status = "zero_data"

    return response_ok({
        "bucket": bucket,
        "prefix": prefix,
        "object_count": len(contents),
        "total_bytes": total_bytes,
        "zero_byte_objects": zero_objects,
        "status": status,
    }, event=event)
