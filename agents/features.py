from agents.base import BaseAgent


class FeaturesAgent(BaseAgent):
    name = "features"
    system_prompt = (
        "You are a product-minded software engineer. Based on the project analysis, "
        "suggest realistic next features and improvements.\n\n"
        "RULES:\n"
        "- Be realistic - don't suggest moonshot features\n"
        "- Prioritize suggestions by impact and effort\n"
        "- Consider the current architecture when suggesting\n"
        "- Group into: Quick Wins (easy), Medium Effort, and Larger Initiatives\n"
        "- For each suggestion: one sentence what, one sentence why\n"
        "- Max 10 suggestions total\n"
        "- Use markdown formatting"
    )

    def run(self, context: dict, **kwargs) -> dict:
        summary = kwargs.get("summary", {}).get("summary", "")
        architecture = kwargs.get("architecture", {}).get("architecture", "")
        quality = kwargs.get("quality", {}).get("quality", "")

        prompt = (
            f"## Project Summary\n{summary}\n\n"
            f"## Architecture\n{architecture}\n\n"
            f"## Quality Review\n{quality}\n\n"
            "Based on this analysis, suggest the next realistic features and improvements."
        )
        result = self._generate(prompt)
        return {"features": result}
