import base64
import io

import qrcode


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
