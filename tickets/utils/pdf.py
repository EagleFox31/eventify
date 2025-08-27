import io, base64, qrcode, weasyprint
from django.template.loader import render_to_string
from django.conf import settings

def build_ticket_pdf(ticket):
    qr_img = qrcode.make(ticket.qr_hash)
    qr_io  = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_b64 = base64.b64encode(qr_io.getvalue()).decode()

    html = render_to_string("tickets/pdf_ticket.html", {
        "ticket": ticket,
        "qr_b64": qr_b64
    })
    pdf_bytes = weasyprint.HTML(string=html, base_url=settings.BASE_DIR).write_pdf()
    return io.BytesIO(pdf_bytes)
