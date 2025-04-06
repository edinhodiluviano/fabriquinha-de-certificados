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


def test_get_download_com_codigo_valido(certificados, cliente):
    resp = cliente.get('download/' + certificados[0].codigo + '.pdf')
    assert resp.status_code == 200
    assert any('pdf' in val for val in resp.headers.values())
    conteudo = b''.join(resp.iter_bytes())
    assert isinstance(conteudo, bytes)
    assert len(conteudo) > 1024


def test_get_download_com_codigo_inexistente(certificados, cliente):
    resp = cliente.get('download/' + certificados[0].codigo + 'a.pdf')
    assert resp.status_code == 200
    assert 'não encontrado' in resp.text
    assert len(resp.history) == 1
    assert resp.history[0].status_code == 302


def test_get_raiz(cliente):
    resp = cliente.get('/')
    assert resp.status_code == 200
    assert 'Validador de Certificados' in resp.text


def test_post_html2png(cliente, html):
    resp = cliente.post('/html2png', json={'html': html})
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith('data:image/png;base64,')
    assert len(resp.text) > 100


def test_get_novo_modelo(cliente):
    resp = cliente.get('/novo-modelo')
    assert resp.status_code == 200
    assert 'Visualizar Rascunho'.lower() in resp.text.lower()
    assert 'img' in resp.text
