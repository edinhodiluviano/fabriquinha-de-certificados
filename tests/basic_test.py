import pydantic
import pytest

import fabriquinha as fabr


def test_deve_sempre_passar():
    pass


def test_criar_config_retorna_objeto_config():
    config = fabr.ambiente.criar_config()
    assert isinstance(config, fabr.ambiente.Config)


def test_criar_config_levanta_erro_com_log_level_errado():
    with pytest.raises(pydantic.ValidationError):
        fabr.ambiente.criar_config(log_level='aaa')


def test_get_ping_retorna_200(cliente):
    resp = cliente.get('ping')
    assert resp.status_code == 200


def test_get_validar_com_codigo_inexistente(certificados, cliente):
    resp = cliente.get('v/aaaaaaaaaaa')
    assert resp.status_code == 200
    assert 'não encontrado' in resp.text


def test_get_validar_com_codigo_valido(certificados, cliente):
    resp = cliente.get('v/' + certificados[0].codigo)
    assert resp.status_code == 200
    assert certificados[0].modelo.emissora in resp.text
    assert 'Certificado OK!' in resp.text
