from django.urls import path
from .views import TranslatePDFView, WatermarkPDFView

urlpatterns = [
    path('api/translate-pdf', TranslatePDFView.as_view(), name='translate-pdf'),
    path('editor/pdf/watermark', WatermarkPDFView.as_view(), name='watermark-pdf'),
]
