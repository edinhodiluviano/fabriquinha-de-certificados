from unittest.mock import patch


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


def test_get_u_com_token_gerado_para_usuaria_apagada(sessao, usuaria, cliente):
    # gera token para pessoa usuaria (válida neste momento)
    resp1 = cliente.post(
        '/login',
        data=dict(nome=usuaria.nome, senha='senha'),
        follow_redirects=False,
    )
    token = resp1.cookies.get('Authorization')
    cliente.cookies.set('Authorization', token)

    # invalida o registro da pessoa usuária de agora em diante
    sessao.delete(usuaria)
    sessao.commit()

    # sut
    resp2 = cliente.get('/u', follow_redirects=False)

    # assert
    assert resp2.status_code == 303
    assert 'location' in resp2.headers
    assert resp2.headers['location'] == r'/login'


def test_get_u_com_token_gerado_para_usuaria_inativa(sessao, usuaria, cliente):
    # gera token para pessoa usuaria (válida neste momento)
    resp1 = cliente.post(
        '/login',
        data=dict(nome=usuaria.nome, senha='senha'),
        follow_redirects=False,
    )
    token = resp1.cookies.get('Authorization')
    cliente.cookies.set('Authorization', token)

    # invalida o registro da pessoa usuária de agora em diante
    usuaria.ativa = False
    sessao.commit()

    # sut
    resp2 = cliente.get('/u', follow_redirects=False)

    # assert
    assert resp2.status_code == 303
    assert 'location' in resp2.headers
    assert resp2.headers['location'] == r'/login'
