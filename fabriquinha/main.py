import fastapi

import fabriquinha as fabr


def criar_app(config: fabr.ambiente.Config | None = None) -> fastapi.FastAPI:
    config = fabr.ambiente.criar_config() if config is None else config

    app = fastapi.FastAPI(
        title='Fabriquinha de Certificados',
        description='',
        version='0.1',
    )

    app.include_router(fabr.rotas.roteador)

    return app


app = criar_app()
