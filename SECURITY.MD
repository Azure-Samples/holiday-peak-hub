# Security Policy

## Supported Versions

This repository currently supports the default branch:
- `main`

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.

Please do **not** open public issues for security reports.

1. Email the maintainers at **security@your-domain.example** with:
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

- Primary: security@your-domain.example

If you need a different contact method, update this file accordingly.
