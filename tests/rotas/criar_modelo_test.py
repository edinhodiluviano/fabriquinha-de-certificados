import sqlalchemy as sa

import fabriquinha as fabr


def test_get_criar_modelo_nao_logado_redireciona_para_login(cliente):
    resp = cliente.get('/criar-modelo', follow_redirects=False)
    assert resp.status_code == 303
    assert 'location' in resp.headers
    assert resp.headers['location'] == '/login'


def test_get_criar_modelo(cliente, acessos, admin):
    resp = cliente.get('/criar-modelo')
    assert resp.status_code == 200
    assert 'Visualizar Rascunho'.lower() in resp.text.lower()
    assert 'img' in resp.text
    assert 'GruPy-SP' in resp.text
    assert 'PyLadies' in resp.text


def test_post_criar_modelo(
    sessao, cliente, acessos, comunidades, admin, gerar_str,
):
    nome = gerar_str(20)
    data = dict(
        nome=nome,
        comunidade=comunidades[0].nome,
        html=gerar_str(100),
    )
    resp = cliente.post('/criar-modelo', data=data)
    assert resp.status_code == 201, resp.text

    stmt = sa.select(fabr.bd.Modelo).where(fabr.bd.Modelo.nome == nome)
    modelo = sessao.execute(stmt).scalar_one()
    assert modelo.nome == nome
    assert modelo.comunidade_id == comunidades[0].id


def test_post_criar_modelo_com_usuaria_sem_acesso(
    sessao, cliente, admin, comunidades, gerar_str,
):
    nome = gerar_str(20)
    data = dict(
        nome=nome,
        comunidade=comunidades[0].nome,
        html=gerar_str(100),
    )
    resp = cliente.post('/criar-modelo', data=data)
    assert resp.status_code == 403

    stmt = sa.select(fabr.bd.Modelo).where(fabr.bd.Modelo.nome == nome)
    modelos = sessao.execute(stmt).fetchall()
    assert len(modelos) == 0
