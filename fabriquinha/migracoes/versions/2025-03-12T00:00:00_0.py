"""
Migração Inicial.

Revisão: 0
Anterior:
Data de Criação: 2025-03-12 00:00:00.000000
"""

from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = '0'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
