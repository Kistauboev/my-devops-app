# Environment Variables Template

Copy the relevant sections to your `.env` file or set as environment variables.

## Backend Environment Variables

### Required for Full Functionality

```bash
# GitHub App Configuration (Required for onboarding)
GITHUB_APP_ID=your_github_app_id
GITHUB_INSTALLATION_ID=your_installation_id
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nYour private key here\n-----END RSA PRIVATE KEY-----"

# Approval Token (Required for production approvals)
APPROVAL_TOKEN=your_secret_approval_token_here
```

### Optional but Recommended

```bash
# Kubernetes Configuration (Required for logs/metrics/deployments)
KUBE_CONFIG=your_base64_encoded_kubeconfig_or_file_path
```

### Optional - Secrets Manager

```bash
# HashiCorp Vault
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=your_vault_token

# GitHub Secrets API (fallback)
GITHUB_TOKEN=your_github_personal_access_token
```

### Optional - Default Secrets for Onboarding

```bash
# These will be provisioned to onboarded repositories
DEFAULT_REGISTRY_USERNAME=your_registry_username
DEFAULT_REGISTRY_PASSWORD=your_registry_password
DEFAULT_KUBE_CONFIG=your_default_kubeconfig
```

## Frontend Environment Variables

```bash
# Backend API URL (defaults to http://localhost:8000)
VITE_API_BASE=http://localhost:8000
```

## Docker Compose

When using `docker-compose.yml`, all backend environment variables are automatically passed through. Create a `.env` file in the project root with the variables above.

## Kubernetes

For Kubernetes deployments, create secrets:

```bash
kubectl create secret generic devplatform-secrets \
  --from-literal=GITHUB_APP_ID=your_app_id \
  --from-literal=GITHUB_INSTALLATION_ID=your_installation_id \
  --from-literal=GITHUB_PRIVATE_KEY="$(cat your-private-key.pem)" \
  --from-literal=APPROVAL_TOKEN=your_token \
  --from-literal=KUBE_CONFIG="$(cat ~/.kube/config | base64)" \
  -n devplatform
```

## Getting GitHub App Credentials

1. Go to GitHub Organization Settings
2. Developer settings > GitHub Apps
3. Create new app or use existing
4. Generate private key
5. Install app to organization/repositories
6. Note the Installation ID from the installation URL

See `DEPLOYMENT_GUIDE.md` for detailed GitHub App setup instructions.

