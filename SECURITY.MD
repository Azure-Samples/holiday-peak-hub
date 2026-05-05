# Security Policy

**Last Updated**: 2026-04-30

## Supported Versions

This repository currently supports the default branch:
- `main`

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Security Architecture

- **Authentication**: Microsoft Entra ID with JWT validation + RBAC (4 roles: anonymous, customer, staff, admin)
- **Secrets management**: Azure Key Vault (no secrets in source or env literals)
- **Identity**: Managed Identity and Entra-based federation for deployment identities (OIDC)
- **Network**: Private Endpoints, NSGs, AGC for edge routing
- **CI scanning**: CodeQL (weekly + PR), pip-audit, Dependabot (grouped updates)
- **Governance**: Weekly security triage via `security-triage-report.yml` workflow

## Reporting a Vulnerability

Please do **not** open public issues for security reports.

1. Email the maintainers at **rcataldi@microsoft.com** with:
   - A detailed description of the issue
   - Steps to reproduce (if applicable)
   - Affected files, services, or endpoints
   - Any suggested remediation
2. You should receive an acknowledgment within **3 business days**.
3. We will work with you on a fix and coordinated disclosure.

If the issue is urgent, include **"URGENT"** in the email subject.

## Security Rules for This Repo

- **Secrets**: Never commit secrets, tokens, or keys. Use environment variables and local secret stores.
- **Dependency Hygiene**: Keep dependencies updated and prefer pinned versions. Avoid unverified packages.
- **Least Privilege**: Use the minimum permissions required for services and credentials.
- **Data Handling**: Do not commit production data. Use synthetic or anonymized datasets for tests.
- **Logging**: Avoid logging sensitive data (PII, credentials, tokens).
- **PR Requirements**: Security-related changes must be reviewed by a maintainer.
- **CI/CD**: Do not bypass CI checks for security fixes unless explicitly approved.
- **Disclosure**: Coordinate disclosures with maintainers before public release.

## Security Contact

- Primary: rcataldi@microsoft.com

If you need a different contact method, update this file accordingly.
