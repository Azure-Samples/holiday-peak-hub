# MkDocs Documentation Site

Local documentation site for Holiday Peak Hub using [MkDocs](https://www.mkdocs.org/) with the [Material](https://squidfunk.github.io/mkdocs-material/) theme.

## Setup

```bash
pip install mkdocs-material
```

## Commands

```bash
# From this directory (mkdocs/)
cd mkdocs

# Serve locally with hot-reload
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages (if configured)
mkdocs gh-deploy
```

## Structure

```
mkdocs/
  mkdocs.yml          # Site config (docs_dir: ../docs)
  stylesheets/        # Custom CSS
  overrides/           # Material theme overrides
  site/                # Build output (gitignored)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docs_dir` not found | Run commands from `mkdocs/` directory |
| Mermaid not rendering | Install `pymdownx` extensions (included with `mkdocs-material`) |
| Broken nav links | Verify file paths in `mkdocs.yml` nav match `docs/` structure |
| Strict mode warnings | Some links to files outside `docs/` are expected |
