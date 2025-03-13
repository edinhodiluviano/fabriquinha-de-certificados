import pydantic
import pytest
import sqlalchemy as sa

import fabriquinha as fabr


def test_deve_sempre_passar():
    pass


def test_gerar_qrcode_retorna_str():
    qrcode = fabr.main.gerar_qrcode(s='laksmdc')
    assert isinstance(qrcode, str)


def test_criar_config_retorna_objeto_config():
    config = fabr.ambiente.criar_config()
    assert isinstance(config, fabr.ambiente.Config)


def test_criar_config_levanta_erro_com_log_level_errado():
    with pytest.raises(pydantic.ValidationError):
        fabr.ambiente.criar_config(log_level='aaa')


def test_criar_config_levanta_erro_com_ambiente_errado():
    with pytest.raises(pydantic.ValidationError):
        fabr.ambiente.criar_config(env='aaa')


def test_criar_sessao_do_banco_retorna_objeto_de_sessao():
    with fabr.bd.criar_sessao() as sess:
        assert isinstance(sess, fabr.bd.Session)


def test_fixture_sessao_permite_iteragir_com_o_banco_de_dados(sessao):
    r = sessao.execute(sa.text('SELECT 1, 2')).fetchall()
    assert r == [(1, 2)]


def test_tabelas_sao_deletadas_entre_tests_parte_1(sessao):
    exp = sa.select(fabr.bd.Modelo)
    assert len(sessao.scalars(exp).all()) == 0
    modelo = fabr.bd.Modelo(
        nome='a', resumo='b', htmlzip='c', emissora='GruPy-SP'
    )
    sessao.add(modelo)
    sessao.commit()
    assert len(sessao.scalars(exp).all()) == 1


def test_tabelas_sao_deletadas_entre_tests_parte_2(sessao):
    exp = sa.select(fabr.bd.Modelo)
    assert len(sessao.scalars(exp).all()) == 0
    modelo = fabr.bd.Modelo(
        nome='d', resumo='e', htmlzip='f', emissora='GruPy-SP'
    )
    sessao.add(modelo)
    sessao.commit()
    assert len(sessao.scalars(exp).all()) == 1
