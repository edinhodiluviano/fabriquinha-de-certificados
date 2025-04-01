import io

import fastapi
from fastapi import Request
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates

import fabriquinha as fabr


roteador = fastapi.APIRouter()
htmls = Jinja2Templates(directory='fabriquinha/htmls')


@roteador.get('/ping', status_code=fastapi.status.HTTP_200_OK)
def ping() -> str:
    return 'pong'


@roteador.get(
    '/',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=HTMLResponse,
)
def get_raiz(
    req: Request,
    config: fabr.ambiente.ConfigDeps,
) -> HTMLResponse:
    return htmls.TemplateResponse(
        request=req,
        name='raiz.html',
        context={},
    )


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
        png=cert.to_png(config),
    )
    return htmls.TemplateResponse(
        request=req,
        name='validar-certificado.html',
        context=context,
    )


@roteador.get(
    '/download/{codigo}.pdf',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=StreamingResponse,
)
def get_download(
    req: Request,
    codigo: str,
    sessao: fabr.bd.Sessao,
    config: fabr.ambiente.ConfigDeps,
) -> Response:
    cert = fabr.bd.Certificado.buscar(sessao, codigo)

    if cert is None:
        return RedirectResponse(url=f'/v/{codigo}', status_code=302)

    pdf_bytes = cert.to_pdf(config=config)
    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_stream.seek(0)

    cabecalho = {'Content-Disposition': 'attachment; filename=certificado.pdf'}
    return StreamingResponse(
        pdf_stream,
        media_type='application/pdf',
        headers=cabecalho,
    )
