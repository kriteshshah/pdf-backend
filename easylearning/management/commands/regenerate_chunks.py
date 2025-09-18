from django.core.management.base import BaseCommand
from easylearning.models import PDFDocument, PDFChunk
from easylearning.views import create_pdf_chunks


class Command(BaseCommand):
    help = 'Regenerate PDF chunks with improved chunking logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pdf-id',
            type=str,
            help='Specific PDF ID to regenerate chunks for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Regenerate chunks for all PDFs',
        )

    def handle(self, *args, **options):
        if options['pdf_id']:
            try:
                pdf_doc = PDFDocument.objects.get(id=options['pdf_id'])
                self.stdout.write(f"Regenerating chunks for PDF: {pdf_doc.title}")
                
                # Delete existing chunks
                PDFChunk.objects.filter(pdf_document=pdf_doc).delete()
                self.stdout.write("Deleted existing chunks")
                
                # Create new chunks
                create_pdf_chunks(pdf_doc)
                self.stdout.write(self.style.SUCCESS(f"Successfully regenerated chunks for {pdf_doc.title}"))
                
            except PDFDocument.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"PDF with ID {options['pdf_id']} not found"))
        
        elif options['all']:
            pdfs = PDFDocument.objects.all()
            self.stdout.write(f"Regenerating chunks for {pdfs.count()} PDFs")
            
            for pdf_doc in pdfs:
                self.stdout.write(f"Processing: {pdf_doc.title}")
                
                # Delete existing chunks
                PDFChunk.objects.filter(pdf_document=pdf_doc).delete()
                
                # Create new chunks
                create_pdf_chunks(pdf_doc)
            
            self.stdout.write(self.style.SUCCESS("Successfully regenerated chunks for all PDFs"))
        
        else:
            self.stdout.write(self.style.ERROR("Please specify --pdf-id or --all")) 