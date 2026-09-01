"""Intent Analyzer parsing user commands into structured Goal representations."""

import json
from enum import Enum
from pydantic import BaseModel, Field
from sae.providers.base import AICapability, AIRequest
from sae.providers.router import ModelRouter


class IntentRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UserIntent(BaseModel):
    objective: str
    actions: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    is_ambiguous: bool = False
    clarification_prompt: str | None = None
    risk_level: IntentRisk = IntentRisk.LOW


class IntentAnalyzer:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def analyze(self, command: str) -> UserIntent:
        if not command or command.strip() == "":
            return UserIntent(
                objective="Empty command",
                is_ambiguous=True,
                clarification_prompt="Command cannot be empty. Please specify an action."
            )

        system_instruction = (
            "You are the Intent Analyzer for Stay Angry Engine (SAE). "
            "Convert user input into a JSON object matching this schema: "
            '{"objective": str, "actions": [str], "entities": [str], "constraints": [str], '
            '"is_ambiguous": bool, "clarification_prompt": str|null, "risk_level": "LOW"|"MEDIUM"|"HIGH"}. '
            "If the request lacks vital details (e.g. deleting without target), set is_ambiguous: true. "
            "Output ONLY valid JSON."
        )

        request = AIRequest(
            prompt=f"User Command: {command}",
            system_instruction=system_instruction,
            required_capabilities=[AICapability.TEXT, AICapability.STRUCTURED_OUTPUT]
        )

        response = await self.router.route_and_generate(request)
        if not response.success or not response.content:
            return UserIntent(
                objective=command,
                actions=[command],
                risk_level=IntentRisk.LOW
            )

        try:
            cleaned = response.content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return UserIntent(**data)
        except Exception:
            return UserIntent(
                objective=command,
                actions=[command],
                risk_level=IntentRisk.LOW
            )