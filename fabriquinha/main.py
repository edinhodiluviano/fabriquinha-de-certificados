import fastapi
from fastapi.staticfiles import StaticFiles

import fabriquinha as fabr


def criar_app(config: fabr.ambiente.Config | None = None) -> fastapi.FastAPI:
    config = fabr.ambiente.criar_config() if config is None else config

    app = fastapi.FastAPI(
        title='Fabriquinha de Certificados',
        description='',
        version='0.1',
    )

    app.mount(
        '/e',
        StaticFiles(directory='fabriquinha/estatico'),
        name='estatico',
    )
    app.include_router(fabr.rotas.roteador)

    return app


app = criar_app()
