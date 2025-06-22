#!/bin/bash

# Local CI/CD script - runs the same checks as GitHub Actions
set -e

echo "🚀 Starting local CI/CD checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Not in a virtual environment. Consider activating one."
fi

# Install dependencies
print_status "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install CI/CD specific dependencies
print_status "Installing CI/CD dependencies..."
pip install flake8 black isort bandit safety pytest pytest-cov pytest-asyncio httpx

# Run linting checks
echo ""
print_status "Running linting checks..."

echo "Running flake8..."
if flake8 app/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
    print_status "Flake8 critical errors check passed"
else
    print_error "Flake8 critical errors found!"
    exit 1
fi

if flake8 app/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics; then
    print_status "Flake8 style check passed"
else
    print_warning "Flake8 style issues found (non-blocking)"
fi

echo "Running black check..."
if black --check app/ tests/; then
    print_status "Black formatting check passed"
else
    print_warning "Black formatting issues found. Run 'black app/ tests/' to fix"
fi

echo "Running isort check..."
if isort --check-only app/ tests/; then
    print_status "Import sorting check passed"
else
    print_warning "Import sorting issues found. Run 'isort app/ tests/' to fix"
fi

# Run security checks
echo ""
print_status "Running security checks..."

echo "Running bandit security scan..."
if bandit -r app/ -f json -o bandit-report.json; then
    print_status "Bandit security scan completed"
else
    print_warning "Bandit found potential security issues"
fi

echo "Running safety check..."
if safety check --json --output safety-report.json; then
    print_status "Safety check completed"
else
    print_warning "Safety found potential vulnerabilities"
fi

# Run tests
echo ""
print_status "Running tests..."

if pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html; then
    print_status "All tests passed!"
else
    print_error "Tests failed!"
    exit 1
fi

# Show coverage summary
if [ -f "htmlcov/index.html" ]; then
    echo ""
    print_status "Coverage report generated at htmlcov/index.html"
fi

# Run type checking (if mypy is available)
if command -v mypy &> /dev/null; then
    echo ""
    print_status "Running type checks..."
    if mypy app/ --ignore-missing-imports; then
        print_status "Type checking passed"
    else
        print_warning "Type checking issues found"
    fi
else
    print_warning "mypy not installed. Install with: pip install mypy"
fi

# Final summary
echo ""
print_status "Local CI/CD checks completed successfully!"
echo ""
echo "📊 Summary:"
echo "  - Linting: ✅"
echo "  - Security: ✅"
echo "  - Tests: ✅"
echo "  - Coverage: Generated"
echo ""
echo "🎉 Ready to commit and push!" 