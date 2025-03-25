import datetime as dt

import sqlalchemy as sa

import fabriquinha as fabr


def test_criar_sessao_do_banco_retorna_objeto_de_sessao():
    with fabr.bd.criar_sessao() as sess:
        assert isinstance(sess, fabr.bd.Session)


def test_fixture_sessao_permite_iteragir_com_o_banco_de_dados(sessao):
    r = sessao.execute(sa.text('SELECT 1, 2')).fetchall()
    assert r == [(1, 2)]


def test_tabelas_sao_deletadas_entre_tests_parte_1(sessao):
    exp = sa.select(fabr.bd.Modelo)
    assert len(sessao.scalars(exp).all()) == 0
    modelo = fabr.bd.Modelo(
        nome='a', resumo='b', htmlzip='c', emissora='GruPy-SP'
    )
    sessao.add(modelo)
    sessao.commit()
    assert len(sessao.scalars(exp).all()) == 1


def test_tabelas_sao_deletadas_entre_tests_parte_2(sessao):
    exp = sa.select(fabr.bd.Modelo)
    assert len(sessao.scalars(exp).all()) == 0
    modelo = fabr.bd.Modelo(
        nome='d', resumo='e', htmlzip='f', emissora='GruPy-SP'
    )
    sessao.add(modelo)
    sessao.commit()
    assert len(sessao.scalars(exp).all()) == 1


def test_buscar_cert_retorna_certificado(sessao, certificados):
    certificado = certificados[0]
    resp = fabr.bd.Certificado.buscar(sessao, certificado.codigo)
    assert isinstance(resp, fabr.bd.Certificado)
    assert resp == certificado
    assert resp.id == certificado.id
    assert resp.codigo == certificado.codigo


def test_buscar_cert_com_codigo_inexistente_retorna_none(sessao, certificados):
    resp = fabr.bd.Certificado.buscar(sessao, 'a' * 12)
    assert resp is None


def test_comprimir_retorna_str(gerar_str):
    s = gerar_str(20)
    resp = fabr.bd._comprimir(s)
    assert isinstance(resp, str)


def test_descomprimir_e_inversa_de_comprimir(gerar_str):
    s = gerar_str(20)
    inter = fabr.bd._comprimir(s)
    resp = fabr.bd._descomprimir(inter)
    assert resp == s


def test_gerar_pdf_retorna_bytes(certificados, config):
    pdf = certificados[0].to_pdf(config)
    assert isinstance(pdf, bytes)


def test_gerar_png_retorna_str(certificados, config):
    png = certificados[0].to_png(config)
    assert isinstance(png, str)


def test_gerar_qrcode_retorna_str(gerar_str):
    qrcode = fabr.bd._gerar_qrcode(s=gerar_str(10))
    assert isinstance(qrcode, str)


def test_gerar_modelo_novo():
    m = fabr.bd.Modelo.novo(
        nome='nome',
        html='aaa\n',
        emissora='GruPy-SP',
    )
    assert m.nome == 'nome'
    assert m.htmlzip == 'eJxLTEzkAgADdwEu'
    assert m.emissora == 'GruPy-SP'
    assert m.resumo == 'a1c57efd1cd0c881'


def test_buscar_modelo(modelo, sessao):
    novo_modelo_1 = fabr.bd.Modelo.novo(
        nome=modelo.nome + 'a',
        html='aaa\n',
        emissora=modelo.emissora,
    )
    novo_modelo_2 = fabr.bd.Modelo.novo(
        nome=modelo.nome + 'a',
        html='aaa\n',
        emissora='PyLadies',
    )
    sessao.add_all([novo_modelo_1, novo_modelo_2])
    sessao.commit()
    modelos = fabr.bd.Modelo.buscar(sessao, modelo.emissora)
    assert modelos == [modelo, novo_modelo_1]


def test_novo_certificado(modelo):
    cert = fabr.bd.Certificado.novo(
        modelo=modelo,
        data=dt.date(2020, 1, 1),
        conteudo=dict(a=1),
    )
    assert cert.modelo == modelo
    assert cert.data == dt.date(2020, 1, 1)
    assert cert.conteudo == dict(a=1)
    assert isinstance(cert.codigo, str)
    assert len(cert.codigo) == 12


def test_a():
    modelo = fabr.bd.Modelo.novo(
        nome='a',
        html='a',
        emissora='PyLadies',
    )
    cert = fabr.bd.Certificado.novo(
        modelo=modelo,
        data=dt.date(2020, 1, 1),
        conteudo={'a': 42},
    )
    assert isinstance(cert, fabr.bd.Certificado)
    assert cert.conteudo == dict(a=42)
