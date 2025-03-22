import base64
import contextlib
import datetime as dt
import functools
import hashlib
import io
import logging
import random
import zlib
from collections.abc import Iterator
from typing import Annotated, Literal, Self, TypeAlias
from urllib.parse import urljoin

import fastapi
import qrcode
import sqlalchemy as sa
import sqlalchemy.orm
import weasyprint
from jinja2 import Template
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)

import fabriquinha as fabr


logger = logging.getLogger(__name__)

Emissora: TypeAlias = Literal['PyLadies', 'GruPy-SP']
Conteudo: TypeAlias = dict[str, str | int | float | dt.date]


def criar_url(config: fabr.ambiente.Config) -> sa.engine.URL:
    url = sa.engine.URL.create(
        drivername='postgresql+psycopg',
        username=config.banco.usuario,
        password=config.banco.senha.get_secret_value(),
        host=config.banco.endereco,
        database=config.banco.nome,
    )
    return url


@functools.cache
def criar_motor(config: fabr.ambiente.Config) -> sa.Engine:
    url = criar_url(config=config)
    logger.debug('Criando motor de conexão ao banco de dados')
    motor = sa.create_engine(
        url,
        # json_serializer=dumps,
        pool_size=config.banco.conexoes,
        max_overflow=2,
        pool_timeout=5,
    )
    logger.debug('Motor de conexão criado')
    return motor


@contextlib.contextmanager
def criar_sessao(
    config: fabr.ambiente.Config | None = None,
) -> Iterator[Session]:
    """
    Retorna uma sessão através do gerenciador de contexto.

    Feita para ser usada dentro de blocos `with`.
    """
    config = fabr.ambiente.criar_config() if config is None else config
    motor = criar_motor(config=config)
    sessao_local = sa.orm.sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=motor,
    )
    sessao = sessao_local()
    try:
        yield sessao
    finally:
        sessao.close()


def sessao_deps() -> Iterator[Session]:
    with criar_sessao() as sess:
        yield sess


Sessao = Annotated[Session, fastapi.Depends(sessao_deps)]


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'{cls_name}(id={self.id})'

    def asdict(
        self,
        excluir: set[str] | list[str] | None = None,
    ) -> dict[str, str | int | float | None | dt.date]:
        if excluir is None:
            excluir = {'_sa_instance_state', 'id'}
        excluir = set(excluir)
        d = self.__dict__
        return {k: v for k, v in d.items() if k not in excluir}


class Modelo(Base):
    """
    nome: str
        nome do modelo
        Por exemplo: palestrante, participação, tutorial, etc.

    resumo: str
        hash de 16 caracteres do html do certificado
        hexdigest da função blake2b com 64 bits (digest_size=8)

    htmlzip: str
        html zipado para renderizar o certificado

    emissora: Emissora
        a entidade emissora do certificado
        Exemplo: PyLadies, GruPy-SP
    """

    __tablename__ = 'modelo'

    nome: Mapped[str] = mapped_column(String(100))
    resumo: Mapped[str] = mapped_column(index=True)
    htmlzip: Mapped[str] = mapped_column(String(1024 * 100))
    emissora: Mapped[Emissora] = mapped_column(index=True)

    @classmethod
    def novo(cls, nome: str, html: str, emissora: Emissora) -> Self:
        r = hashlib.blake2b(html.encode('utf8'), digest_size=8).hexdigest()
        h = _comprimir(html)
        o = cls(nome=nome, resumo=r, htmlzip=h, emissora=emissora)
        return o

    @classmethod
    def buscar(cls, sessao: Sessao, emissora: Emissora) -> list[Self]:
        stmt = sa.select(cls).where(cls.emissora == emissora)
        linhas = sessao.execute(stmt).scalars().all()
        modelos = list(linhas)
        return modelos


def _gerar_qrcode(s: str) -> str:
    # mimetype=image/png
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=4,
    )
    qr.add_data(s)
    img_obj = qr.make_image(fill_color='black', back_color='white')

    img_io = io.BytesIO()
    img_obj.save(img_io, 'PNG')
    img_io.seek(0)
    img_bytes = img_io.read()
    img_base64 = base64.b64encode(img_bytes)
    img_base64_str = img_base64.decode('utf8')
    return img_base64_str


def _comprimir(s: str) -> str:
    raw_bytes = s.encode('utf8')
    z_bytes = zlib.compress(raw_bytes)
    z_b64 = base64.b64encode(z_bytes)
    z_str = z_b64.decode('utf8')
    return z_str


def _descomprimir(s: str) -> str:
    z_b64 = s.encode('utf8')
    z_bytes = base64.b64decode(z_b64)
    raw_bytes = zlib.decompress(z_bytes)
    s = raw_bytes.decode('utf8')
    return s


class Certificado(Base):
    """
    codigo: str
        Código único do certificado.
        Composto de exatamente 12 caracteres alfa numéricos.

    data: dt.date
        Data do certificado
        Não necessariamente é a mesma data na qual o certificado foi emitido
        No caso do evento ter mais de um dia de duração, utilize a data do
        último dia do evento.

    emissora: Emissora
        Entidade emissora do certificado (ex.: GruPy-SP, PyLadies, etc).

    modelo: Modelo
        Relacionamento com o modelo que deve ser utilizado para renderizar
        este certificado

    conteudo: Conteudo
        Quase um JSON. Permite incluir campos customizados no certificado.
        Por exemplo: titulo_da_palestra, duração, cpf, etc...
    """

    __tablename__ = 'certificado'

    codigo: Mapped[str] = mapped_column(String(12), index=True, unique=True)
    modelo_id: Mapped[int] = mapped_column(ForeignKey('modelo.id'))
    modelo: Mapped[Modelo] = relationship()
    data: Mapped[dt.date] = mapped_column(index=True)
    conteudo: Mapped[Conteudo] = mapped_column(sa.JSON)

    @classmethod
    def novo(cls, modelo: Modelo, data: dt.date, conteudo: Conteudo) -> Self:
        car = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        codigo = ''.join(random.choices(car, k=12))
        o = cls(
            codigo=codigo,
            modelo=modelo,
            data=data,
            conteudo=conteudo,
        )
        return o

    @classmethod
    def buscar(cls, sessao: Sessao, codigo: str) -> Self | None:
        stmt = sa.select(cls).where(cls.codigo == codigo)
        try:
            cert = sessao.execute(stmt).scalars().one()
        except sa.exc.NoResultFound:
            cert = None
        return cert

    def to_pdf(self, config: fabr.ambiente.Config) -> str:
        url_inter = urljoin(config.url_base, 'v')
        url_validacao = urljoin(url_inter, self.codigo)
        qrcode = _gerar_qrcode(url_validacao)

        contexto = {
            **self.conteudo,
            'qrcode': qrcode,
            'url_validacao': url_validacao,
            'emissora': self.modelo.emissora,
            'data': self.data,
        }

        html_modelo = _descomprimir(self.modelo.htmlzip)
        html_final = Template(html_modelo).render(contexto)

        pdf_bytes = bytes(
            weasyprint.HTML(string=html_final).write_pdf(  # type: ignore[no-untyped-call]
                target=None,
                pdf_variant='pdf/a-3u',
            )
        )
        pdf_b64 = base64.b64encode(pdf_bytes)
        pdf_b64_str = pdf_b64.decode('utf8')
        return pdf_b64_str
