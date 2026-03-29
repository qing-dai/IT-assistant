import json
import logging

from openai import OpenAI
from pydantic import ValidationError

from config import LLM_JUDGE_MODEL
from models import LLMJudgeResult

logger = logging.getLogger(__name__)


def build_llm_prompt(source: str, title: str, body: str, fused_score: float) -> str:
    return f"""
You are evaluating whether a article or post should be kept in an enterprise IT newsfeed.

Keep only if the item is relevant for enterprise IT managers, such as:
- security incidents
- outages
- severe bugs or broken updates
- vendor advisories or deprecations with operational impact

Discard if it is mainly:
- troubleshooting discussion
- personal rant
- shopping/review content
- low-impact community discussion
- generic advice request

Return JSON only:
{{
  "keep": true,
  "relevance_score": 82,
  "reason": "short reason"
}}

Rules for relevance_score:
- 0 to 39: irrelevant
- 40 to 59: weakly relevant
- 60 to 74: relevant but not strong
- 75 to 100: highly relevant and worth surfacing

Source: {source}
Title: {title}
Body: {body or ""}
Initial hybrid score: {fused_score:.2f}
""".strip()


class LLMJudge:
    def __init__(self, model_name: str = LLM_JUDGE_MODEL) -> None:
        self.client = OpenAI()
        self.model_name = model_name

    def judge(self, source: str, title: str, body: str, fused_score: float) -> dict:
        prompt = build_llm_prompt(source, title, body, fused_score)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "developer",
                    "content": (
                        "Return only valid JSON that matches the provided schema. "
                        "Do not include markdown, comments, or extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "llm_judge_result",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "keep": {"type": "boolean"},
                            "relevance_score": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "reason": {"type": "string"},
                        },
                        "required": ["keep", "relevance_score", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            logger.error(f"LLM judge returned empty content for title='{title}'")
            raise RuntimeError("LLM judge returned empty content.")

        try:
            data = json.loads(content)
            validated = LLMJudgeResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"LLM judge invalid output for title='{title}': {content!r} — {e}")
            raise RuntimeError(f"Invalid LLM judge output: {content}") from e

        return {
            "keep": validated.keep,
            "relevance_score": validated.relevance_score,
            "normalized_score": validated.relevance_score / 100.0,
            "reason": validated.reason,
        }
