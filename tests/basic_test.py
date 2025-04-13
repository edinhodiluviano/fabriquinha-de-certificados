from unittest.mock import patch

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


def test_get_novo_modelo_nao_logado_redireciona_para_login(cliente):
    resp = cliente.get('/novo-modelo', follow_redirects=False)
    assert resp.status_code == 303
    assert 'location' in resp.headers
    assert resp.headers['location'] == '/login'


def test_get_novo_modelo(cliente, admin):
    resp = cliente.get('/novo-modelo')
    assert resp.status_code == 200
    assert 'Visualizar Rascunho'.lower() in resp.text.lower()
    assert 'img' in resp.text


def test_usuaria_nova():
    o = fabr.bd.Usuaria.novo(nome='aaa', senha='bbb')
    assert isinstance(o, fabr.bd.Usuaria)
    assert o.nome == 'aaa'
    assert o.senha != 'bbb'


def test_usuaria_verifica(usuaria):
    assert usuaria.verifica_senha('senha') is True
    assert usuaria.verifica_senha('senha_incorreta') is False


def test_usuaria_busca(sessao, usuaria):
    o1 = fabr.bd.Usuaria.buscar(sessao, nome=usuaria.nome)
    assert isinstance(o1, fabr.bd.Usuaria)
    o2 = fabr.bd.Usuaria.buscar(sessao, nome=usuaria.nome + 'a')
    assert o2 is None


def test_post_login(usuaria, cliente):
    resp = cliente.post(
        '/login',
        data=dict(nome=usuaria.nome, senha='senha'),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert 'set-cookie' in resp.headers
    assert resp.headers['set-cookie'].startswith('Authorization=')
    assert 'location' in resp.headers
    assert resp.headers['location'] == r'/u'


@pytest.mark.parametrize('incorreto', ['nome', 'senha'])
def test_post_login_com_informacao_incorreta(incorreto, usuaria, cliente):
    nome = usuaria.nome + ('a' if incorreto == 'nome' else '')
    senha = 'senha' + ('a' if incorreto == 'senha' else '')
    resp = cliente.post(
        '/login',
        data=dict(nome=nome, senha=senha),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert 'set-cookie' not in resp.headers
    assert 'location' in resp.headers
    assert resp.headers['location'] == r'/login'


def test_get_u_sem_usuario_retorna_redirecionamento_para_login(cliente):
    resp = cliente.get('/u', follow_redirects=False)
    assert resp.status_code == 303
    assert 'location' in resp.headers
    assert resp.headers['location'] == r'/login'


def test_get_u_retorna_pagina_com_nome(usuaria, cliente):
    resp1 = cliente.post(
        '/login',
        data=dict(nome=usuaria.nome, senha='senha'),
        follow_redirects=False,
    )
    token = resp1.cookies.get('Authorization')
    cliente.cookies.set('Authorization', token)

    resp2 = cliente.get('/u')
    assert resp2.status_code == 200
    assert usuaria.nome in resp2.text


def test_get_u_com_admin_retorna_nome(admin, cliente):
    resp = cliente.get('/u')
    assert resp.status_code == 200, resp.text
    assert admin.nome in resp.text


def test_get_u_com_admin_nao_chama_verificar_login(admin, cliente):
    with patch('fabriquinha.rotas.verificar_login') as m:
        cliente.get('/u')
        assert m.call_count == 0
