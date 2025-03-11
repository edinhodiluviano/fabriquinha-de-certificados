import datetime as dt
import string
from uuid import uuid4

import jwt
import pytest

from fabriquinha import main


CHAVE_PRIVADA = '-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIPtUxyxlhjOWetjIYmc98dmB2GxpeaMPP64qBhZmG13r\n-----END PRIVATE KEY-----'
CHAVE_PUBLICA = '-----BEGIN PUBLIC KEY-----MCowBQYDK2VwAyEA7p4c1IU6aA65FWn6YZ+Bya5dRbfd4P6d4a6H0u9+gCg=-----END PUBLIC KEY-----'


def test_deve_sempre_passar():
    pass


@pytest.fixture
def conteudo_exemplo():
    c = main.Conteudo(
        titular=str(uuid4()),
        emissao=dt.date(2020, 1, 1),
        emissora=str(uuid4()),
        texto=str(uuid4()),
    )
    return c


def test_assinar_e_de_assinatura_sao_funcoes_inversas(conteudo_exemplo):
    s = main.assinar(conteudo_exemplo, CHAVE_PRIVADA)
    conteudo_gerada = main.deserializar(s, CHAVE_PUBLICA)
    assert conteudo_gerada == conteudo_exemplo


def test_se_chave_publica_for_diferente_entao_de_assinatura_levanta_erro(
    conteudo_exemplo,
):
    s = main.assinar(conteudo_exemplo, CHAVE_PRIVADA)
    with pytest.raises(jwt.exceptions.InvalidSignatureError):
        main.deserializar(s, CHAVE_PUBLICA.replace('A65', 'A64'))


@pytest.fixture
def token_exemplo():
    chars = (
        '0123456789'
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        'áàãâéèẽêíìĩîïóòõôúùũüç '
        'ÁÀÃÂÉÈẼÊÍÌĨÎÏÓÒÕÔÚÙŨÜÇ'
        '''!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'''
        '''\t\n\r\x0b\x0c'''
    )
    d = {
        chars: chars,
        chars + 'a': None,
        chars + 'b': 0,
        chars + 'c': 123456789,
        chars + 'd': 0.123456789,
    }
    token = jwt.encode(d, CHAVE_PRIVADA, algorithm='EdDSA')
    return token


def test_comprimir_e_descomprimir_retornam_mesmo_resultado(token_exemplo):
    token_comprimido = main._comprimir(token_exemplo)
    token_obtido = main._descomprimir(token_comprimido)
    assert token_obtido == token_exemplo


def test_comprimir_resulta_em_menos_caracteres(token_exemplo):
    token_comprimido = main._comprimir(token_exemplo)
    assert len(token_exemplo) > len(token_comprimido)


def test_comprimir_resulta_somente_em_chars_url_safe_plus_equal(token_exemplo):
    url_safe = set(string.ascii_letters + string.digits + '-._~')
    token_comprimido = main._comprimir(token_exemplo)
    chars = set(token_comprimido)
    assert len(chars - url_safe) == 0


def test_gerar_qrcode_retorna_str(conteudo_exemplo):
    conteudo_assinado = main.assinar(conteudo_exemplo, CHAVE_PRIVADA)
    qrcode = main.gerar_qrcode(conteudo_assinado, 'https://www.abc.com')
    assert isinstance(qrcode, str)
