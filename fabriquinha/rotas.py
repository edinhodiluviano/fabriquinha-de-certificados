import base64
import datetime as dt
import io
import re
from typing import Annotated, Self

import fastapi
import jwt
import pymupdf
import weasyprint
from fastapi import Form, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import fabriquinha as fabr


roteador = fastapi.APIRouter()
htmls = Jinja2Templates(directory='fabriquinha/htmls')


@roteador.get('/ping', status_code=fastapi.status.HTTP_200_OK)
def ping() -> str:
    return 'pong'


@roteador.get('/favicon.ico', include_in_schema=False)
def get_favicon() -> FileResponse:
    return FileResponse(
        'fabriquinha/htmls/favicon.ico',
        media_type='image/vnd.microsoft.icon',
    )


def verificar_login(
    requisicao: Request,
    config: fabr.ambiente.ConfigDeps,
    sessao: fabr.bd.Sessao,
) -> fabr.bd.Usuaria | RedirectResponse:
    token = requisicao.cookies.get('Authorization')
    try:
        dados = jwt.decode(
            token,
            config.segredo.get_secret_value(),
            algorithms=['HS256'],
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_303_SEE_OTHER,
            headers=dict(location='/login'),
        )
    usuaria = fabr.bd.Usuaria.buscar(sessao=sessao, nome=dados['nome'])
    return usuaria


LoginDeps = Annotated[fabr.bd.Usuaria, fastapi.Depends(verificar_login)]


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


@roteador.get(
    '/criar-modelo',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=HTMLResponse,
)
def get_criar_modelo(
    req: Request,
    usuaria: LoginDeps,
    config: fabr.ambiente.ConfigDeps,
) -> HTMLResponse:
    # gera png como base64

    context = dict(png='')
    return htmls.TemplateResponse(
        request=req,
        name='criar-modelo.html',
        context=context,
    )


class TextoHtml(BaseModel):
    html: str


@roteador.post(
    '/html2png',
    status_code=fastapi.status.HTTP_200_OK,
    responses={200: dict(content={'image/png': {}})},
    response_class=Response,
)
def post_html2png(texto_html: TextoHtml) -> Response:
    html_inicial = texto_html.html

    qrcode = fabr.bd._gerar_qrcode('a')
    html = re.sub(r'\{\{ *?qrcode *?\}\}', qrcode, html_inicial)

    pdf_bytes = bytes(
        weasyprint.HTML(string=html).write_pdf(  # type: ignore[no-untyped-call]
            target=None,
            pdf_variant='pdf/a-3u',
        )
    )
    doc = pymupdf.Document(stream=pdf_bytes)  # type: ignore[no-untyped-call]
    pagina = next(iter(doc))
    pixels = pagina.get_pixmap()  # type: ignore[attr-defined]
    png_bytes = pixels.tobytes(output='png')
    b64_str = base64.b64encode(png_bytes).decode('utf8')
    src = 'data:image/png;base64,' + b64_str
    return Response(content=src, media_type='application/octet-stream')


class TokenRequest(BaseModel):
    nome: str
    senha: str


@roteador.post(
    '/login',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=JSONResponse,
)
def post_login(
    token_request: Annotated[TokenRequest, Form()],
    sessao: fabr.bd.Sessao,
    config: fabr.ambiente.ConfigDeps,
) -> RedirectResponse:
    usuaria = fabr.bd.Usuaria.buscar(sessao=sessao, nome=token_request.nome)
    if usuaria is None or usuaria.verifica_senha(token_request.senha) is False:
        print('autorizacao ruim' + '=' * 50)
        return RedirectResponse(
            url='/login',
            status_code=fastapi.status.HTTP_303_SEE_OTHER,
        )

    print('autorizacao legal' + '=' * 50)
    vencimento = dt.datetime.now(tz=dt.UTC) + dt.timedelta(hours=48)
    dados = dict(nome=usuaria.nome)
    token = jwt.encode(
        dados,
        config.segredo.get_secret_value(),
        algorithm='HS256',
    )

    resp = RedirectResponse(
        url='/u',
        status_code=fastapi.status.HTTP_303_SEE_OTHER,
    )
    resp.set_cookie(
        key='Authorization',
        value=token,
        expires=vencimento,
        secure=True,
        httponly=True,
        samesite='strict',
    )
    return resp


@roteador.get(
    '/login',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=HTMLResponse,
)
def get_login(req: Request) -> HTMLResponse:
    return htmls.TemplateResponse(
        request=req,
        name='login.html',
    )


@roteador.get(
    '/u',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=HTMLResponse,
)
def get_u(req: Request, usuaria: LoginDeps) -> HTMLResponse:
    return htmls.TemplateResponse(
        request=req,
        name='u.html',
        context=dict(usuaria=usuaria),
    )
