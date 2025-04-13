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


def test_get_raiz(cliente):
    resp = cliente.get('/')
    assert resp.status_code == 200
    assert 'Validador de Certificados' in resp.text


def test_post_html2png(cliente, html):
    resp = cliente.post('/html2png', json={'html': html})
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith('data:image/png;base64,')
    assert len(resp.text) > 100


def test_get_favicon(cliente):
    resp = cliente.get('/favicon.ico')
    assert resp.status_code == 200
