import asyncio
from pathlib import Path

from gemini_client import GeminiClient
from tools import ToolExecutor
from repo_manager import download_repo, cleanup
from context_builder import build_context

from agents.summary import SummaryAgent
from agents.structure import StructureAgent
from agents.code_overview import CodeOverviewAgent
from agents.architecture import ArchitectureAgent
from agents.quality import QualityAgent
from agents.features import FeaturesAgent


class Orchestrator:
    def __init__(self):
        self.client = GeminiClient()

    async def analyze(self, repo_url: str, on_progress=None) -> dict:
        async def progress(value: int, phase: str):
            if on_progress:
                await on_progress(value, phase)

        await progress(5, "Downloading repository...")
        repo_path = await download_repo(repo_url)

        try:
            await progress(15, "Building context...")
            context = build_context(repo_path)
            executor = ToolExecutor(repo_path)

            summary_agent = SummaryAgent(self.client)
            structure_agent = StructureAgent(self.client)
            code_overview_agent = CodeOverviewAgent(self.client, executor)
            architecture_agent = ArchitectureAgent(self.client, executor)
            quality_agent = QualityAgent(self.client)
            features_agent = FeaturesAgent(self.client)

            await progress(20, "Phase 1: Analyzing summary, structure, code...")
            summary_res, structure_res, code_overview_res = await asyncio.gather(
                asyncio.to_thread(summary_agent.run, context),
                asyncio.to_thread(structure_agent.run, context),
                asyncio.to_thread(code_overview_agent.run, context),
            )

            await progress(55, "Phase 2: Building architecture diagram...")
            architecture_res = await asyncio.to_thread(
                architecture_agent.run,
                context,
                summary=summary_res,
                code_overview=code_overview_res,
                structure=structure_res,
            )

            await progress(75, "Phase 3: Quality review & feature suggestions...")
            quality_res, features_res = await asyncio.gather(
                asyncio.to_thread(
                    quality_agent.run, context, architecture=architecture_res
                ),
                asyncio.to_thread(
                    features_agent.run,
                    context,
                    summary=summary_res,
                    architecture=architecture_res,
                    quality={},
                ),
            )

            await progress(95, "Compiling report...")
            return {
                "summary": summary_res.get("summary", ""),
                "structure": structure_res.get("structure", ""),
                "file_tree": structure_res.get("file_tree", context.get("tree", "")),
                "code_overview": code_overview_res.get("code_overview", ""),
                "architecture": architecture_res.get("architecture", ""),
                "quality": quality_res.get("quality", ""),
                "features": features_res.get("features", ""),
            }
        finally:
            cleanup(repo_path)
            await progress(100, "Done!")
