from logging.config import fileConfig

from alembic import context

import fabriquinha as fabr


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = fabr.bd.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# option = config.get_main_option("option")  NOQA: ERA001
# ... etc.


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    config = fabr.ambiente.criar_config()
    motor = fabr.bd.criar_motor(config=config)

    with motor.connect() as conexao:
        context.configure(
            connection=conexao,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    msg = 'não são permitidas migrações offline'  # pragma: no cover
    raise NotImplementedError(msg)  # pragma: no cover

run_migrations_online()
