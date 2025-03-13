import contextlib
import datetime as dt
import functools
import logging
from collections.abc import Iterator
from typing import Literal, TypeAlias

import sqlalchemy as sa
import sqlalchemy.orm
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


class Base(DeclarativeBase):
    pass


class Modelo(Base):
    """
    nome: str
        nome do modelo
        Por exemplo: palestrante, participação, tutorial, etc.

    resumo: str
        hash de 8 caracteres do html do certificado
        hexdigest da função blake2b com 64 bits (digest_size=8)

    htmlzip: str
        html zipado para renderizar o certificado

    emissora: Emissora
        a entidade emissora do certificado
        Exemplo: PyLadies, GruPy-SP
    """

    __tablename__ = 'modelo'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    resumo: Mapped[str] = mapped_column(index=True)
    htmlzip: Mapped[str] = mapped_column(String(1024 * 100))
    emissora: Mapped[Emissora] = mapped_column(index=True)


class Certificado(Base):
    """
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

    id: Mapped[int] = mapped_column(primary_key=True)
    resumo: Mapped[str] = mapped_column(index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey('modelo.id'))
    model: Mapped[Modelo] = relationship()
    data: Mapped[dt.date] = mapped_column(index=True)
    conteudo: Mapped[Conteudo] = mapped_column(sa.JSON)


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
