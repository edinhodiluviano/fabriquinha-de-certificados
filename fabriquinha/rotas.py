import base64
import datetime as dt
import io
import logging
import re
from typing import Annotated, NoReturn

import fastapi
import jwt
import pymupdf
import sqlalchemy as sa
import toolz
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


logger = logging.getLogger(__name__)

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
) -> fabr.bd.Usuaria:
    token = requisicao.cookies.get('Authorization', '')

    def redireciona_para_login() -> NoReturn:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_303_SEE_OTHER,
            headers=dict(location='/login'),
        )

    try:
        dados = jwt.decode(
            token,
            config.segredo.get_secret_value(),
            algorithms=['HS256'],
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        redireciona_para_login()

    usuaria = fabr.bd.Usuaria.buscar(sessao=sessao, nome=dados['nome'])
    if usuaria is None:
        redireciona_para_login()

    return usuaria


LoginDeps = Annotated[fabr.bd.Usuaria, fastapi.Depends(verificar_login)]


@roteador.get(
    '/',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=HTMLResponse,
)
def get_raiz(
    req: Request,
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
        emissora=cert.modelo.comunidade.nome,
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
    sessao: fabr.bd.Sessao,
) -> HTMLResponse:
    # Busca comunidades que a pessoa usuária tem acesso
    comunidades = usuaria.organizadora(sessao) + usuaria.administradora(sessao)
    comunidades_nomes = sorted({c.nome for c in comunidades})

    context = dict(png='', comunidades=comunidades_nomes)
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

    qrcode = fabr.bd.gerar_qrcode('a')
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


@roteador.post(
    '/criar-modelo',
    status_code=fastapi.status.HTTP_303_SEE_OTHER,
    response_class=JSONResponse,
)
def post_criar_modelo(
    usuaria: LoginDeps,
    sessao: fabr.bd.Sessao,
    nome: Annotated[str, Form()],
    comunidade: Annotated[str, Form()],
    html: Annotated[str, Form()],
) -> JSONResponse:
    # Verifica se a usuária tem acesso à comunidade selecionada
    acesso = (
        sessao.query(fabr.bd.Acesso)
        .join(fabr.bd.Comunidade)
        .where(
            fabr.bd.Acesso.usuaria_id == usuaria.id,
            fabr.bd.Comunidade.nome == comunidade,
        )
        .first()
    )
    if not acesso:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail='Acesso negado a esta comunidade.',
        )

    m = fabr.bd.Modelo.novo(
        sessao=sessao,
        nome=nome,
        html=html,
        comunidade=comunidade,
    )
    sessao.add(m)
    sessao.commit()

    return JSONResponse(
        status_code=fastapi.status.HTTP_201_CREATED,
        content=dict(nome=m.nome, comunidade=comunidade),
    )


class TokenRequest(BaseModel):
    nome: str
    senha: str


@roteador.post(
    '/login',
    status_code=fastapi.status.HTTP_200_OK,
    response_class=RedirectResponse,
)
def post_login(
    token_request: Annotated[TokenRequest, Form()],
    sessao: fabr.bd.Sessao,
    config: fabr.ambiente.ConfigDeps,
) -> RedirectResponse:
    usuaria = fabr.bd.Usuaria.buscar(sessao=sessao, nome=token_request.nome)
    if usuaria is None or usuaria.verifica_senha(token_request.senha) is False:
        return RedirectResponse(
            url='/login',
            status_code=fastapi.status.HTTP_303_SEE_OTHER,
        )

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
def get_u(
    req: Request,
    usuaria: LoginDeps,
    sessao: fabr.bd.Sessao,
) -> HTMLResponse:
    comunidades = sorted(
        c.nome
        for c
        in usuaria.organizadora(sessao) + usuaria.administradora(sessao)
    )
    return htmls.TemplateResponse(
        request=req,
        name='u.html',
        context=dict(usuaria=usuaria, comunidades=comunidades),
    )


@roteador.get(
    '/comunidade/{nome}',
    status_code=fastapi.status.HTTP_200_OK,
    response_model=None,
)
def get_comunidade(
    nome: str,
    usuaria: LoginDeps,
    sessao: fabr.bd.Sessao,
) -> HTMLResponse | RedirectResponse:
    # verifica se a comunidade existe
    comunidade = fabr.bd.Comunidade.buscar(sessao, nome=nome)
    if comunidade is None:
        return RedirectResponse(
            url='/u',
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
        )

    # verifica se a pessoa tem acesso à comunidade
    stmt = (
        sa.select(fabr.bd.Acesso)
        .where(fabr.bd.Acesso.usuaria_id == usuaria.id)
        .where(fabr.bd.Acesso.comunidade_id == comunidade.id)
    )
    acesso = sessao.execute(stmt).scalars().one_or_none()
    if acesso is None:
        return RedirectResponse(
            url='/u',
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
        )

    context = dict(comunidade=comunidade.nome)

    # coleta todas as pessoas oragnizadoras e administradoras da comunidade
    stmt = (
        sa.select(fabr.bd.Acesso, fabr.bd.Usuaria)
        .join(fabr.bd.Usuaria)
        .order_by(fabr.bd.Acesso.tipo, fabr.bd.Usuaria.nome)
    )
    acesso_usuaria = sessao.execute(stmt).scalars().all()
    adiciona_acesso = lambda a: lambda u: setattr(u, 'acesso', a.tipo)
    usuarias = [toolz.do(adiciona_acesso(a), u) for a, u in acesso_usuaria]
    context = context | dict(usuarias=usuarias)

    # verifica o tipo de acesso
    if acesso.tipo in {'organizadora', 'administradora'}:
        context = context | dict(emitir=True)
    if acesso.tipo == 'administradora':
        pass

    # retorna a página
    return htmls.TemplateResponse(
        request=req,
        name='comunidade.html',
        context=context,
    )
