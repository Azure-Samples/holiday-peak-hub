---
name: "Issue Engineering With Process"
description: "Run issue engineering with mandatory code-first investigation, BPMN issue creation, branch-per-issue execution, PR validation, merge monitoring, and branch cleanup. Use the issue-engineering-workflows skill templates."
agent: "TechLeadOrchestrator"
argument-hint: "Provide the list of requested changes, issue references (if any), constraints, and expected outcomes."
---

Execute issue engineering with strict process control:

0. **Skill Bootstrap (mandatory)**
   - Load `.github/skills/issue-engineering-workflows/SKILL.md`.
   - Select the matching template for create/correct/improve/feature/risk issue flows before drafting issues.

0.5 **ADR Preflight (mandatory for architecture-impacting items)**
   - Read `docs/architecture/ADRs.md` before scoping implementation.
   - Capture impacted ADRs, ADR update needs, or an explicit no-impact statement with assumptions.

1. **Code-First Reconnaissance (mandatory before any action)**
   - Read the relevant code paths first.
   - Use workspace search and file reads to confirm current behavior.
   - Call relevant specialists via `#runSubagent` before implementation when cross-domain analysis is needed:
       - `system-architect` for architecture/integration concerns
       - `python-specialist`, `typescript-specialist`, `rust-specialist`, `ui-agent`, `platform-quality` as applicable
   - Do not implement or open PRs before reconnaissance is complete.

2. **Per-Change Engineering Analysis (for every requested change item)**
   - Build an itemized list where each item includes:
     - Current behavior (with file/function evidence)
     - Required change
     - Affected components and risks
     - Effort estimate (S/M/L/XL + rough hours)
       - ADR impact (`ADR-###` references or explicit no-impact statement)
   - Keep each item atomic and independently traceable.

3. **Issue Creation With BPMN Format (mandatory before coding each item)**
   - For each item in the list, open one GitHub issue before implementation starts.
   - Each issue must include:
     - Problem statement
     - Acceptance criteria checklist
     - Risks and dependencies
     - BPMN-formatted process section using Mermaid (required), for example:

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
       A[Analyze Current Code] --> B[Design Change]
       B --> C[Implement on Issue Branch]
       C --> D[Open PR]
       D --> E[Validation and Fixes]
       E --> F[Merge to Main]
       F --> G[Monitor Workflows]
       G --> H[Close Issue and Cleanup]
     ```

4. **Branch-Per-Issue Execution**
   - Work each issue in a separate branch.
   - Create branches from `main` using repository branch naming policy.
   - Keep commits scoped to the corresponding issue only.

5. **PR-First Validation and Merge Discipline**
   - Open a PR for each issue branch targeting `main`.
   - Perform validation in the PR (tests, lint, review feedback).
   - Apply all fixes required for clean validation in the same open PR branch.
   - After checks and reviews pass, merge to `main`.
   - Monitor post-merge workflows/deployment and resolve regressions through PR updates until green.

6. **Issue and Remote Branch Closure**
   - After merge completion, close the related GitHub issue with merge evidence.
   - Delete the remote working branch.

7. **Local Branch and Repository Cleanup**
   - Switch to `main` and pull latest changes.
   - Delete the local working branch.
   - Confirm repository cleanup (`git status` clean, no stale branches for completed issues).

Deliver a final execution report containing:
- Issue list with BPMN links/sections
- Branch and PR mapping per issue
- Validation evidence and merge status
- Monitoring outcome
- Closure + cleanup confirmation
