from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework.renderers import JSONRenderer

from .serializers import TranslatePDFRequestSerializer, WatermarkPDFRequestSerializer
from .renderers import PDFRenderer
from .services.pdf_translator import translate_pdf
from .services.pdf_watermark import watermark_pdf


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
            # Delegate to service layer
            buffer = translate_pdf(pdf_file.read(), source_lang, target_lang)

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
            "Upload a PDF file and configure the watermark settings.\n\n"
            "The API will stamp the watermark text on every page and return the watermarked PDF.\n\n"
            "**Position options:** center, top-left, top-center, top-right, bottom-left, bottom-center, bottom-right\n\n"
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
            # Delegate to service layer
            buffer = watermark_pdf(pdf_file, text, position, opacity, color_hex)

            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="watermarked.pdf"'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
