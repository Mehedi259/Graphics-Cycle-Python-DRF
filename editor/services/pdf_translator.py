import os
from io import BytesIO
import pymupdf as fitz
from fpdf import FPDF
from openai import OpenAI
from django.conf import settings

FONT_PATH = os.path.join(settings.BASE_DIR, 'editor', 'fonts', 'Kalpurush.ttf')

def translate_pdf(pdf_stream, source_lang, target_lang):
    """
    Extracts text from PDF, translates it using OpenAI, and returns a translated PDF buffer.
    """
    # 1. Extract text
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    extracted_texts = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            extracted_texts.append(text)

    # 2. Translate text using OpenAI GPT
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

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
    
    return buffer
