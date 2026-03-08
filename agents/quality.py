from agents.base import BaseAgent


class QualityAgent(BaseAgent):
    name = "quality"
    system_prompt = (
        "You are a code quality reviewer. Analyze the codebase and identify issues.\n\n"
        "Look for:\n"
        "- Unused imports or dead code\n"
        "- Code duplication / repeated patterns\n"
        "- Hardcoded values that should be configurable\n"
        "- Missing error handling\n"
        "- Poor naming conventions\n"
        "- Security concerns (exposed secrets, SQL injection, etc.)\n"
        "- Missing type hints (for Python)\n"
        "- Overly complex functions\n\n"
        "OUTPUT FORMAT:\n"
        "Use markdown with these sections:\n"
        "## Issues Found\n"
        "(list each issue with file path and brief explanation)\n\n"
        "## Improvement Suggestions\n"
        "(actionable suggestions ranked by impact)\n\n"
        "## Overall Quality Score\n"
        "(rate 1-10 with brief justification)\n\n"
        "Be constructive, not nitpicky. Focus on impactful issues.\n\n"
        "IMPORTANT: Do NOT flag model names, API identifiers, or library/package names as errors "
        "based on your training data. Your knowledge has a cutoff date — newer models, APIs, and "
        "libraries may exist that you are unaware of. Never say a model 'does not exist' or 'is not "
        "available'. Only flag issues that are clearly visible in the code logic itself."
    )

    def run(self, context: dict, **kwargs) -> dict:
        architecture = kwargs.get("architecture", {}).get("architecture", "")
        arch_summary = architecture[:2000] if architecture else ""

        file_summaries = []
        for path, content in list(context["files"].items())[:10]:
            file_summaries.append(f"### {path}\n```\n{content[:2000]}\n```")
        files_text = "\n\n".join(file_summaries)

        prompt = (
            f"## Architecture Overview\n{arch_summary}\n\n"
            f"## Code Files\n{files_text}\n\n"
            "Review this code for quality issues."
        )
        result = self._generate(prompt)
        return {"quality": result}
