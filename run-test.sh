set -e

echo "ruff format"
ruff format --check --diff fabriquinha tests
echo ""

echo "ruff check"
ruff check fabriquinha tests
echo ""

echo "mypy"
mypy --strict fabriquinha
echo ""

pytest --integration ${1:-} ${2:-} ${3:-} ${4:-}

echo ""
echo "Finished all checks."
echo "OK"
