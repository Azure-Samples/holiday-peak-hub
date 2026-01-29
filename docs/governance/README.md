# Governance and Compliance Guidelines

This folder contains comprehensive governance documentation for development and operations across the Holiday Peak Hub project.

## Overview

These documents define mandatory standards, coding conventions, architectural patterns, security policies, and compliance requirements that all team members must follow.

## Documents

### [Frontend Governance](frontend-governance.md)
**Audience**: Frontend developers, UI/UX engineers  
**Scope**: Next.js, React, TypeScript development

**Key Topics**:
- Tech stack and mandatory libraries
- ESLint 7 and TypeScript standards
- Atomic design component development
- State management (Redux Toolkit, TanStack Query)
- AG-UI Protocol compliance
- ACP frontend integration
- Authentication and security
- Testing requirements (80% coverage)
- Performance guidelines
- Accessibility standards (WCAG 2.1 AA)

---

### [Backend Governance](backend-governance.md)
**Audience**: Backend developers, API engineers  
**Scope**: Python FastAPI services, AI agents, adapters

**Key Topics**:
- Python 3.13 and PEP 8 standards
- Architecture patterns (Adapter, Builder, SAGA)
- Agent development with Microsoft Agent Framework
- Memory management (Hot/Warm/Cold tiers)
- FastAPI and MCP API design
- ACP (Agentic Commerce Protocol) compliance
- Security and authentication
- Testing requirements (80% coverage)
- Performance and async/await patterns
- Observability and structured logging

---

### [Infrastructure Governance](infrastructure-governance.md)
**Audience**: DevOps engineers, SREs, cloud architects  
**Scope**: Azure infrastructure, Kubernetes, CI/CD

**Key Topics**:
- Infrastructure as Code (Bicep)
- Azure services standards
- AKS and Helm deployment
- KEDA autoscaling
- Security and compliance (Key Vault, RBAC)
- Networking architecture
- Data persistence (Cosmos DB, Redis, Storage)
- Monitoring and observability
- Disaster recovery
- Cost management
- CI/CD pipeline standards

---

## Usage Guidelines

### For Developers

1. **Read relevant governance document(s)** before starting work
2. **Follow all mandatory standards** (marked with ✅ DO / ❌ DO NOT)
3. **Reference ADRs** linked in governance docs for decision context
4. **Update documentation** when patterns change
5. **Ask questions** if requirements are unclear

### For Reviewers

1. **Validate compliance** during code reviews
2. **Reference specific sections** when requesting changes
3. **Suggest improvements** to governance docs
4. **Escalate violations** to tech leads

### For Tech Leads

1. **Enforce governance** across all teams
2. **Update docs** when new decisions are made
3. **Communicate changes** to all stakeholders
4. **Conduct quarterly reviews** of governance effectiveness

---

## Compliance Levels

### 🔴 Critical (Must Follow)
- Security requirements
- Data protection policies
- Compliance standards (SOC 2, GDPR, PCI DSS)
- API authentication/authorization
- Infrastructure security (Key Vault, RBAC)

### 🟡 Important (Should Follow)
- Code style and linting
- Testing coverage minimums
- Performance guidelines
- Documentation requirements
- Naming conventions

### 🟢 Recommended (Best Practice)
- Component patterns
- Code organization
- Comments and docstrings
- Monitoring practices
- Optimization techniques

---

## Enforcement

### Automated Checks

**Frontend**:
- ESLint (pre-commit hook)
- TypeScript strict mode (build-time)
- Test coverage (CI pipeline)
- Lighthouse scores (CI pipeline)

**Backend**:
- Pylint (pre-commit hook)
- mypy type checking (build-time)
- pytest coverage (CI pipeline)
- Security scanning (CI pipeline)

**Infrastructure**:
- Bicep validation (pre-deploy)
- Azure Policy (runtime)
- Cost alerts (runtime)
- Security baseline checks (CI pipeline)

### Manual Reviews

- **Code Reviews**: All PRs require approval from governance-aware reviewer
- **Architecture Reviews**: Quarterly reviews with architecture team
- **Security Audits**: Annual third-party security audits
- **Compliance Audits**: SOC 2 Type II annual audit

---

## Document Structure

Each governance document follows this structure:

1. **Overview** - Purpose and scope
2. **Tech Stack** - Mandatory and prohibited technologies
3. **Standards** - Coding conventions and patterns
4. **Architecture** - Patterns and design principles
5. **Security** - Authentication, authorization, data protection
6. **Testing** - Coverage requirements and testing strategies
7. **Performance** - Optimization guidelines and targets
8. **Observability** - Logging, monitoring, telemetry
9. **References** - ADRs, external docs, specifications

---

## Updates and Versioning

### Version Format
`{major}.{minor}` (e.g., 1.0, 1.1, 2.0)

**Major Version**: Breaking changes (e.g., new mandatory tools, deprecated patterns)  
**Minor Version**: Additive changes (e.g., new guidelines, clarifications)

### Update Process

1. **Propose Change**: Create GitHub issue with rationale
2. **Discuss**: Tech lead review and team discussion
3. **Approve**: Architecture team approval required
4. **Document**: Update governance doc with version bump
5. **Communicate**: Announce changes in team channels
6. **Train**: Conduct training sessions if needed

### Changelog

See **Revision History** section at bottom of each document.

---

## Related Documentation

### Architecture
- [Architecture Overview](../architecture/architecture.md)
- [Architecture Decision Records (ADRs)](../architecture/ADRs.md)
- [Components Documentation](../architecture/components.md)

### Implementation
- [Backend Component Docs](../architecture/components/apps/)
- [Frontend Component Library](../../ui/components/COMPONENT_README.md)
- [Infrastructure Bicep Modules](../../infrastructure/bicep/modules/)

### Operations
- [Operational Playbooks](../architecture/playbooks/)
- [Incident Response](../architecture/playbooks/incident-response.md)

---

## Support

### Questions or Clarifications
- **Slack**: #engineering-governance
- **Email**: devops@holidaypeak.com
- **GitHub**: Open issue with `question` label

### Report Violations
- **Security violations**: security@holidaypeak.com (urgent)
- **Policy violations**: tech-lead@holidaypeak.com
- **Process issues**: Open GitHub issue

### Suggest Improvements
- **GitHub**: Open issue with `governance-improvement` label
- **Monthly meetings**: Governance review meetings (first Monday)

---

## Governance Principles

1. **Security First**: Security is non-negotiable
2. **Consistency Over Perfection**: Consistent patterns > perfect patterns
3. **Document Decisions**: All significant decisions must be documented in ADRs
4. **Automate Enforcement**: Prefer automated checks over manual reviews
5. **Continuous Improvement**: Governance evolves with the project
6. **Team Ownership**: Teams own and improve governance together

---

**Last Updated**: 2026-01-30  
**Document Owner**: Architecture Team  
**Next Review**: 2026-04-30
