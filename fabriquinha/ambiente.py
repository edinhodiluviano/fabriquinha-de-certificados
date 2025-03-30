from typing import Annotated, Literal

import fastapi
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Banco(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        frozen=True,
        extra='ignore',
    )
    endereco: str = Field(alias='POSTGRES_HOST')
    nome: str = Field(alias='POSTGRES_DB')
    usuario: str = Field(alias='POSTGRES_USER')
    senha: SecretStr = Field(alias='POSTGRES_PASSWORD')
    conexoes: int = Field(alias='POSTGRES_POOL_SIZE')


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        frozen=True,
        extra='ignore',
    )

    ambiente: Literal['teste', 'prod'] = Field(alias='AMBIENTE')
    log_level: Literal['DEBUG', 'INFO', 'WARNING']
    banco: Banco
    url_base: str = Field(alias='URL_BASE')


def criar_config(
    log_level: Literal['DEBUG', 'INFO', 'WARNING'] = 'INFO',
    banco: Banco | None = None,
) -> Config:
    banco = Banco() if banco is None else banco  # type: ignore[call-arg]
    config = Config(  # type: ignore[call-arg]
        log_level=log_level,
        banco=banco,
    )
    return config


def config_deps() -> Config:
    config = criar_config()
    return config


ConfigDeps = Annotated[Config, fastapi.Depends(config_deps)]
