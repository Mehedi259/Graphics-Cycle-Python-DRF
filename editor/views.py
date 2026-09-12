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
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework.renderers import BaseRenderer, JSONRenderer

class PDFRenderer(BaseRenderer):
    media_type = 'application/pdf'
    format = 'pdf'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


LANGUAGE_HELP = (
    "Language code. Options: "
    "en (English), bn (Bengali), ar (Arabic), "
    "es (Spanish), fr (French), de (German), "
    "hi (Hindi), zh (Chinese), ja (Japanese), ko (Korean)"
)

POSITION_HELP = (
    "Watermark position. Options: "
    "center, top-left, top-center, top-right, "
    "bottom-left, bottom-center, bottom-right"
)

class TranslatePDFRequestSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Click 'Choose File' to upload a PDF document"
    )
    source_language = serializers.CharField(
        default='en',
        initial='en',
        help_text=LANGUAGE_HELP,
    )
    target_language = serializers.CharField(
        default='bn',
        initial='bn',
        help_text=LANGUAGE_HELP,
    )

class WatermarkPDFRequestSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Click 'Choose File' to upload a PDF document"
    )
    text = serializers.CharField(
        default='CONFIDENTIAL',
        initial='CONFIDENTIAL',
        help_text="Text to stamp on the PDF (e.g., CONFIDENTIAL, DRAFT, APPROVED)",
    )
    position = serializers.CharField(
        default='center',
        initial='center',
        help_text=POSITION_HELP,
    )
    opacity = serializers.FloatField(
        default=0.3,
        initial=0.3,
        min_value=0.0,
        max_value=1.0,
        help_text="Transparency level — 0.0 (invisible) to 1.0 (fully opaque). Default: 0.3",
    )
    color = serializers.CharField(
        default='#FF0000',
        initial='#FF0000',
        help_text="Watermark color in hex format (e.g., #FF0000 for red, #0000FF for blue)",
    )

# Register Bengali Font
FONT_PATH = os.path.join(settings.BASE_DIR, 'editor', 'fonts', 'Kalpurush.ttf')

class TranslatePDFView(APIView):
    renderer_classes = [JSONRenderer, PDFRenderer]

    @extend_schema(
        request={
            "multipart/form-data": TranslatePDFRequestSerializer
        },
        responses={
            (200, 'application/pdf'): OpenApiTypes.BINARY,
        },
        description=(
            "Upload a PDF file and specify source and target language codes.\n\n"
            "The API will extract text, translate it using AI (GPT-4o-mini), "
            "and return a translated PDF.\n\n"
            "**Language codes:** en, bn, ar, es, fr, de, hi, zh, ja, ko"
        ),
        examples=[
            OpenApiExample(
                'Bengali Translation',
                summary='Translate English PDF to Bengali',
                description='Standard example: translate an English document to Bengali',
                value={'source_language': 'en', 'target_language': 'bn'},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        pdf_file = request.FILES.get('file')
        source_lang = request.data.get('source_language')
        target_lang = request.data.get('target_language')

        if not all([pdf_file, source_lang, target_lang]):
            return Response({"error": "Missing required fields (file, source_language, target_language)."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the file is actually a PDF
        if not pdf_file.name.lower().endswith('.pdf'):
            return Response({"error": f"Invalid file type. Expected a PDF file, but got {pdf_file.name}"}, status=status.HTTP_400_BAD_REQUEST)

        if pdf_file.content_type not in ['application/pdf', 'application/x-pdf']:
            return Response({"error": f"Invalid content type: {pdf_file.content_type}. Please upload a valid PDF document."}, status=status.HTTP_400_BAD_REQUEST)

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
    renderer_classes = [JSONRenderer, PDFRenderer]

    @extend_schema(
        request={
            "multipart/form-data": WatermarkPDFRequestSerializer
        },
        responses={
            (200, 'application/pdf'): OpenApiTypes.BINARY,
        },
        description=(
            "Upload a PDF file and configure the watermark settings.\\n\\n"
            "The API will stamp the watermark text on every page and return the watermarked PDF.\\n\\n"
            "**Position options:** center, top-left, top-center, top-right, bottom-left, bottom-center, bottom-right\\n\\n"
            "**Color:** Use hex format — e.g., `#FF0000` (red), `#0000FF` (blue), `#808080` (gray)"
        ),
        examples=[
            OpenApiExample(
                'Confidential Watermark',
                summary='Add a red CONFIDENTIAL watermark to center',
                description='Standard example: stamp CONFIDENTIAL in red at center with 30% opacity',
                value={
                    'text': 'CONFIDENTIAL',
                    'position': 'center',
                    'opacity': 0.3,
                    'color': '#FF0000',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        pdf_file = request.FILES.get('file')
        text = request.data.get('text')
        position = request.data.get('position')
        opacity = request.data.get('opacity')
        color_hex = request.data.get('color')

        if not all([pdf_file, text, position, opacity, color_hex]):
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the file is actually a PDF
        if not pdf_file.name.lower().endswith('.pdf'):
            return Response({"error": f"Invalid file type. Expected a PDF file, but got {pdf_file.name}"}, status=status.HTTP_400_BAD_REQUEST)

        if pdf_file.content_type not in ['application/pdf', 'application/x-pdf']:
            return Response({"error": f"Invalid content type: {pdf_file.content_type}. Please upload a valid PDF document."}, status=status.HTTP_400_BAD_REQUEST)

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
