---
applyTo: '.github/**'
description: Canonical and immutable rule for .github directory state.
---

# Canonical Rule for .github

The current state of the `.github` directory is canonical.

It is managed by an external application running on the repository owner's computer, not by manual edits from contributors or coding agents.

This is an immutable repository rule:

- Do not modify files under `.github` as part of regular code changes.
- Do not propose or apply drift fixes under `.github` unless they come from the external management application.
- Treat any local/manual change in `.github` as non-authoritative.