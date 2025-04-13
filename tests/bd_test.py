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
    exp = sa.select(fabr.bd.Comunidade)
    assert len(sessao.scalars(exp).all()) == 0
    comunidade = fabr.bd.Comunidade(nome='GruPy-SP')
    sessao.add(comunidade)
    sessao.commit()
    assert len(sessao.scalars(exp).all()) == 1


def test_tabelas_sao_deletadas_entre_tests_parte_2(sessao):
    exp = sa.select(fabr.bd.Comunidade)
    assert len(sessao.scalars(exp).all()) == 0
    comunidade = fabr.bd.Comunidade(nome='GruPy-SP')
    sessao.add(comunidade)
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


def test_gerar_modelo_novo(sessao, comunidades):
    m = fabr.bd.Modelo.novo(
        sessao=sessao,
        nome='nome',
        html='aaa\n',
        comunidade='GruPy-SP',
    )
    sessao.add(m)
    sessao.commit()
    assert m.nome == 'nome'
    assert m.htmlzip == 'eJxLTEzkAgADdwEu'
    assert m.comunidade.nome == 'GruPy-SP'
    assert m.resumo == 'a1c57efd1cd0c881'


def test_buscar_modelos(comunidades, modelo, sessao):
    novo_modelo_1 = fabr.bd.Modelo.novo(
        sessao=sessao,
        nome=modelo.nome + 'a',
        html='aaa\n',
        comunidade=comunidades[0].nome,
    )
    novo_modelo_2 = fabr.bd.Modelo.novo(
        sessao=sessao,
        nome=modelo.nome + 'a',
        html='aaa\n',
        comunidade=comunidades[1].nome,
    )
    sessao.add_all([novo_modelo_1, novo_modelo_2])
    sessao.commit()

    comunidade = fabr.bd.Comunidade.buscar(sessao, comunidades[0].nome)
    modelos = comunidade.modelos
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


def test_usuaria_busca_somente_ativa_com_usuaria_ativa(sessao, usuaria):
    u = fabr.bd.Usuaria.buscar(sessao, nome=usuaria.nome, somente_ativas=True)
    assert u.nome == usuaria.nome


def test_usuaria_busca_somente_ativa_com_usuaria_inativa(sessao, usuaria):
    usuaria.ativa = False
    sessao.commit()
    u = fabr.bd.Usuaria.buscar(sessao, nome=usuaria.nome, somente_ativas=True)
    assert u is None


def test_usuaria_comunidades(sessao, comunidades, usuarias, acessos):
    assert usuarias[0].administradora(sessao) == comunidades
    assert usuarias[0].organizadora(sessao) == []
    assert usuarias[1].administradora(sessao) == []
    assert usuarias[1].organizadora(sessao) == comunidades
    assert usuarias[2].administradora(sessao) == comunidades[:1]
    assert usuarias[2].organizadora(sessao) == []
    assert usuarias[4].administradora(sessao) == []
    assert usuarias[4].organizadora(sessao) == comunidades[:1]
