## Title
[P2] <component>: improve <issue quality or process>

## Problem statement
Explain what is incomplete or ambiguous in the current issue and why improvement is needed.

## Improvement goals
- Better acceptance criteria
- Stronger dependency mapping
- Clear owner and sequencing

## Acceptance criteria
- [ ] Issue has measurable acceptance checklist
- [ ] Risks and dependencies are explicit
- [ ] Effort sizing and ownership are defined
- [ ] BPMN section is present

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
  A[Review Current Issue] --> B[Identify Gaps]
  B --> C[Refine Acceptance Criteria]
  C --> D[Add Risks and Dependencies]
  D --> E[Update Issue]
  E --> F[Execute via PR Workflow]
```
