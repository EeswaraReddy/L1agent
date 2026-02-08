import boto3
from common import parse_event, response_ok, response_error


kafka = boto3.client("kafka")


def handler(event, _context):
    body = parse_event(event)
    cluster_arn = body.get("cluster_arn")

    if not cluster_arn:
        return response_error("cluster_arn is required", event=event)

    cluster = kafka.describe_cluster(ClusterArn=cluster_arn)
    brokers = kafka.get_bootstrap_brokers(ClusterArn=cluster_arn)

    return response_ok({
        "cluster": cluster.get("ClusterInfo", {}),
        "brokers": brokers,
    }, event=event)
