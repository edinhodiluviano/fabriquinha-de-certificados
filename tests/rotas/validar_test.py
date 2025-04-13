def test_get_validar_com_codigo_inexistente(certificados, cliente):
    resp = cliente.get('v/aaaaaaaaaaa')
    assert resp.status_code == 200
    assert 'não encontrado' in resp.text


def test_get_validar_com_codigo_valido(certificados, cliente):
    resp = cliente.get('v/' + certificados[0].codigo)
    assert resp.status_code == 200
    assert certificados[0].modelo.comunidade.nome in resp.text
    assert 'Certificado OK!' in resp.text
