# GitHub Actions CI/CD Pipeline

This directory contains the GitHub Actions workflows that automate testing, building, and security checks for the Suman Narla project.

## Workflows Overview

### 1. CI - Tests and Linting (`ci.yml`)

**Triggered on:**
- Push to `main` or `claude/*` branches
- Pull requests to `main`

**Jobs:**
- **Backend Lint**: Runs `ruff` to check code style and formatting
- **Backend Type Check**: Runs `mypy` for type safety (non-blocking)
- **Backend Test**: Runs pytest with coverage reporting
  - Sets up PostgreSQL service for database tests
  - Reports coverage to Codecov
- **Frontend Build**: Builds the React frontend and uploads artifacts
- **Frontend Lint**: Lints frontend code with ESLint
- **All Checks Passed**: Final gate that fails if critical checks fail

**Requirements:**
- Python 3.11
- Node.js 18
- Dependencies from `requirements.txt` and `requirements-dev.txt`

### 2. Docker Build and Push (`docker-build.yml`)

**Triggered on:**
- Push to `main` branch
- Tags matching `v*` (semantic versioning)
- Manual trigger via `workflow_dispatch`

**Jobs:**
- Builds Docker images for backend (and frontend if Dockerfile exists)
- Pushes to:
  - Docker Hub (requires `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets)
  - GitHub Container Registry (uses `GITHUB_TOKEN`)
- Creates Release on version tags
- Caches layers for faster builds

**Environment Variables Required:**
- `DOCKER_USERNAME` (GitHub Secrets)
- `DOCKER_PASSWORD` (GitHub Secrets)

**Tags Generated:**
- `latest` (from main branch)
- Semantic versions (from tags like `v1.0.0`)
- Short SHA (unique per commit)
- Branch names (for development builds)

### 3. Security Checks (`security.yml`)

**Triggered on:**
- Push to `main` or `claude/*` branches
- Pull requests to `main`
- Daily at 2 AM UTC (scheduled)

**Jobs:**
- **Python Dependency Check**: Runs `pip-audit` to detect vulnerable packages
- **Trivy Scan**: Scans filesystem for vulnerabilities and uploads to GitHub Security tab
- **CodeQL Analysis**: GitHub's native code scanning for Python
- **Bandit Scan**: Scans Python code for security issues (OWASP)
- **NPM Audit**: Checks frontend dependencies for vulnerabilities

## Setup Instructions

### 1. Configure GitHub Secrets

For Docker push functionality, add these secrets to your repository:

1. Go to Settings → Secrets and variables → Actions
2. Add:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: Your Docker Hub password or personal access token

### 2. Enable Required Features

1. **Codecov Integration** (Optional but recommended):
   - Connect Codecov to your GitHub account
   - Coverage reports will auto-upload with the workflow

2. **GitHub Security Tab**:
   - Ensure "Security" tab is enabled in repository settings
   - Trivy and CodeQL results will appear there

3. **Branch Protection Rules** (Recommended):
   - Go to Settings → Branches → Protect Matching Branches
   - Create rule for `main`
   - Require status checks to pass:
     - `backend-lint`
     - `backend-test`
     - `frontend-build`

### 3. Database Configuration for Tests

The `backend-test` job uses PostgreSQL service container. Ensure:
- Your tests support `DATABASE_URL` environment variable
- Update the connection string if needed in `ci.yml`

## Configuration Files

### Python Dependencies
- `requirements.txt`: Production dependencies
- `requirements-dev.txt`: Development/CI dependencies (testing, linting, type checking)

### Makefile Targets
The workflows align with these Makefile targets:
```bash
make lint      # ruff check
make test      # pytest
make typecheck # mypy
make check     # all checks
```

## Monitoring and Troubleshooting

### View Workflow Runs
1. Go to Actions tab in GitHub
2. Select the workflow name
3. Click on a run to see detailed logs

### Common Issues

**Docker Push Fails:**
- Check `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are set
- Verify Docker Hub credentials are correct

**Tests Fail:**
- Check Python version compatibility (3.11)
- Ensure all dependencies in `requirements-dev.txt` are up to date
- Review test logs for database connection issues

**Coverage Not Uploading:**
- Codecov integration is optional; failures are non-blocking
- Check that `pytest-cov` is installed

**Security Scan Alerts:**
- Review detailed reports in GitHub Security tab
- Address high-severity vulnerabilities in pull requests
- Use `continue-on-error` flag to allow builds to pass while investigating

## Performance Tips

1. **Use Actions cache**: Workflows cache pip and npm dependencies
2. **Parallel jobs**: Most jobs run in parallel for faster feedback
3. **Selective builds**: Docker build only pushes on `main` and tags
4. **Skip workflows**: Add `[skip ci]` to commit message to skip CI (not recommended)

## Customization

### Add New Checks
Edit the respective workflow file and add new steps. Example:

```yaml
- name: New Check
  run: some-command
  continue-on-error: true  # Make non-blocking
```

### Change Python/Node Version
Update the version in `setup-python` or `setup-node` steps:

```yaml
python-version: '3.12'  # Change this
node-version: '20'      # Or this
```

### Modify Trigger Events
Edit the `on:` section in workflow files:

```yaml
on:
  push:
    branches: [ main, develop ]  # Add/remove branches
  schedule:
    - cron: '0 * * * *'  # Change schedule
```

## Next Steps

1. Add required GitHub Secrets for Docker
2. Test a pull request to verify CI passes
3. Set up branch protection rules for `main`
4. Monitor workflows in the Actions tab
