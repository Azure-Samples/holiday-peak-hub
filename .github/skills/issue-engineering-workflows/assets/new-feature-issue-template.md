## Title
[P1] <domain>: feature <summary>

## Business context
Describe user outcome, business value, and urgency.

## Scope
- In scope: <items>
- Out of scope: <items>

## Current behavior evidence
- <reference 1>
- <reference 2>

## Acceptance criteria
- [ ] Functional behavior is defined
- [ ] Non-functional constraints are defined
- [ ] Tests and verification path are defined
- [ ] Rollout and rollback expectations are defined

## Risks and dependencies
- Risk: <risk>
- Dependency: <dependency>

## BPMN process
```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart LR
  A[Assess Business Need] --> B[Analyze Current Code]
  B --> C[Define Atomic Feature Scope]
  C --> D[Open Feature Issue]
  D --> E[Implement on Branch]
  E --> F[PR Validation]
  F --> G[Merge and Monitor]
```
