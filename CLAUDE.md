# MCAT Course Builder

## Core Rules

Use only files explicitly named in the current task.

Do not add outside factual knowledge.
Mark unsupported information as:

`SOURCE GAP`

Never make parallel tool calls.
Sequential tool calls are allowed within the same task.

Complete one artifact per task.
Do not inspect unrelated files.
Do not edit files other than the explicitly named output.

Prefer concise structured JSON over large Markdown or HTML files.

Stop immediately after completing and validating the requested artifact.

## Project Structure

- `raw/` — canonical source material
- `wiki/` — cleaned source articles
- `wiki/course/context/` — compact module-specific source packets
- `schemas/` — JSON schemas
- `course-data/` — generated structured lessons
- `validation/` — deterministic validation reports
- `app/` — fixed course interface
- `scripts/` — deterministic build and validation tools
- `tasks/` — reusable focused prompts

## Course Workflow

1. Build one compact module context file.
2. Generate one module JSON file.
3. Validate it using local code.
4. Correct only the reported errors.
5. Cache the completed artifact.
6. Do not regenerate completed modules unnecessarily.
7. Build the interface from validated JSON only.

## Model Responsibilities

Use the language model for:

- explanations
- lesson organization
- worked examples supported by the sources
- questions supported by the sources
- concise summaries

Use deterministic code for:

- file discovery
- graph filtering
- JSON validation
- required-field checks
- source-reference checks
- course assembly
- duplicate detection
