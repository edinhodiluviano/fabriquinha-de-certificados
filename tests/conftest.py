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
def modelo(sessao):
    htmlzip = 'eJyNVNFu0zAUfd9X3AWhgUSaVlsZpGkFAsQjleCFJ3QTu443J/Zsp1uJ8jF8Cz+GHac0rFRa+9Dre22fc889LmTnH798+PZ9/QlKW4nV2Vk2/AJkJUWycoELjd0J2mf9551CRqEdVgCG/6QpvJ+DwJqYAhVd/K1VqBmvYytVCrPJvKiOSoJu7Kma5qw8WcyltbJKYTqudnuSuSS7Eccci1umZVOTmFeOfgqNFi8ueMV+MK7F5Eaxi5cHiOw8jt0VmlAd982nYKTgZAFxvDpcGjYUUkidwrOr6zfX+dsjJhMhmRxRIdwogbsUciGL2xN6YGPlKTn+rd1zYssULufPj4AtfbBjZL+OUXBWp1DQ2lJ9uGbfxOXUfw/5jaxtvMGKC8d4SzXBGo9bvNOFJGNPbIRER7VnvBgJFkY2O6TclZYXKPa8wpZjBC2JM9aTEaZPRRg6DB6eTdXDI+gsGczvw/AkfOjtNTyIzJkIjC6WUWmtMmmSaLyfMG7LJm8Mdco4pWs7KWSVMN2oXWxU4j2RVGjcDPo47isTVbMICoHGLCOfjvYYap/tZxqtPutmvYu/rt0cXXcb1x/cNTRL1PBiy9mjA21ruW0E6q5zfcxW/7926H2NXjKuZANEAt06+s5HbQi6zpmlgsJ5EqGU+vcvzRH89FvSaCzQ76il8zn6MxU3xqcGNR3BkWwDerBPFFQkaDHtH2lyoyhb5Gjo66tXbRt2dd1AM8P98eCNCEpNN8uobbdu0iQQ8Y2PllmCAT9LwgSdFv0f3h/Qq3HO'
    m = fabr.bd.Modelo(
        nome='d',
        resumo='e',
        htmlzip=htmlzip,
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
