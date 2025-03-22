import fastapi
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import fabriquinha as fabr


roteador = fastapi.APIRouter()
htmls = Jinja2Templates(directory='fabriquinha/htmls')


@roteador.get('/ping', status_code=fastapi.status.HTTP_200_OK)
def ping() -> str:
    return 'pong'


@roteador.get(
    '/v/{codigo}',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=HTMLResponse,
)
def get_validar(
    req: Request,
    codigo: str,
    sessao: fabr.bd.Sessao,
    config: fabr.ambiente.ConfigDeps,
) -> HTMLResponse:
    cert = fabr.bd.Certificado.buscar(sessao, codigo)

    if cert is None:
        return htmls.TemplateResponse(
            request=req,
            name='cert-nao-encontrado.html',
            context=dict(codigo=codigo),
        )

    context = dict(
        certificado=cert.asdict(),
        emissora=cert.modelo.emissora,
        pdf=cert.to_pdf(config),
    )
    return htmls.TemplateResponse(
        request=req,
        name='validar-certificado.html',
        context=context,
    )
