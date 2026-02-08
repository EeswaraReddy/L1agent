from strands import Agent
from strands.models import BedrockModel
from .config import BEDROCK_REGION, MODEL_ID


def build_agent(system_prompt: str, tools=None) -> Agent:
    model = BedrockModel(model_id=MODEL_ID, region=BEDROCK_REGION)
    return Agent(system_prompt=system_prompt, model=model, tools=tools or [])
