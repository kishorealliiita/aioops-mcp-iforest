# CI/CD Pipeline Documentation

This repository includes a comprehensive CI/CD pipeline using GitHub Actions that automates testing, building, and deployment of the AIOps system.

## 🚀 Pipeline Overview

The CI/CD pipeline consists of several workflows:

1. **Main CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)
2. **Security Scans** (`.github/workflows/security.yml`)
3. **Dependabot Integration** (`.github/dependabot.yml`)

## 📋 Pipeline Stages

### 1. Test and Quality Assurance
- **Triggers**: Push to main/develop, Pull Requests
- **Python Versions**: 3.9, 3.10, 3.11
- **Checks**:
  - Code linting (flake8, black, isort)
  - Security scanning (bandit, safety)
  - Unit tests with coverage
  - Test artifacts upload

### 2. Build and Push Docker Images
- **Triggers**: Push to main branch only
- **Actions**:
  - Builds main application Docker image
  - Builds log generator Docker image
  - Pushes to GitHub Container Registry
  - Applies semantic versioning tags


### 3. Release Management
- **Triggers**: GitHub release creation
- **Actions**:
  - Generates release notes from commits
  - Updates release with Docker image information

## 🔧 Local Development

### Running CI Checks Locally

Use the provided script to run the same checks locally:

```bash
# Make the script executable (first time only)
chmod +x scripts/ci-local.sh

# Run all CI checks
./scripts/ci-local.sh
```

### Manual Commands

If you prefer to run checks individually:

```bash
# Install development dependencies
pip install flake8 black isort bandit safety pytest pytest-cov

# Run linting
flake8 app/ tests/
black --check app/ tests/
isort --check-only app/ tests/

# Run security checks
bandit -r app/
safety check

# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=html
```

## 🔒 Security Features

### Automated Security Scans
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability checker
- **Trivy**: Container vulnerability scanner
- **Dependency Review**: GitHub's built-in dependency analysis

### Security Workflow
- Runs on schedule (weekly)
- Runs on all PRs and pushes
- Comments on PRs with security results
- Fails on moderate+ severity issues

## 📦 Docker Images

The pipeline builds and pushes two Docker images:

1. **Main Application**: `ghcr.io/{owner}/{repo}:{tag}`
2. **Log Generator**: `ghcr.io/{owner}/{repo}-log-generator:{tag}`

### Image Tags
- `latest`: Latest commit on main branch
- `v1.0.0`: Semantic version tags
- `main-{sha}`: Branch-specific tags
- `pr-{number}`: Pull request tags

## 🚀 Deployment

### Prerequisites
1. Kubernetes cluster access
2. Helm installed
3. `KUBE_CONFIG` secret configured in GitHub

### Deployment Process
1. Builds Docker images
2. Updates Helm values with new image tags
3. Deploys using `helm upgrade --install`
4. Verifies pod readiness

### Environment Configuration
- **Namespace**: `aiops`
- **Release Name**: `aiops-iforest`
- **Timeout**: 5 minutes

## 🔄 Dependabot Integration

### Automated Dependency Updates
- **Python**: Weekly updates
- **GitHub Actions**: Weekly updates
- **Docker**: Weekly updates

### Configuration
- Ignores major version updates for critical dependencies
- Automatically assigns reviewers
- Runs tests on dependency PRs
- Comments on successful test runs

## 📊 Monitoring and Reporting

### Test Coverage
- Generates coverage reports in multiple formats
- Uploads to Codecov for tracking
- Creates HTML reports for local viewing

### Artifacts
- Test results and coverage reports
- Security scan results
- Docker build logs

## 🛠️ Configuration Files

### Code Quality
- `.flake8`: Flake8 linting configuration
- `pyproject.toml`: Black, isort, bandit, and coverage configuration
- `pytest.ini`: Pytest configuration

### CI/CD
- `.github/workflows/ci-cd.yml`: Main pipeline
- `.github/workflows/security.yml`: Security workflow
- `.github/dependabot.yml`: Dependency updates

## 🔧 Customization

### Adding New Checks
1. Add the check to the appropriate workflow file
2. Update the local CI script if needed
3. Add any required configuration files

### Modifying Deployment
1. Update Helm values in the deploy job
2. Modify Kubernetes manifests as needed
3. Update environment variables

### Adding New Environments
1. Create new workflow files for staging/preview
2. Configure environment-specific secrets
3. Update deployment conditions

## 🚨 Troubleshooting

### Common Issues

#### Pipeline Failures
1. Check the Actions tab for detailed logs
2. Run local CI script to reproduce issues
3. Verify dependency versions are compatible

#### Deployment Failures
1. Check Kubernetes cluster access
2. Verify Helm chart syntax
3. Check resource limits and requests

#### Security Scan Failures
1. Review security scan reports
2. Update vulnerable dependencies
3. Fix code security issues

### Getting Help
1. Check the Actions tab for workflow logs
2. Review the local CI script output
3. Check GitHub's Actions documentation

## 📈 Best Practices

### Code Quality
- Run local CI checks before pushing
- Address linting issues promptly
- Maintain good test coverage

### Security
- Review security scan results regularly
- Keep dependencies updated
- Follow security best practices

### Deployment
- Test changes in staging first
- Use semantic versioning
- Monitor deployment health

## 🔗 Useful Links

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Codecov Documentation](https://docs.codecov.io/) 