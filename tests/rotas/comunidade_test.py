import pytest


@pytest.mark.skip
def test_get_comunidade(sessao, cliente, acessos, comunidades, admin):
    resp = cliente.get(f'/comunidade/{comunidades[0].nome}')
    assert resp.status_code == 200
    assert comunidades[0].nome in resp.text
