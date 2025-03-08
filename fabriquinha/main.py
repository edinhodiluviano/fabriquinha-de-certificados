import base64
import datetime as dt
import io
import zlib
from typing import NewType, Annotated
from urllib.parse import urljoin

import pydantic
import jwt
import qrcode
from pydantic.types import StringConstraints


StrCurta = Annotated[str, StringConstraints(min_length=5, max_length=50)]
StrLonga = Annotated[str, StringConstraints(min_length=5, max_length=250)]
ConteudoAssinado = NewType('ConteudoAssinado', str)


def _comprimir(s: str) -> str:
    bytes_comprimidos = zlib.compress(s.encode('utf8'))
    str_b64 = base64.urlsafe_b64encode(bytes_comprimidos).decode('utf8')
    str_url_safe = str_b64.replace('=', '~')
    return str_url_safe


def _descomprimir(s: str) -> str:
    bytes_b64 = s.replace('~', '=').encode('utf8')
    bytes_comprimidos = base64.urlsafe_b64decode(bytes_b64)
    bytes_cru = zlib.decompress(bytes_comprimidos)
    return bytes_cru.decode('utf8')


class Conteudo(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, extra='allow')

    titular: StrCurta  # Pessoa portadora do certificado
    emissao: dt.date  # Data do evento
    emissora: StrCurta  # Comunidade emissora. Ex.: GruPy-SP, PyLadies, etc
    texto: StrLonga  # Descricao do certificado. Campo de texto livre.


def assinar(conteudo: Conteudo, chave_privada: str) -> ConteudoAssinado:
    d = conteudo.model_dump()
    d = d | dict(emissao=d['emissao'].isoformat())
    e = jwt.encode(d, chave_privada, algorithm='EdDSA')
    c = _comprimir(e)
    return ConteudoAssinado(c)


def deserializar(
    conteudo: ConteudoAssinado,
    chave_publica: str,
) -> Conteudo:
    s = _descomprimir(conteudo)
    d = jwt.decode(s, chave_publica, algorithms=['EdDSA'])
    c = Conteudo(**d)
    return c


def gerar_qrcode(conteudo: ConteudoAssinado, url_base: str) -> bytes:
    # mimetype=image/png
    qrcode_str = urljoin(url_base, conteudo)
    img_obj = qrcode.make(qrcode_str)

    img_io = io.BytesIO()
    img_obj.save(img_io, 'PNG')
    img_io.seek(0)
    img_bytes = img_io.read()
    return img_bytes
