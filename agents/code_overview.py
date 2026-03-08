from agents.base import ToolUsingAgent


class CodeOverviewAgent(ToolUsingAgent):
    name = "code_overview"
    system_prompt = (
        "You are a code analyst. Your job is to explain what each script/module does in the repository. "
        "You have access to tools to read files and search code. "
        "Rules:\n"
        "- For main/core scripts: write 2-3 sentences explaining what they do\n"
        "- For helper/utility scripts: write 1 sentence\n"
        "- For config files, boilerplate, or standard format files: skip or mention in one line\n"
        "- Group related files together under their module/directory\n"
        "- Use markdown formatting with headers for each module/directory\n"
        "- If a file seems important but wasn't provided, use the read_file tool to read it"
    )

    def run(self, context: dict, **kwargs) -> dict:
        file_summaries = []
        files = context.get("files") or {}
        for path, content in list(files.items())[:30]:
            file_summaries.append(f"### {path}\n```\n{content[:2000]}\n```")

        files_text = "\n\n".join(file_summaries)
        prompt = (
            f"## File Tree\n{context.get('tree', '')}\n\n"
            f"## File Contents (first batch)\n{files_text}\n\n"
            "Analyze these files and explain what each one does. "
            "If you see references to important files not included above, use read_file to check them."
        )
        result = self._generate_with_tools(prompt)
        return {"code_overview": result}
