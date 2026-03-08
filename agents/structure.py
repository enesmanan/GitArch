from agents.base import BaseAgent


class StructureAgent(BaseAgent):
    name = "structure"
    system_prompt = (
        "You are a software analyst. Given a repository file tree, "
        "write 2-3 sentences summarizing the top-level modules and their purpose. "
        "Do NOT list every file. Just give a high-level overview of what the main folders/modules do."
    )

    def run(self, context: dict, **kwargs) -> dict:
        prompt = f"## File Tree\n{context['tree']}"
        summary = self._generate(prompt)
        return {
            "structure": summary,
            "file_tree": context.get("tree", ""),
        }
