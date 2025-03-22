import sqlalchemy as sa

import fabriquinha as fabr


def test_criar_sessao_do_banco_retorna_objeto_de_sessao():
    with fabr.bd.criar_sessao() as sess:
        assert isinstance(sess, fabr.bd.Session)


def test_fixture_sessao_permite_iteragir_com_o_banco_de_dados(sessao):
    r = sessao.execute(sa.text('SELECT 1, 2')).fetchall()
    assert r == [(1, 2)]
