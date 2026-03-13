# Entra ID Configuration Guide

This guide explains how to configure Microsoft Entra ID (formerly Azure Active Directory) for the Holiday Peak Hub UI in local development and deployed environments.

---

## Table of Contents

1. [Overview](#overview)
2. [Running Without Entra (Anonymous / Guest Mode)](#running-without-entra-anonymous--guest-mode)
3. [Dev Mock Login Mode (Dev Only)](#dev-mock-login-mode-dev-only)
4. [App Registration — Step-by-Step](#app-registration--step-by-step)
5. [Local Development Configuration](#local-development-configuration)
6. [Deployed Environment Configuration](#deployed-environment-configuration)
7. [MSAL Frontend Configuration](#msal-frontend-configuration)
8. [CRUD Service JWT Validation](#crud-service-jwt-validation)
9. [RBAC Role Definitions](#rbac-role-definitions)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Authentication is handled by **Microsoft Entra ID** using the [MSAL](https://github.com/AzureAD/microsoft-authentication-library-for-js) library on the frontend and JWT Bearer validation on the CRUD service backend.

Key files:

| File | Purpose |
|------|---------|
| `apps/ui/lib/auth/msalConfig.ts` | MSAL client configuration, reads env vars |
| `apps/ui/contexts/AuthContext.tsx` | React context that wraps the whole app with MSAL |
| `apps/ui/.env.example` | Template listing all required environment variables |
| `apps/crud-service/` | FastAPI backend that validates Entra ID JWTs |

---

## Running Without Entra (Anonymous / Guest Mode)

Entra ID is **optional** in local development. When `NEXT_PUBLIC_ENTRA_CLIENT_ID` or `NEXT_PUBLIC_ENTRA_TENANT_ID` are not set, the application runs in anonymous/guest mode:

- No login popup is shown automatically.
- A **debug-level log** message is emitted in the browser console:
  ```
  UI running without Entra ID – authentication is disabled.
  ```
- The `useAuth()` hook returns `isAuthenticated: false` and `authConfigError` is populated.
- All public pages remain fully accessible.
- Features that require authentication (e.g. order history, checkout) will display a prompt or be disabled.

This behaviour is intentional and expected on developer machines that have not registered an Entra app.

---

## Dev Mock Login Mode (Dev Only)

For local UI scenario testing, the app supports a **dev-only mock auth mode** that provides role selection at `/auth/login` and sets a **signed** auth cookie consumed by middleware.

Environment variables:

```env
DEV_AUTH_MOCK=true
NEXT_PUBLIC_DEV_AUTH_MOCK=true
AUTH_COOKIE_SECRET=<dev-secret>
```

Behavior:

- Available roles: `customer`, `staff`, `admin`.
- Mock mode is **automatically disabled in production** even if `DEV_AUTH_MOCK=true`.
- Production deployments should keep `DEV_AUTH_MOCK=false` and use Entra login.
- Route protection behavior remains role-based (`/staff` requires `staff|admin`, `/admin` requires `admin`).

Safeguards:

- Mock login/logout API routes return `403` when mock mode is disabled.
- Mock auth uses a signed cookie that is validated by middleware before role checks are applied.
- Entra mode also uses a server-managed signed session cookie (`/api/auth/session`) validated by middleware; unsigned client-written role cookies are rejected.
- In production, `AUTH_COOKIE_SECRET` must be set for signed cookie operations; non-production can use a local fallback secret.

---

## App Registration — Step-by-Step

You need **one app registration** for the UI (and optionally a separate one for the API, which the UI calls on behalf of the user).

### 1. Create the UI App Registration

1. Open the [Azure Portal](https://portal.azure.com) and navigate to **Entra ID → App registrations → New registration**.
2. Fill in:
   - **Name**: `HolidayPeakHub-UI` (or any meaningful name).
   - **Supported account types**: *Accounts in this organizational directory only* (single tenant) or *Accounts in any organizational directory* (multi-tenant) — choose based on your requirements.
   - **Redirect URI**: Select **Single-page application (SPA)** and enter `http://localhost:3000` for local dev.
3. Click **Register**.
4. On the overview page, copy:
   - **Application (client) ID** → used as `NEXT_PUBLIC_ENTRA_CLIENT_ID`.
   - **Directory (tenant) ID** → used as `NEXT_PUBLIC_ENTRA_TENANT_ID`.

### 2. Configure Redirect URIs

Under **Authentication → Platform configurations → Single-page application**, add all redirect URIs you need:

| Environment | URI |
|-------------|-----|
| Local dev | `http://localhost:3000` |
| Staging | `https://<staging-hostname>` |
| Production | `https://<production-hostname>` |

Enable **Implicit grant** only if your MSAL version requires it (MSAL v2+ with auth code + PKCE does **not** need it).

### 3. Add API Permissions

Under **API permissions → Add a permission**:

- **Microsoft Graph** → Delegated → `openid`, `profile`, `email`, `User.Read`.
- If you have a separate API app registration, add a delegated scope for it (e.g. `api://<API_CLIENT_ID>/user_impersonation`).

Click **Grant admin consent** if your tenant requires it.

### 4. (Optional) Expose an API Scope

If the CRUD service validates tokens issued for a specific audience:

1. Go to **Expose an API → Add a scope**.
2. Set **Application ID URI** to `api://<UI_CLIENT_ID>` (or a custom URI).
3. Add a scope named `user_impersonation` with admin + user consent.

Update `apiRequest.scopes` in `apps/ui/lib/auth/msalConfig.ts` accordingly.

---

## Local Development Configuration

1. Copy the example file:
   ```bash
   cp apps/ui/.env.example apps/ui/.env.local
   ```
2. Fill in the values:
   ```env
   NEXT_PUBLIC_ENTRA_CLIENT_ID=<Application (client) ID>
   NEXT_PUBLIC_ENTRA_TENANT_ID=<Directory (tenant) ID>
   NEXT_PUBLIC_CRUD_API_URL=http://localhost:8000
   ```
3. Start the dev server:
   ```bash
   cd apps/ui && yarn dev
   ```

> **Tip**: If you are only working on UI components and do not need real authentication, leave `NEXT_PUBLIC_ENTRA_CLIENT_ID` and `NEXT_PUBLIC_ENTRA_TENANT_ID` empty and the app will run in anonymous mode.

---

## Deployed Environment Configuration

For staging and production, set environment variables in the hosting platform (Azure Static Web Apps, App Service, or similar). Do **not** commit real credentials to the repository.

### Azure Static Web Apps

In the Azure Portal, navigate to your Static Web App → **Configuration → Application settings** and add:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_ENTRA_CLIENT_ID` | `<client ID>` |
| `NEXT_PUBLIC_ENTRA_TENANT_ID` | `<tenant ID>` |
| `NEXT_PUBLIC_CRUD_API_URL` | `<CRUD service URL>` |
| `NEXT_PUBLIC_AGENT_API_URL` | `<Agent service URL>` |
| `AUTH_COOKIE_SECRET` | `<strong random secret>` |
| `DEV_AUTH_MOCK` | `false` |
| `NEXT_PUBLIC_DEV_AUTH_MOCK` | `false` |

Production safety requirements:
- Keep `DEV_AUTH_MOCK=false` and `NEXT_PUBLIC_DEV_AUTH_MOCK=false` in all deployed environments.
- Set `AUTH_COOKIE_SECRET` to a strong secret (minimum 32+ random characters) so signed auth cookies are valid across API routes and middleware.

Alternatively, reference Azure Key Vault secrets via the Key Vault Reference syntax: `@Microsoft.KeyVault(SecretUri=...)`.

### GitHub Actions / AZD Workflow

The `.github/workflows/deploy-azd.yml` workflow already sets UI deploy-time `NEXT_PUBLIC_ENTRA_CLIENT_ID` and `NEXT_PUBLIC_ENTRA_TENANT_ID` from repository/environment variables.

CRUD `ENTRA_*` runtime env wiring is not explicit by default in that workflow; add optional/custom mappings when you want workflow-managed backend injection.

If you want CI-managed wiring, add explicit mappings in your workflow and/or azd environment values. Example optional pattern:

```yaml
env:
  NEXT_PUBLIC_ENTRA_CLIENT_ID: ${{ secrets.ENTRA_CLIENT_ID }}
  NEXT_PUBLIC_ENTRA_TENANT_ID: ${{ secrets.ENTRA_TENANT_ID }}
   AUTH_COOKIE_SECRET: ${{ secrets.AUTH_COOKIE_SECRET }}
   DEV_AUTH_MOCK: false
   NEXT_PUBLIC_DEV_AUTH_MOCK: false
```

### Deployed CRUD service env wiring

When Entra validation is enabled for deployed CRUD service endpoints, set the backend env vars explicitly:

| Name | Value |
|------|-------|
| `ENTRA_TENANT_ID` | `<Directory (tenant) ID>` |
| `ENTRA_CLIENT_ID` | `<API application (client) ID used as token audience>` |

Where to set them:
- **Deployed service environment** (App Service, ACA, AKS Helm values, or equivalent): add `ENTRA_TENANT_ID` and `ENTRA_CLIENT_ID` as runtime env vars for `apps/crud-service`.
- **Deployment workflow** (`.github/workflows/deploy-azd.yml`, optional customization): map from secrets (for example `secrets.ENTRA_TENANT_ID` and `secrets.ENTRA_CLIENT_ID`) into CRUD deployment env values if you want workflow-managed injection.
- **Key Vault references**: if your deployment supports Key Vault reference syntax, store both IDs as Key Vault secrets and reference them in the deployed env configuration instead of hardcoding values.

---

## MSAL Frontend Configuration

MSAL is initialised in `apps/ui/contexts/AuthContext.tsx`. The key settings are read from environment variables via `apps/ui/lib/auth/msalConfig.ts`:

```ts
// apps/ui/lib/auth/msalConfig.ts (excerpt)
const entraClientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID || '';
const entraTenantId = process.env.NEXT_PUBLIC_ENTRA_TENANT_ID || '';

export const getMsalConfig = () => ({
  auth: {
    clientId: entraClientId,
    authority: `https://login.microsoftonline.com/${entraTenantId || 'common'}`,
    redirectUri: window.location.origin,
  },
  cache: { cacheLocation: 'sessionStorage' },
});
```

Token caching uses `sessionStorage` by default. Change `cacheLocation` to `localStorage` if you need tokens to persist across browser tabs.

---

## CRUD Service JWT Validation

The FastAPI CRUD service validates Entra ID JWTs on protected endpoints. Configure the service with:

| Environment Variable | Description |
|----------------------|-------------|
| `ENTRA_TENANT_ID` | Entra tenant ID for JWT issuer validation |
| `ENTRA_CLIENT_ID` | API app client ID (audience claim) |

The service verifies:
- Token signature against Microsoft's JWKS endpoint.
- `iss` claim matches `https://login.microsoftonline.com/<tenant>/v2.0`.
- `aud` claim matches the configured `ENTRA_CLIENT_ID`.

---

## RBAC Role Definitions

Four application roles are defined in the app manifest:

| Role | Value | Description |
|------|-------|-------------|
| Admin | `Admin` | Full access including user management and configuration |
| Staff | `Staff` | Access to inventory, orders, and CRM features |
| Customer | `Customer` | Standard shopping and order tracking |
| Guest | `Guest` | Read-only access to the product catalog |

To assign roles:
1. In the Azure Portal, go to **Entra ID → Enterprise applications → <your app>**.
2. Navigate to **Users and groups → Add user/group**.
3. Select the user (or group) and assign the desired role.

---

## Troubleshooting

### "UI running without Entra ID – authentication is disabled."

This **debug** message in the browser console is expected when `NEXT_PUBLIC_ENTRA_CLIENT_ID` and/or `NEXT_PUBLIC_ENTRA_TENANT_ID` are not set. Set these variables in `.env.local` to enable authentication.

### Login popup is blocked

Most browsers block popups by default. Either allow popups for `localhost`, or switch to the redirect flow by replacing `loginPopup` with `loginRedirect` in `AuthContext.tsx`.

### `AADSTS50011` — reply URL mismatch

The redirect URI used by MSAL does not match any URI registered in the app registration. Add the current origin (e.g. `http://localhost:3000`) under **Authentication → Redirect URIs** in the Azure Portal.

### `AADSTS70011` — invalid scope

The requested scope is not registered on the API app registration. Ensure the scope exists under **Expose an API** and that the client app has been granted permission to it.

### Token acquired but API returns 401

Verify that:
1. The CRUD service `ENTRA_CLIENT_ID` matches the audience in the token (`aud` claim).
2. The user has been assigned an appropriate application role.
3. The JWT has not expired (check `exp` claim).
