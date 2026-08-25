# GitHub Actions Setup Guide

This guide helps you configure GitHub Actions for continuous integration and deployment.

## Prerequisites

- Repository is on GitHub
- You have admin/settings access to the repository
- (Optional) Docker Hub account for image registry

## Step 1: Enable GitHub Actions

1. Go to your repository settings
2. Navigate to **Actions** → **General**
3. Ensure "Actions permissions" is set to allow actions
4. Workflow permissions should be set to "Read and write permissions"

## Step 2: Configure Secrets (For Docker Publishing)

### Optional: Docker Hub Publishing

If you want to automatically push Docker images to Docker Hub:

1. Go to Settings → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets:

#### `DOCKER_USERNAME`
- Your Docker Hub username
- Example: `narlasuman`

#### `DOCKER_PASSWORD`
- Docker Hub personal access token (NOT your password)
- Create at: https://hub.docker.com/settings/security
- Scopes needed: Read, Write

### Getting Docker Hub Token

1. Log in to Docker Hub: https://hub.docker.com/
2. Go to Account Settings → Security
3. Create New Access Token
4. Copy the token immediately (you can't see it again)
5. Paste it as `DOCKER_PASSWORD` secret in GitHub

## Step 3: Enable Branch Protection Rules (Recommended)

1. Go to Settings → **Branches**
2. Click **Add rule** under "Branch protection rules"
3. Set branch name pattern to `main`
4. Enable:
   - ✓ Require a pull request before merging
   - ✓ Require status checks to pass before merging
     - Select these checks:
       - `backend-lint`
       - `backend-test`
       - `frontend-build`
   - ✓ Require code reviews before merging (at least 1)
   - ✓ Require status checks to pass before merging
   - ✓ Include administrators in restrictions (optional)

## Step 4: Configure GitHub Security Tab

1. Go to Settings → **Code security and analysis**
2. Enable:
   - ✓ Dependency graph
   - ✓ Dependabot alerts
   - ✓ Dependabot security updates
   - ✓ Secret scanning

This allows security scan results to appear in the Security tab.

## Step 5: Test the Setup

1. Create a test branch
2. Make a small change (e.g., update README)
3. Push and create a pull request
4. Go to the **Actions** tab to watch workflows run
5. Verify all checks pass

## Workflow Files Included

### `.github/workflows/ci.yml`
- **Runs on**: Push to main/claude/* and PRs
- **Tests**: Python linting, type checking, unit tests
- **Tests**: Frontend build and lint
- **Reports**: Coverage to Codecov

### `.github/workflows/docker-build.yml`
- **Runs on**: Push to main, version tags, manual trigger
- **Builds**: Docker images for backend and frontend
- **Pushes to**: Docker Hub + GitHub Container Registry
- **Requires**: DOCKER_USERNAME and DOCKER_PASSWORD secrets

### `.github/workflows/security.yml`
- **Runs on**: Push, PRs, daily schedule
- **Scans**: Python deps, filesystem, Python code, Node deps
- **Reports to**: GitHub Security tab (Trivy, CodeQL)

### `.github/dependabot.yml`
- **Auto-updates**: Python, Node, GitHub Actions dependencies
- **Schedule**: Weekly on Monday
- **Creates**: Pull requests with dependency updates

## First Run Checklist

- [ ] Cloned repo to local machine
- [ ] Reviewed the workflow files in `.github/workflows/`
- [ ] Added Docker secrets (if using Docker Hub)
- [ ] Created a test branch and verified CI passes
- [ ] Enabled branch protection on `main`
- [ ] Enabled security features in Settings → Code security
- [ ] Viewed Actions tab to see workflow runs

## Common Configuration

### Change Python Version
Edit `.github/workflows/ci.yml`:
```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.12'  # Update this
```

### Change Node Version
Edit `.github/workflows/ci.yml`:
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'  # Update this
```

### Skip Workflows on Certain Commits
Add to commit message: `[skip ci]`

### Disable a Workflow
Rename workflow file or remove `.yml` extension

### Run Workflow Manually
In GitHub, go to Actions → select workflow → "Run workflow"

## Monitoring and Troubleshooting

### View Workflow Status
1. Go to **Actions** tab
2. Select workflow from left sidebar
3. Click on a run to see details
4. Click on a failed job to see logs

### Common Issues

**"workflow does not exist"**
- Ensure files are in `.github/workflows/` directory
- Workflow files must be `.yml` or `.yaml`

**"Docker push fails"**
- Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets exist
- Test Docker credentials locally: `docker login`

**"PostgreSQL connection error in tests"**
- Service container may take time to start
- Check if `postgres` service is healthy before tests

**"Coverage upload fails"**
- This is non-blocking; build still succeeds
- Codecov integration is optional

**"Bandit report empty"**
- This is expected if no security issues found
- High-severity findings should still be reviewed

## Security Best Practices

1. **Never commit secrets**
   - Use GitHub Secrets for passwords/tokens
   - Add sensitive files to `.gitignore`

2. **Review security alerts**
   - Check GitHub Security tab regularly
   - Address high-severity vulnerabilities promptly

3. **Keep dependencies updated**
   - Dependabot automatically creates PRs
   - Review and merge promptly

4. **Use branch protection**
   - Require CI to pass before merging
   - Require code review for main branch

5. **Monitor workflow logs**
   - Review failed jobs for security warnings
   - Fix linting/type errors before merging

## Useful Links

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Actions Marketplace](https://github.com/marketplace/actions)
- [Docker Hub Personal Access Tokens](https://hub.docker.com/settings/security)
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Security Tab](https://docs.github.com/en/code-security)

## Support

For issues with the CI/CD pipeline:
1. Check workflow logs in the Actions tab
2. Review the README in `.github/workflows/README.md`
3. Check GitHub Actions documentation
4. Create an issue with error logs

---

**Last Updated**: 2026-08-25
