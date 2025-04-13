import pytest


def test_get_login(cliente):
    resp = cliente.get('/login')
    assert resp.status_code == 200
    pagina = resp.text.lower()
    assert 'nome' in pagina
    assert 'senha' in pagina
    assert 'entrar' in pagina


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
