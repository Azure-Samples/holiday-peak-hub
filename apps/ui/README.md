# UI

## Purpose
Provides the Next.js frontend for Holiday Peak Hub operations and workflows.

## Responsibilities
- Render admin and operations interfaces for retail workflows.
- Call backend APIs for transactional and intelligence scenarios.
- Provide a single web entry point for platform users.

## Key endpoints or interfaces
- Next.js app interface served through the standard web root.
- API integration targets are configured through frontend environment variables.

## Run/Test commands
```bash
yarn --cwd apps/ui install
yarn --cwd apps/ui dev
yarn --cwd apps/ui test
```

## Configuration notes
- Uses frontend environment variables for backend/API URLs and auth integration.
- Build and runtime behavior are controlled by `apps/ui/package.json` scripts.
- Uses Next.js and TypeScript toolchain configured in the UI app directory.
