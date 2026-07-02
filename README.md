# MCAT AI Tutor

Static lesson app and validation pipeline for source-grounded MCAT study modules.

## Portfolio Preview

From the repository root:

```bash
python -m http.server 8000
```

Then open:

- `http://localhost:8000/app/portfolio.html` for the portfolio showcase page
- `http://localhost:8000/app/index.html` for the student lesson demo

The portfolio page is static and reuses existing repository assets:

- `app/course-data.js` for chapter content
- `validation/module-*-report.json` for validation status
- `benchmarks/production-pilot/output/*` for pilot metrics

## Local Full Stack with Open Notebook

From the repository root:

```bash
docker compose up
```

Local service URLs:

- MCAT tutor learner UI: `http://localhost:8765`
- Open Notebook admin/source UI: `http://localhost:8502`
- Open Notebook REST API: `http://localhost:5055`
- SurrealDB: `http://localhost:8000`

Open Notebook is used for admin/source management and retrieval. The MCAT tutor
app remains the learner-facing UI; learner-visible answers still flow through
the tutor Council verification gates before citation-backed content is shown.

## GitHub Pages Deployment

The public GitHub Pages bundle lives under `docs/`.

- GitHub Pages source: `main` branch, `/docs` folder
- Public entrypoint: `docs/index.html`
- Expected URL: `https://srao189.github.io/ai-mcat-tutor/`

For a local check of the Pages bundle only:

```bash
cd docs
python -m http.server 8000
```

Then open:

- `http://localhost:8000/` for the showcase homepage
- `http://localhost:8000/demo.html` for the public lesson demo

The `docs/` site is intentionally static and sanitized:

- includes only CSS, JavaScript, and public preview lesson data needed for the showcase
- excludes source PDFs, environment files, private logs, and local filesystem paths
- uses relative links so it works under the `/ai-mcat-tutor/` project subpath on GitHub Pages
