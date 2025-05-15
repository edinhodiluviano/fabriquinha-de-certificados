"""
Adiciona tabela Comunidade.

Revisão: 5957dcc61a1e
Anterior: 45cf2fcb4fe9
Data de Criação: 2025-04-13 22:08:43.958888
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5957dcc61a1e'
down_revision: str | None = '45cf2fcb4fe9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # cria tabela 'Comunidade'
    op.create_table(
        'comunidade',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_comunidade')),
    )
    op.create_index(
        op.f('ix_comunidade_nome'), 'comunidade', ['nome'], unique=True
    )
    # Adiciona dados na tabela
    op.execute(
        """
            INSERT INTO comunidade (nome)
            SELECT DISTINCT emissora FROM modelo
        """
    )

    op.create_table(
        'acesso',
        sa.Column('usuaria_id', sa.Integer(), nullable=False),
        sa.Column('comunidade_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ['comunidade_id'],
            ['comunidade.id'],
            name=op.f('fk_acesso_comunidade_id_comunidade'),
        ),
        sa.ForeignKeyConstraint(
            ['usuaria_id'],
            ['usuaria.id'],
            name=op.f('fk_acesso_usuaria_id_usuaria'),
        ),
        sa.PrimaryKeyConstraint(
            'usuaria_id', 'comunidade_id', name=op.f('pk_acesso')
        ),
    )
    op.create_index(op.f('ix_acesso_tipo'), 'acesso', ['tipo'], unique=False)

    # tabela 'modelo'
    # cria coluna 'comunidade_id' (sem restrições)
    op.add_column('modelo', sa.Column('comunidade_id', sa.Integer()))
    # adiciona dados na coluna
    op.execute(
        """
            UPDATE modelo
            SET comunidade_id = (
                SELECT id
                FROM comunidade
                WHERE modelo.emissora = comunidade.nome
            )
        """
    )
    # adiciona restrições
    op.alter_column('modelo', 'comunidade_id', nullable=False)

    op.drop_index('ix_modelo_emissora', table_name='modelo')
    op.create_index(
        op.f('ix_modelo_comunidade_id'),
        'modelo',
        ['comunidade_id'],
        unique=False,
    )
    op.create_foreign_key(
        op.f('fk_modelo_comunidade_id_comunidade'),
        'modelo',
        'comunidade',
        ['comunidade_id'],
        ['id'],
    )
    op.drop_column('modelo', 'emissora')
    op.add_column('usuaria', sa.Column('ativa', sa.Boolean(), nullable=False))
    op.add_column(
        'usuaria', sa.Column('sysadmin', sa.Boolean(), nullable=False)
    )
    op.create_index(
        op.f('ix_usuaria_ativa'), 'usuaria', ['ativa'], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_usuaria_ativa'), table_name='usuaria')
    op.drop_column('usuaria', 'sysadmin')
    op.drop_column('usuaria', 'ativa')

    # preenche coluna "emissora" antes de tornala "não nula"
    op.add_column(
        'modelo',
        sa.Column(
            'emissora',
            sa.VARCHAR(length=8),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.execute("""
        update modelo set emissora = (
            select comunidade.nome
            from modelo
                left join comunidade
                    on modelo.comunidade_id = comunidade.id
        )
    """)
    op.alter_column(
        'modelo',
        'emissora',
        nullable=False,
    )

    op.drop_constraint(
        op.f('fk_modelo_comunidade_id_comunidade'),
        'modelo',
        type_='foreignkey',
    )
    op.drop_index(op.f('ix_modelo_comunidade_id'), table_name='modelo')
    op.create_index('ix_modelo_emissora', 'modelo', ['emissora'], unique=False)
    op.drop_column('modelo', 'comunidade_id')
    op.drop_index(op.f('ix_acesso_tipo'), table_name='acesso')
    op.drop_table('acesso')
    op.drop_index(op.f('ix_comunidade_nome'), table_name='comunidade')
    op.drop_table('comunidade')
