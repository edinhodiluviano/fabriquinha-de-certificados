import base64
import io
import zlib
from urllib.parse import urljoin

import fastapi
import qrcode
import sqlalchemy as sa
import weasyprint
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Template

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
    cert = buscar_certificado(sessao, codigo)

    if cert is None:
        return htmls.TemplateResponse(
            request=req,
            name='cert-nao-encontrado.html',
            context=dict(codigo=codigo),
        )

    context = dict(
        certificado=cert.asdict(),
        emissora=cert.modelo.emissora,
        pdf=gerar_pdf(cert, config),
    )
    return htmls.TemplateResponse(
        request=req,
        name='validar-certificado.html',
        context=context,
    )


def buscar_certificado(
    sessao: fabr.bd.Sessao,
    codigo: str,
) -> fabr.bd.Certificado | None:
    stmt = sa.select(fabr.bd.Certificado).where(
        fabr.bd.Certificado.codigo == codigo
    )
    try:
        cert = sessao.execute(stmt).scalars().one()
    except sa.exc.NoResultFound:
        cert = None
    return cert


def gerar_qrcode(s: str) -> str:
    # mimetype=image/png
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=4,
    )
    qr.add_data(s)
    img_obj = qr.make_image(fill_color='black', back_color='white')

    img_io = io.BytesIO()
    img_obj.save(img_io, 'PNG')
    img_io.seek(0)
    img_bytes = img_io.read()
    img_base64 = base64.b64encode(img_bytes)
    img_base64_str = img_base64.decode('utf8')
    return img_base64_str


def comprimir(s: str) -> str:
    raw_bytes = s.encode('utf8')
    z_bytes = zlib.compress(raw_bytes)
    z_b64 = base64.b64encode(z_bytes)
    z_str = z_b64.decode('utf8')
    return z_str


def descomprimir(s: str) -> str:
    z_b64 = s.encode('utf8')
    z_bytes = base64.b64decode(z_b64)
    raw_bytes = zlib.decompress(z_bytes)
    s = raw_bytes.decode('utf8')
    return s


def gerar_pdf(
    certificado: fabr.bd.Certificado,
    config: fabr.ambiente.Config,
) -> str:
    url_inter = urljoin(config.url_base, 'v')
    url_validacao = urljoin(url_inter, certificado.codigo)
    qrcode = gerar_qrcode(url_validacao)

    contexto = {
        **certificado.conteudo,
        'qrcode': qrcode,
        'url_validacao': url_validacao,
        'emissora': certificado.modelo.emissora,
        'data': certificado.data,
    }

    html_modelo = descomprimir(certificado.modelo.htmlzip)
    html_final = Template(html_modelo).render(contexto)

    pdf_bytes = bytes(
        weasyprint.HTML(string=html_final).write_pdf(  # type: ignore[no-untyped-call]
            target=None,
            pdf_variant='pdf/a-3u',
        )
    )
    pdf_b64 = base64.b64encode(pdf_bytes)
    pdf_b64_str = pdf_b64.decode('utf8')
    return pdf_b64_str
