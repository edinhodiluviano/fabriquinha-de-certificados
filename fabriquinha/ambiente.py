from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr
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


class Ambiente(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        frozen=True,
        extra='ignore',
    )
    valor: Literal['teste', 'prod'] = Field(alias='AMBIENTE')


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    env: Literal['teste', 'prod']
    log_level: Literal['DEBUG', 'INFO', 'WARNING']
    banco: Banco


def criar_config(
    env: Literal['teste', 'prod'] | None = None,
    log_level: Literal['DEBUG', 'INFO', 'WARNING'] = 'INFO',
    banco: Banco | None = None,
) -> Config:
    env = Ambiente().valor if env is None else env  # type: ignore[call-arg]
    banco = Banco() if banco is None else banco  # type: ignore[call-arg]
    config = Config(
        env=env,
        log_level=log_level,
        banco=banco,
    )
    return config


config = criar_config()
