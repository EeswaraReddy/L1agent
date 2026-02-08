import os


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", AWS_REGION)
MODEL_ID = os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")

GATEWAY_CONFIG_PATH = os.getenv("GATEWAY_CONFIG_PATH", "agentcore/gateway_config.json")
GATEWAY_URL = os.getenv("GATEWAY_URL", "")
GATEWAY_REGION = os.getenv("GATEWAY_REGION", AWS_REGION)

RCA_BUCKET = os.getenv("RCA_BUCKET", "")
RCA_PREFIX = os.getenv("RCA_PREFIX", "rca/")

STRANDS_ENABLE_LLM = os.getenv("STRANDS_ENABLE_LLM", "0") == "1"
