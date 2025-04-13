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
        alembic_args = [
            '--config',
            'fabriquinha/migracoes/alembic.ini',
            '--raiseerr',
            'upgrade',
            'head',
        ]
        alembic.config.main(argv=alembic_args)
        yield sess
        alembic_args = [
            '--config',
            'fabriquinha/migracoes/alembic.ini',
            '--raiseerr',
            'downgrade',
            '0',
        ]
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
def comunidades(sessao):
    cs = [
        fabr.bd.Comunidade(nome='GruPy-SP'),
        fabr.bd.Comunidade(nome='PyLadies'),
    ]
    sessao.add_all(cs)
    sessao.commit()
    return cs


@pytest.fixture
def modelo(comunidades, html, sessao):
    m = fabr.bd.Modelo.novo(
        sessao=sessao,
        nome='d',
        html=html,
        comunidade='GruPy-SP',
    )
    sessao.add(m)
    sessao.commit()
    return m


@pytest.fixture
def usuarias(sessao, gerar_str):
    us = [
        fabr.bd.Usuaria.novo(
            nome=gerar_str(20),
            senha='senha',
            teste=True,
        )
        for _ in range(20)
    ]
    sessao.add_all(us)
    sessao.commit()
    return us


@pytest.fixture
def acessos(sessao, usuarias, comunidades):
    tabela = [
        (usuarias[0].id, comunidades[0].id, 'administradora'),
        (usuarias[0].id, comunidades[1].id, 'administradora'),
        (usuarias[1].id, comunidades[0].id, 'organizadora'),
        (usuarias[1].id, comunidades[1].id, 'organizadora'),
        (usuarias[2].id, comunidades[0].id, 'administradora'),
        (usuarias[3].id, comunidades[0].id, 'administradora'),
        (usuarias[4].id, comunidades[0].id, 'organizadora'),
        (usuarias[5].id, comunidades[0].id, 'organizadora'),
    ]
    a = [
        fabr.bd.Acesso(usuaria_id=li[0], comunidade_id=li[1], tipo=li[2])
        for li in tabela
    ]
    sessao.add_all(a)
    sessao.commit()
    return a


@pytest.fixture
def usuaria(usuarias):
    return usuarias[0]


@pytest.fixture
def admin(cliente, usuaria):
    verificar_login = fabr.rotas.verificar_login
    cliente.app.dependency_overrides[verificar_login] = lambda: usuaria
    return usuaria


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
