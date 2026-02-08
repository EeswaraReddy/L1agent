import json
from urllib.parse import urljoin
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import get_session
from .config import AWS_REGION


class AgentcoreGatewayClient:
    def __init__(self, base_url: str, region: str = AWS_REGION, service: str = "execute-api") -> None:
        if not base_url:
            raise ValueError("GATEWAY_URL is required")
        self.base_url = base_url.rstrip("/") + "/"
        self.region = region
        self.service = service
        self.session = get_session()

    def _sign(self, method: str, url: str, body: str, headers: dict) -> dict:
        creds = self.session.get_credentials()
        if creds is None:
            raise RuntimeError("No AWS credentials available for SigV4 signing")
        req = AWSRequest(method=method, url=url, data=body, headers=headers)
        SigV4Auth(creds, self.service, self.region).add_auth(req)
        return dict(req.headers)

    def call_tool(self, tool_name: str, payload: dict) -> dict:
        url = urljoin(self.base_url, f"tools/{tool_name}")
        body = json.dumps(payload)
        headers = {"content-type": "application/json"}
        signed_headers = self._sign("POST", url, body, headers)
        resp = requests.post(url, data=body, headers=signed_headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
