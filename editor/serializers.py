from rest_framework import serializers

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
