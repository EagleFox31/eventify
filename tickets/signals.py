from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from .models import Ticket
from .utils.pdf import build_ticket_pdf

@receiver(post_save, sender=Ticket)
def generate_pdf_on_create(sender, instance, created, **kwargs):
    if created and not instance.pdf_file:
        pdf_io = build_ticket_pdf(instance)
        filename = f"ticket_{instance.id}.pdf"
        instance.pdf_file.save(filename, ContentFile(pdf_io.read()), save=True)
