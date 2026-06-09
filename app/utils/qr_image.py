import io

import qrcode
from qrcode.constants import ERROR_CORRECT_H


def qr_png_bytes(data: str, *, box_size: int = 10) -> bytes:
    """PNG QR without compression — send as document in Telegram, not photo."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()
