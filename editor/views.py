from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
import pymupdf as fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from deep_translator import GoogleTranslator
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from io import BytesIO

# Register Bengali Font
FONT_PATH = os.path.join(settings.BASE_DIR, 'editor', 'fonts', 'Kalpurush.ttf')
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Kalpurush', FONT_PATH))

class TranslatePDFView(APIView):
    def post(self, request, *args, **kwargs):
        pdf_file = request.FILES.get('file')
        source_lang = request.data.get('source_language')
        target_lang = request.data.get('target_language')

        if not all([pdf_file, source_lang, target_lang]):
            return Response({"error": "Missing required fields (file, source_language, target_language)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Extract text
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            extracted_texts = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    extracted_texts.append(text)

            # 2. Translate text
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_texts = []
            for text in extracted_texts:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    translated = translator.translate(chunk)
                    if translated:
                        translated_texts.append(translated)

            # 3. Generate new PDF
            buffer = BytesIO()
            pdf = SimpleDocTemplate(buffer)
            styles = getSampleStyleSheet()
            
            font_name = 'Kalpurush' if target_lang == 'bn' and os.path.exists(FONT_PATH) else 'Helvetica'
            
            custom_style = ParagraphStyle(
                name='Custom',
                fontName=font_name,
                fontSize=12,
                leading=16,
                wordWrap='CJK' if target_lang == 'bn' else None
            )

            story = []
            for text in translated_texts:
                p = Paragraph(text.replace('\n', '<br/>'), custom_style)
                story.append(p)
                story.append(Spacer(1, 12))

            pdf.build(story)
            buffer.seek(0)

            # 4. Return as downloadable file
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="translated_{target_lang}.pdf"'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WatermarkPDFView(APIView):
    def post(self, request, *args, **kwargs):
        pdf_file = request.FILES.get('file')
        text = request.data.get('text')
        position = request.data.get('position')
        opacity = request.data.get('opacity')
        color_hex = request.data.get('color')

        if not all([pdf_file, text, position, opacity, color_hex]):
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            opacity = float(opacity)
            color_hex = color_hex.lstrip('#')
            if len(color_hex) == 6:
                r, g, b = tuple(int(color_hex[i:i+2], 16)/255.0 for i in (0, 2, 4))
            else:
                r, g, b = 0.0, 0.0, 0.0 # fallback

            reader = PdfReader(pdf_file)
            writer = PdfWriter()

            for page in reader.pages:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)

                # Create watermark for this specific page size
                watermark_buffer = BytesIO()
                c = canvas.Canvas(watermark_buffer, pagesize=(width, height))
                c.setFont("Helvetica-Bold", 40)
                c.setFillColorRGB(r, g, b, alpha=opacity)
                
                text_width = c.stringWidth(text, "Helvetica-Bold", 40)
                
                # Default to center
                x = (width - text_width) / 2
                y = height / 2

                if position == 'top-left':
                    x, y = 50, height - 50
                elif position == 'top-center':
                    x, y = (width - text_width) / 2, height - 50
                elif position == 'top-right':
                    x, y = width - text_width - 50, height - 50
                elif position == 'bottom-left':
                    x, y = 50, 50
                elif position == 'bottom-center':
                    x, y = (width - text_width) / 2, 50
                elif position == 'bottom-right':
                    x, y = width - text_width - 50, 50

                c.drawString(x, y, text)
                c.save()
                watermark_buffer.seek(0)

                # Merge
                watermark_reader = PdfReader(watermark_buffer)
                watermark_page = watermark_reader.pages[0]
                page.merge_page(watermark_page)
                writer.add_page(page)

            output_buffer = BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)

            response = HttpResponse(output_buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="watermarked.pdf"'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
