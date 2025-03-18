import fastapi

import fabriquinha as fabr


def criar_app(config: fabr.ambiente.Config | None = None) -> fastapi.FastAPI:
    config = fabr.ambiente.criar_config() if config is None else config

    app = fastapi.FastAPI(
        title='Fabriquinha de Certificados',
        description='',
        version='0.1',
        # openapi_url=settings.openapi_url,
        # docs_url=settings.docs_url,
        # redoc_url=settings.redoc_url,
        # default_response_class=fastapi.responses.ORJSONResponse,
        # servers=[
        #     dict(url='https://dev.api.facings.io'),
        #     dict(url='https://api.facings.io'),
        # ],
    )

    app.include_router(fabr.rotas.roteador)

    return app


app = criar_app()
