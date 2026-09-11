from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
import pymupdf as fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import os
from io import BytesIO
from fpdf import FPDF
from openai import OpenAI
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

class TranslatePDFRequestSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="PDF file to translate")
    source_language = serializers.CharField(help_text="Source language code (e.g., 'en')")
    target_language = serializers.CharField(help_text="Target language code (e.g., 'bn')")

class WatermarkPDFRequestSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="PDF file to watermark")
    text = serializers.CharField(help_text="Watermark text")
    position = serializers.CharField(help_text="Position (e.g., center, top-left, bottom-right)")
    opacity = serializers.FloatField(help_text="Opacity between 0.0 and 1.0")
    color = serializers.CharField(help_text="Color in hex format (e.g., #FF0000)")

# Register Bengali Font
FONT_PATH = os.path.join(settings.BASE_DIR, 'editor', 'fonts', 'Kalpurush.ttf')

class TranslatePDFView(APIView):
    @extend_schema(
        request={
            "multipart/form-data": TranslatePDFRequestSerializer
        },
        responses={
            (200, 'application/pdf'): OpenApiTypes.BINARY,
        },
        description="Translate a PDF file to another language. Returns a translated PDF file."
    )
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

            # 2. Translate text using OpenAI GPT
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            model = settings.OPENAI_MODEL

            # Language name map for clearer GPT prompts
            lang_names = {
                'en': 'English', 'bn': 'Bengali', 'ar': 'Arabic', 'fr': 'French',
                'de': 'German', 'es': 'Spanish', 'hi': 'Hindi', 'zh': 'Chinese',
                'ja': 'Japanese', 'ko': 'Korean', 'pt': 'Portuguese', 'ru': 'Russian',
            }
            src_name = lang_names.get(source_lang, source_lang)
            tgt_name = lang_names.get(target_lang, target_lang)

            translated_texts = []
            for text in extracted_texts:
                # Split into max 4000-char chunks
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        f"You are a professional translator. "
                                        f"Translate the following text from {src_name} to {tgt_name}. "
                                        f"Preserve the original formatting and line breaks as much as possible. "
                                        f"Only return the translated text, nothing else."
                                    )
                                },
                                {"role": "user", "content": chunk}
                            ],
                            temperature=0.3,
                        )
                        translated = response.choices[0].message.content.strip()
                        if translated:
                            translated_texts.append(translated)
                    except Exception as e:
                        # Fallback: keep original text if translation fails
                        translated_texts.append(chunk)


            # 3. Generate new PDF using fpdf2
            pdf = FPDF()
            pdf.add_page()
            
            # Setup font
            if target_lang == 'bn' and os.path.exists(FONT_PATH):
                pdf.add_font("Kalpurush", "", FONT_PATH)
                pdf.set_font("Kalpurush", size=12)
            else:
                pdf.set_font("Helvetica", size=12)
            
            # Enable text shaping for CTL scripts like Bengali (requires uharfbuzz)
            if hasattr(pdf, 'set_text_shaping'):
                pdf.set_text_shaping(True)

            for text in translated_texts:
                pdf.multi_cell(0, 8, text, align="L")
                pdf.ln(4)

            # Output to buffer
            buffer = BytesIO(pdf.output())
            buffer.seek(0)

            # 4. Return as downloadable file
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="translated_{target_lang}.pdf"'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WatermarkPDFView(APIView):
    @extend_schema(
        request={
            "multipart/form-data": WatermarkPDFRequestSerializer
        },
        responses={
            (200, 'application/pdf'): OpenApiTypes.BINARY,
        },
        description="Add a watermark to a PDF file. Returns the watermarked PDF file."
    )
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
