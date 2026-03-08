from agents.base import BaseAgent


class SummaryAgent(BaseAgent):
    name = "summary"
    system_prompt = (
        "You are a software analyst. Given a repository's README and file tree, "
        "write a concise summary (3-5 sentences) explaining what this project does, "
        "what problem it solves, and who it's for. Be clear and direct. "
        "Write your response in the same language as the README. If no README, use English."
    )

    def run(self, context: dict, **kwargs) -> dict:
        prompt = f"## README\n{context['readme'] or '(no README found)'}\n\n## File Tree\n{context['tree']}"
        result = self._generate(prompt)
        return {"summary": result}
