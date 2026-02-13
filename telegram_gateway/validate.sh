#!/bin/bash

# Validation script for Telegram Gateway Service

echo "🔍 Telegram Gateway Service - Validation Check"
echo "==============================================="
echo ""

ERRORS=0

# Check Python version
echo "✓ Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "  ❌ Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check required files exist
echo "✓ Checking required files..."
REQUIRED_FILES=(
    "app/__init__.py"
    "app/main.py"
    "app/config.py"
    "app/session_manager.py"
    "app/rate_limiter.py"
    "app/router.py"
    "app/api_client.py"
    "app/formatter.py"
    "tests/test_router.py"
    "tests/test_formatter.py"
    "requirements.txt"
    ".env.example"
    "README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ❌ Missing: $file"
        ERRORS=$((ERRORS + 1))
    fi
done
echo "  ✅ All required files present"
echo ""

# Check if .env exists
echo "✓ Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "  ⚠️  No .env file found (expected for first run)"
    echo "     Run: cp .env.example .env"
else
    echo "  ✅ .env file exists"
fi
echo ""

# Check Python syntax
echo "✓ Checking Python syntax..."
python3 -m py_compile app/*.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ All Python files compile successfully"
else
    echo "  ❌ Syntax errors found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Count lines of code
echo "✓ Code Statistics:"
echo "  App code:"
find app -name "*.py" -type f -exec wc -l {} + | tail -1 | awk '{print "    " $1 " lines"}'
echo "  Test code:"
find tests -name "*.py" -type f -exec wc -l {} + | tail -1 | awk '{print "    " $1 " lines"}'
echo "  Total Python files:"
find . -name "*.py" -type f | wc -l | awk '{print "    " $1 " files"}'
echo ""

# Summary
echo "==============================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ Validation PASSED - All checks successful!"
    echo ""
    echo "Next steps:"
    echo "  1. Copy .env.example to .env and configure"
    echo "  2. Install dependencies: pip install -r requirements.txt"
    echo "  3. Start Redis: docker run -d -p 6379:6379 redis:7-alpine"
    echo "  4. Run tests: pytest"
    echo "  5. Start service: ./start.sh"
else
    echo "❌ Validation FAILED - $ERRORS error(s) found"
    exit 1
fi
