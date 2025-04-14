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

import argon2
import fastapi
import pymupdf
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

TipoDeAcesso: TypeAlias = Literal['Organizadora', 'Administradora']
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

convencao_de_nomes = dict(
    ix='ix_%(column_0_label)s',
    uq='uq_%(table_name)s_%(column_0_name)s',
    ck='ck_%(table_name)s_%(constraint_name)s',
    fk='fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    pk='pk_%(table_name)s',
)


class Base(DeclarativeBase):
    metadata = sa.MetaData(naming_convention=convencao_de_nomes)

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'{cls_name}(id={self.id})'  # type: ignore[attr-defined]

    def asdict(
        self,
        excluir: set[str] | list[str] | None = None,
    ) -> dict[str, str | int | float | None | dt.date]:
        if excluir is None:
            excluir = {'_sa_instance_state', 'id'}
        excluir = set(excluir)
        d = self.__dict__
        return {k: v for k, v in d.items() if k not in excluir}


class Comunidade(Base):
    __tablename__ = 'comunidade'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), index=True, unique=True)
    modelos: Mapped[list['Modelo']] = relationship(back_populates='comunidade')

    @classmethod
    def buscar(cls, sessao: Sessao, nome: str) -> Self | None:
        stmt = sa.select(cls).where(cls.nome == nome)
        o = sessao.execute(stmt).scalars().one_or_none()
        return o


class Usuaria(Base):
    """
    nome: str
        Nome da pessoa usuária.

    senha: str
        Hash da senha.
    """

    __tablename__ = 'usuaria'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), index=True, unique=True)
    senha: Mapped[str] = mapped_column(String(100))
    ativa: Mapped[bool] = mapped_column(index=True)
    sysadmin: Mapped[bool] = mapped_column()

    @classmethod
    def novo(cls, nome: str, senha: str, teste: bool = False) -> Self:
        if teste:
            ph = argon2.PasswordHasher(time_cost=3, memory_cost=100)
        else:
            ph = argon2.PasswordHasher()
        hash_da_senha = ph.hash(senha)
        o = cls(nome=nome, senha=hash_da_senha, ativa=True, sysadmin=False)
        return o

    def verifica_senha(self, senha_dada: str) -> bool:
        try:
            argon2.PasswordHasher().verify(self.senha, senha_dada)
        except argon2.exceptions.VerifyMismatchError:
            return False
        return True

    @classmethod
    def buscar(
        cls,
        sessao: Sessao,
        nome: str,
        somente_ativas: bool = True,
    ) -> Self | None:
        stmt = sa.select(cls).where(cls.nome == nome)
        if somente_ativas:
            stmt = stmt.where(cls.ativa == True)
        o = sessao.execute(stmt).scalars().one_or_none()
        return o

    def organizadora(self, sessao: Sessao) -> list[Comunidade]:
        """Retorna as comunidades onde a usuária é Organizadora."""
        stmt = (
            sa.select(Comunidade)
            .join(Acesso)
            .where(Acesso.usuaria_id == self.id)
            .where(Acesso.tipo == 'organizadora')
        )
        comunidades = sessao.execute(stmt).scalars().all()
        return comunidades

    def administradora(self, sessao: Sessao) -> list[Comunidade]:
        """Retorna as comunidades onde a usuária é Administradora."""
        stmt = (
            sa.select(Comunidade)
            .join(Acesso)
            .where(Acesso.usuaria_id == self.id)
            .where(Acesso.tipo == 'administradora')
        )
        comunidades = sessao.execute(stmt).scalars().all()
        return comunidades


class Acesso(Base):
    __tablename__ = 'acesso'

    usuaria_id: Mapped[int] = mapped_column(
        sa.ForeignKey('usuaria.id'),
        primary_key=True,
    )
    comunidade_id: Mapped[int] = mapped_column(
        sa.ForeignKey('comunidade.id'),
        primary_key=True,
    )
    tipo: Mapped[TipoDeAcesso] = mapped_column(String(100), index=True)


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

    comunidade: Comunidade
        a comunidade emissora do certificado
        Exemplo: PyLadies, GruPy-SP
    """

    __tablename__ = 'modelo'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    resumo: Mapped[str] = mapped_column(index=True)
    htmlzip: Mapped[str] = mapped_column(String(1024 * 100))
    comunidade_id: Mapped[int] = mapped_column(
        sa.ForeignKey('comunidade.id'),
        index=True,
    )
    comunidade: Mapped[Comunidade] = relationship(back_populates='modelos')

    @classmethod
    def novo(
        cls,
        sessao: Sessao,
        nome: str,
        html: str,
        comunidade: str,
    ) -> Self:
        r = hashlib.blake2b(html.encode('utf8'), digest_size=8).hexdigest()
        h = _comprimir(html)

        stmt = sa.select(Comunidade).where(Comunidade.nome == comunidade)
        comunidade_obj = sessao.execute(stmt).scalar_one()
        comunidade_id = comunidade_obj.id
        o = cls(nome=nome, resumo=r, htmlzip=h, comunidade_id=comunidade_id)
        return o


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

    modelo: Modelo
        Relacionamento com o modelo que deve ser utilizado para renderizar
        este certificado

    conteudo: Conteudo
        Quase um JSON. Permite incluir campos customizados no certificado.
        Por exemplo: titulo_da_palestra, duração, cpf, etc...
    """

    __tablename__ = 'certificado'

    id: Mapped[int] = mapped_column(primary_key=True)
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

    def to_pdf(self, config: fabr.ambiente.Config) -> bytes:
        url_validacao = urljoin(config.url_base, 'v/' + self.codigo)
        qrcode = _gerar_qrcode(url_validacao)

        contexto = {
            **self.conteudo,
            'qrcode': qrcode,
            'url_validacao': url_validacao,
            'emissora': self.modelo.comunidade.nome,
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
        return pdf_bytes

    def to_png(self, config: fabr.ambiente.Config) -> str:
        pdf_bytes = self.to_pdf(config=config)
        doc = pymupdf.Document(stream=pdf_bytes)  # type: ignore[no-untyped-call]
        pagina = next(iter(doc))
        pixels = pagina.get_pixmap()  # type: ignore[attr-defined]
        png_bytes = pixels.tobytes(output='png')
        b64_str = base64.b64encode(png_bytes).decode('utf8')
        return b64_str
