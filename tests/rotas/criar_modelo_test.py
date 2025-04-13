def test_get_criar_modelo_nao_logado_redireciona_para_login(cliente):
    resp = cliente.get('/criar-modelo', follow_redirects=False)
    assert resp.status_code == 303
    assert 'location' in resp.headers
    assert resp.headers['location'] == '/login'


def test_get_criar_modelo(cliente, admin):
    resp = cliente.get('/criar-modelo')
    assert resp.status_code == 200
    assert 'Visualizar Rascunho'.lower() in resp.text.lower()
    assert 'img' in resp.text
