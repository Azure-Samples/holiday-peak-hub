# Roadmap & Known Issues

**Created**: February 27, 2026  
**Source**: Deployment validation audit (February 2026)

This folder tracks corrections, gaps, and planned enhancements discovered during architecture review and deployment validation.

## Issue Index

| # | Issue | Severity | Category | GitHub Issue |
|---|-------|----------|----------|--------------|
| 1 | [CRUD not registered in APIM](001-crud-apim-routing.md) | Critical | Infrastructure | [#25](https://github.com/Azure-Samples/holiday-peak-hub/issues/25) |
| 2 | [Agent health endpoints return 500](002-agent-health-500.md) | Critical | Agents | [#26](https://github.com/Azure-Samples/holiday-peak-hub/issues/26) |
| 3 | [SWA API proxy returns 404](003-swa-api-proxy-404.md) | High | Frontend | [#27](https://github.com/Azure-Samples/holiday-peak-hub/issues/27) |
| 4 | [Frontend pages use mock data](004-frontend-mock-data.md) | High | Frontend | [#28](https://github.com/Azure-Samples/holiday-peak-hub/issues/28) |
| 5 | [Lib config test failures](005-lib-config-test-failures.md) | Medium | Testing | [#29](https://github.com/Azure-Samples/holiday-peak-hub/issues/29) |
| 6 | [CI agent tests swallowed](006-ci-agent-tests-swallowed.md) | Medium | CI/CD | [#30](https://github.com/Azure-Samples/holiday-peak-hub/issues/30) |
| 7 | [Payments fully stubbed](007-payments-stubbed.md) | Medium | Backend | [#31](https://github.com/Azure-Samples/holiday-peak-hub/issues/31) |
| 8 | [AI Search not provisioned](008-ai-search-not-provisioned.md) | Medium | Infrastructure | [#32](https://github.com/Azure-Samples/holiday-peak-hub/issues/32) |
| 9 | [Route protection middleware implemented (resolved)](009-missing-middleware-ts.md) | Medium | Frontend | [#33](https://github.com/Azure-Samples/holiday-peak-hub/issues/33) |
| 13 | [AGC edge migration plan](013-agc-edge-migration.md) | High | Infrastructure | [#282](https://github.com/Azure-Samples/holiday-peak-hub/issues/282) - [#287](https://github.com/Azure-Samples/holiday-peak-hub/issues/287) |

### Feature Requests

| # | Feature | Priority | Category | GitHub Issue |
|---|---------|----------|----------|--------------|
| 10 | [PIM/DAM Agentic Workflow](010-pim-dam-feature-request.md) | High | Product Management | [#34](https://github.com/Azure-Samples/holiday-peak-hub/issues/34) |

## Categories

- **Infrastructure**: Azure resource configuration and deployment gaps
- **Agents**: AI agent service health and connectivity issues
- **Frontend**: UI/UX integration and data binding issues
- **Backend**: CRUD service and API implementation gaps
- **Testing**: Test failures and coverage gaps
- **CI/CD**: Pipeline configuration issues

## How to Contribute

1. Pick an issue from the index above
2. Create a feature branch: `feat/<issue-slug>`
3. Implement the fix with tests
4. Reference the issue in your PR description
5. Update this index when the issue is resolved
