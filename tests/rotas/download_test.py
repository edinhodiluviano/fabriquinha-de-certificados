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
