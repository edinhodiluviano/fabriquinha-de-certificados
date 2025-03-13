import alembic.config
import pytest
import sqlalchemy as sa

import fabriquinha as fabr


@pytest.fixture
def config():
    c = fabr.ambiente.criar_config()
    return c


def limpar_banco(sessao):
    """Deleta todoas as linhas de todas as tabelas. Mas mantem as tabelas."""
    executar = lambda s: sessao.execute(sa.text(s))
    for tabela in fabr.bd.Base.metadata.tables.values():
        executar(f'ALTER TABLE "{tabela.name}" DISABLE TRIGGER ALL;')
        sessao.execute(tabela.delete())
        executar(f'ALTER TABLE "{tabela.name}" ENABLE TRIGGER ALL;')
        sessao.commit()


@pytest.fixture(scope='module')
def _sessao():
    with fabr.bd.criar_sessao() as sess:
        alembic_args = ['--raiseerr', 'upgrade', 'head']
        alembic.config.main(argv=alembic_args)
        yield sess
        alembic_args = ['--raiseerr', 'downgrade', '0']
        alembic.config.main(argv=alembic_args)


@pytest.fixture
def sessao(_sessao):
    limpar_banco(_sessao)
    yield _sessao
    limpar_banco(_sessao)
