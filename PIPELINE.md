# Lean MCAT Course Pipeline

## Step 1: Build a compact context packet

Run inside WSL:

    cd /mnt/c/Users/sahar/mcat-tutor

    python3 scripts/build-context.py \
      --topic thermodynamics \
      --wiki-file wiki/thermodynamics.md \
      --graph wiki/.understand-anything/knowledge-graph.json \
      --output wiki/course/context/module-1-context.md \
      --keywords "free energy" entropy enthalpy gibbs equilibrium spontaneous

## Step 2: Generate one module

Launch Claude Code and give it the contents of:

    tasks/generate-module-1.txt

## Step 3: Validate deterministically

Run inside WSL:

    python3 scripts/validate-module.py course-data/module-1.json

The report will be written to:

    validation/module-1-report.json

## Step 4: Correct only validation errors

Give Claude Code only:

- `course-data/module-1.json`
- `validation/module-1-report.json`
- `schemas/module.schema.json`

Tell it to correct only the reported problems.

## Step 5: Assemble validated modules

Run inside WSL:

    python3 scripts/build-course.py

Validated modules will be assembled into:

    app/course-data.js

## Operating Principle

Use the model for language judgment.

Use deterministic code for:

- context filtering
- JSON validation
- course assembly
- duplicate detection
- required-field enforcement
- caching
