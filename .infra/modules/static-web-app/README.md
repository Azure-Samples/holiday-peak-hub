# Static Web App Module

This module provisions **Azure Static Web Apps** for the Holiday Peak Hub frontend (Next.js application).

## What's Deployed

- **Azure Static Web App** - Serverless hosting for Next.js static export
  - Free tier (dev/staging)
  - Standard tier (prod) with enterprise CDN
- **GitHub Actions Integration** - Automatic CI/CD on push to main
- **Custom Domain** (prod only) - www.holidaypeakhub.com

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Azure Static Web Apps                                    │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Frontend (Next.js)                                   │ │
│ │ - Homepage                                           │ │
│ │ - Product Pages                                      │ │
│ │ - Checkout                                           │ │
│ │ - Dashboard                                          │ │
│ │ - Staff/Admin Pages                                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                          │                               │
│                          ▼                               │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Azure CDN (Global Edge Locations)                    │ │
│ │ - Static assets (JS, CSS, images)                   │ │
│ │ - Automatic caching                                  │ │
│ │ - Brotli compression                                 │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Azure API Management   │
              │ (Backend APIs)         │
              └───────────────────────┘
```

## Next.js Configuration

The frontend must be configured for **static export** (no server-side rendering in Azure Static Web Apps).

### Required Changes to `next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export', // Enable static export
  images: {
    unoptimized: true, // Disable Next.js Image Optimization (not supported in static export)
  },
  trailingSlash: true, // Add trailing slashes to URLs
  // Environment variables (injected at build time)
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001',
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT || 'dev',
  },
}

module.exports = nextConfig
```

### Update `package.json`

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "export": "next build && next export"
  }
}
```

## Deployment

### Option 1: Bicep Deployment

```bash
# Deploy to dev environment
az deployment sub create \
  --location eastus2 \
  --template-file .infra/modules/static-web-app/static-web-app-main.bicep \
  --parameters environment=dev \
               repositoryUrl='https://github.com/Azure-Samples/holiday-peak-hub' \
               branch='main'

# Deploy to production
az deployment sub create \
  --location eastus2 \
  --template-file .infra/modules/static-web-app/static-web-app-main.bicep \
  --parameters environment=prod \
               repositoryUrl='https://github.com/Azure-Samples/holiday-peak-hub' \
               branch='main'
```

### Option 2: Manual Deployment

```bash
# Install Azure Static Web Apps CLI
npm install -g @azure/static-web-apps-cli

# Build Next.js app
cd apps/ui
npm run build

# Deploy to Azure
swa deploy \
  --app-name holidaypeakhub-ui-dev \
  --resource-group holidaypeakhub-dev-rg \
  --app-location ./apps/ui \
  --output-location out
```

## GitHub Actions Integration

The Bicep deployment automatically creates a GitHub Actions workflow. The deployment token is output by the module.

### Store Deployment Token in GitHub Secrets

```bash
# Get deployment token
DEPLOYMENT_TOKEN=$(az deployment sub show \
  --name static-web-app-deployment \
  --query properties.outputs.deploymentToken.value -o tsv)

# Store in GitHub secrets (requires GitHub CLI)
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body "$DEPLOYMENT_TOKEN"
```

### GitHub Actions Workflow (auto-generated)

Azure Static Web Apps automatically creates `.github/workflows/azure-static-web-apps-<name>.yml`:

```yaml
name: Azure Static Web Apps CI/CD

on:
  push:
    branches:
      - main
    paths:
      - 'apps/ui/**'
  pull_request:
    types: [opened, synchronize, reopened, closed]
    branches:
      - main

jobs:
  build_and_deploy_job:
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.action != 'closed')
    runs-on: ubuntu-latest
    name: Build and Deploy Job
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: true

      - name: Build And Deploy
        id: builddeploy
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/apps/ui"
          output_location: "out"
```

## Environment Configuration

### Environment Variables (Build Time)

Set in Bicep module:
- `NEXT_PUBLIC_API_BASE_URL` - Backend API URL
- `NEXT_PUBLIC_ENVIRONMENT` - Environment name (dev/staging/prod)

### Update API URLs

**Dev**:
```bash
NEXT_PUBLIC_API_BASE_URL=https://holidaypeakhub-dev-apim.azure-api.net
```

**Production**:
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.holidaypeakhub.com
```

## Custom Domain (Production)

### Prerequisites
1. Domain registered (e.g., GoDaddy, Namecheap)
2. DNS access to create CNAME records

### Steps

1. **Add Custom Domain in Bicep** (already configured for prod)
   ```bicep
   resource customDomain 'Microsoft.Web/staticSites/customDomains@2023-01-01' = if (environment == 'prod') {
     parent: staticWebApp
     name: 'www.holidaypeakhub.com'
     properties: {}
   }
   ```

2. **Get Validation Token**
   ```bash
   az staticwebapp hostname show \
     --name holidaypeakhub-ui-prod \
     --resource-group holidaypeakhub-prod-rg
   ```

3. **Add DNS Records**
   | Type  | Name | Value                                      |
   |-------|------|--------------------------------------------|
   | CNAME | www  | <static-web-app-default-hostname>          |
   | TXT   | www  | <validation-token>                         |

4. **Verify Domain**
   ```bash
   az staticwebapp hostname show \
     --name holidaypeakhub-ui-prod \
     --resource-group holidaypeakhub-prod-rg
   ```

5. **SSL Certificate** - Automatically provisioned by Azure (may take 15-30 minutes)

## Routing Configuration

Static Web Apps supports client-side routing. Create `staticwebapp.config.json` in `/apps/ui/public/`:

```json
{
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["anonymous"]
    },
    {
      "route": "/dashboard/*",
      "allowedRoles": ["authenticated"]
    },
    {
      "route": "/staff/*",
      "allowedRoles": ["staff"]
    },
    {
      "route": "/admin/*",
      "allowedRoles": ["admin"]
    }
  ],
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/images/*.{png,jpg,gif}", "/css/*"]
  },
  "globalHeaders": {
    "content-security-policy": "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:; font-src 'self' data: https:; connect-src 'self' https:",
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin"
  }
}
```

## Performance Optimization

### 1. Enable Compression
- Brotli/Gzip automatically enabled by Azure CDN

### 2. Optimize Images
Use Next.js Image component (with `unoptimized: true` for static export):
```tsx
import Image from 'next/image'

<Image 
  src="/images/product.jpg" 
  alt="Product" 
  width={500} 
  height={500} 
  unoptimized 
/>
```

### 3. Code Splitting
Next.js automatically code-splits pages. Use dynamic imports for heavy components:
```tsx
import dynamic from 'next/dynamic'

const HeavyComponent = dynamic(() => import('../components/HeavyComponent'), {
  loading: () => <p>Loading...</p>,
})
```

### 4. Cache Headers
Configured in `staticwebapp.config.json`:
```json
{
  "routes": [
    {
      "route": "/images/*",
      "headers": {
        "cache-control": "public, max-age=31536000, immutable"
      }
    },
    {
      "route": "/*.js",
      "headers": {
        "cache-control": "public, max-age=31536000, immutable"
      }
    }
  ]
}
```

## Monitoring

### View Deployment Logs
```bash
az staticwebapp show \
  --name holidaypeakhub-ui-dev \
  --resource-group holidaypeakhub-dev-rg
```

### View Application Insights
Static Web Apps automatically integrates with Application Insights if configured in the shared infrastructure module.

## Cost

### Free Tier (Dev/Staging)
- **Bandwidth**: 100 GB/month
- **Custom domains**: 2
- **SSL certificates**: Included
- **Build minutes**: 500 minutes/month
- **Cost**: $0/month

### Standard Tier (Production)
- **Bandwidth**: Unlimited
- **Custom domains**: Unlimited
- **Enterprise CDN**: Included
- **Staging environments**: 3
- **Build minutes**: Unlimited
- **Cost**: ~$9/month + $0.20 per GB bandwidth

## Troubleshooting

### Build Failures
1. Check GitHub Actions logs
2. Verify `next.config.js` has `output: 'export'`
3. Ensure no server-side features (getServerSideProps, API routes)

### 404 Errors
1. Verify `staticwebapp.config.json` has `navigationFallback`
2. Check `trailingSlash: true` in `next.config.js`

### API Connection Issues
1. Verify `NEXT_PUBLIC_API_BASE_URL` is set correctly
2. Check CORS configuration in APIM
3. Verify APIM is accessible from client browser

## Next Steps

1. **Configure Authentication** - See Azure Static Web Apps authentication docs
2. **Add Staging Environments** - Enable in Standard tier for PR previews
3. **Monitor Performance** - Use Application Insights and Azure Monitor
