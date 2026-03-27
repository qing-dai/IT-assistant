import json

from openai import OpenAI


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
    def __init__(self, model_name: str = "gpt-5") -> None:
        self.client = OpenAI()
        self.model_name = model_name

    def judge(self, source: str, title: str, body: str, fused_score: float) -> dict:
        prompt = build_llm_prompt(source, title, body, fused_score)

        response = self.client.responses.create(
            model=self.model_name,
            input=prompt,
        )

        text = response.output_text
        data = json.loads(text)

        relevance_score = int(data["relevance_score"])
        relevance_score = max(0, min(relevance_score, 100))

        return {
            "keep": bool(data["keep"]),
            "relevance_score": relevance_score,
            "normalized_score": relevance_score / 100.0,
            "reason": data.get("reason", ""),
        }
