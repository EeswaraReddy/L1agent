import os
from datetime import datetime
import boto3
from common import parse_event, response_ok, response_error


s3 = boto3.client("s3")


def handler(event, _context):
    body = parse_event(event)
    bucket = body.get("bucket") or os.environ.get("LOG_BUCKET") or os.environ.get("RCA_BUCKET")
    prefix = body.get("prefix", "")
    max_objects = int(body.get("max_objects", 5))

    if not bucket:
        return response_error("bucket is required", event=event)

    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_objects)
    contents = resp.get("Contents", [])
    contents.sort(key=lambda x: x.get("LastModified", datetime.min), reverse=True)

    logs = []
    for obj in contents[:max_objects]:
        key = obj["Key"]
        obj_resp = s3.get_object(Bucket=bucket, Key=key)
        data = obj_resp["Body"].read()
        text = data.decode("utf-8", errors="replace")
        last_modified = obj.get("LastModified")
        logs.append({
            "key": key,
            "last_modified": last_modified.isoformat() if last_modified else "",
            "size": obj.get("Size", 0),
            "preview": "\n".join(text.splitlines()[-50:]),
        })

    return response_ok({"bucket": bucket, "prefix": prefix, "logs": logs}, event=event)
