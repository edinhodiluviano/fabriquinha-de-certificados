set -e

ruff check fabriquinha tests
black --check --diff fabriquinha tests
mypy --strict fabriquinha
pytest

echo ""
echo "Finished all checks."
echo "OK"
