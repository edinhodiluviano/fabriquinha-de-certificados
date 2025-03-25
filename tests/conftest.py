import datetime as dt
import random

import alembic.config
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

import fabriquinha as fabr


@pytest.fixture
def config():
    c = fabr.ambiente.criar_config()
    return c


def pytest_addoption(parser):
    parser.addoption(
        '--integration',
        action='store_true',
        default=False,
        help='Also run tests with the "integration" mark',
    )
    parser.addoption(
        '--migration',
        action='store_true',
        default=False,
        help='Also run tests with the "migration" mark',
    )


def pytest_runtest_setup(item):
    # skip integration tests unless --integration option is given
    integration_marker = bool(list(item.iter_markers(name='integration')))
    integration_opt = bool(item.config.getoption('--integration'))
    if integration_marker and not integration_opt:
        pytest.skip('requires "--integration" option')

    # skip migration tests unless --migration option is given
    migration_marker = bool(list(item.iter_markers(name='migration')))
    migration_opt = bool(item.config.getoption('--migration'))
    if migration_marker and not migration_opt:
        pytest.skip('requires "--migration" option')


def limpar_banco(sessao):
    """Deleta todoas as linhas de todas as tabelas. Mas mantem as tabelas."""
    executar = lambda s: sessao.execute(sa.text(s))
    for tabela in fabr.bd.Base.metadata.tables.values():
        executar(f'ALTER TABLE "{tabela.name}" DISABLE TRIGGER ALL;')
        sessao.execute(tabela.delete())
        executar(f'ALTER TABLE "{tabela.name}" ENABLE TRIGGER ALL;')
        sessao.commit()


@pytest.fixture(
    scope='module',
    params=[pytest.param(None, marks=pytest.mark.integration)],
)
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


@pytest.fixture
def cliente(config):
    app = fabr.main.criar_app(config)
    teste_cli = TestClient(app)
    return teste_cli


@pytest.fixture
def html():
    with open('tests/test.html') as f:
        c = f.read()
    return c


@pytest.fixture
def modelo(html, sessao):
    m = fabr.bd.Modelo.novo(
        nome='d',
        html=html,
        emissora='GruPy-SP',
    )
    sessao.add(m)
    sessao.commit()
    return m


@pytest.fixture
def gerar_str():
    s = 'abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789'
    return lambda n: ''.join(random.choices(s, k=n))


@pytest.fixture
def certificados(sessao, modelo, gerar_str):
    c = [
        fabr.bd.Certificado(
            codigo=gerar_str(12),
            modelo=modelo,
            data=dt.date(2020, 1, 1),
            conteudo=dict(teste=gerar_str(20)),
        )
        for _ in range(10)
    ]
    sessao.add_all(c)
    sessao.commit()
    return c
