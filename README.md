# GitArch

![banner](/static/banner.jpg)

Turn any GitHub repository into an interactive report with summary, file structure, code overview, architecture diagrams, quality review, and feature suggestions — powered by multi-agent AI.

## Features

- **Architecture Diagrams**: Auto-generated Mermaid.js system diagrams
- **Code Quality Review**: Issues, improvements, and best practice suggestions
- **Multi-Agent Pipeline**: 6 specialized AI agents analyze in parallel
- **Interactive Report**: Tabbed UI with summary, structure, code, architecture, quality, and features

## About

I built this because reading through an unfamiliar codebase is slow, especially when you just want to understand how things connect, what the architecture looks like, or where the weak points are.

GitArch solves this by running a multi-agent AI pipeline that reads the repository the way a senior developer would: starting from the structure, diving into the code, then building a coherent picture of the architecture and quality. Instead of spending an hour navigating files, you get an interactive report in minutes.

The focus is on understanding, not just summarizing, which is why each agent has a specific role and architecture is generated as an actual diagram rather than a text description. The goal is to let you grasp any repository as clearly and simply as possible, without getting lost in its complexity.

## Tech Stack

- **Backend**: FastAPI, Python
- **AI**: Google Gemini API (multi-agent with tool calling)
- **Frontend**: Jinja2, Mermaid.js, Marked.js, Highlight.js
- **Repo Handling**: GitHub ZIP API, httpx

## Quick Start

1. Clone the repository

```bash
git clone https://github.com/enesmanan/GitArch.git
cd GitArch
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Create a `.env` file and add your Gemini API key

```
GEMINI_API_KEY=your_key_here
```

4. Run

```bash
python main.py
```

Open http://localhost:8000

## How It Works

1. Enter a public GitHub repository URL
2. GitArch downloads and processes the codebase
3. A 3-phase multi-agent pipeline analyzes the repo in parallel
4. Results are compiled into an interactive tabbed report

### Agents

| Agent | Tools | What it does |
|---|---|---|
| Summary | - | Reads the README and file tree, writes a 3-5 sentence explanation of what the project does and who it's for |
| Structure | - | Analyzes the top-level modules and summarizes the purpose of each folder/component |
| Code Overview | `read_file`, `search_code` | Reads each file, explains what it does, and groups related modules together under their directory |
| Architecture | `read_file`, `search_code` | Builds a high-level Mermaid.js diagram, then searches for specific patterns (API flows, ML pipelines, RAG, auth, etc.) and draws separate diagrams for each one found |
| Quality | - | Reviews the code for unused imports, duplication, missing error handling, security issues, poor naming, and missing type hints — rates overall quality 1-10 |
| Features | - | Takes the full analysis as input and suggests up to 10 realistic improvements grouped by effort: quick wins, medium effort, and larger initiatives |

Made by [Enes Fehmi Manan](https://github.com/enesmanan) - [MIT](LICENSE)
