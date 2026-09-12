from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

def watermark_pdf(pdf_stream, text, position, opacity, color_hex):
    """
    Adds a watermark to a PDF document and returns the watermarked PDF buffer.
    """
    opacity = float(opacity)
    color_hex = color_hex.lstrip('#')
    if len(color_hex) == 6:
        r, g, b = tuple(int(color_hex[i:i+2], 16)/255.0 for i in (0, 2, 4))
    else:
        r, g, b = 0.0, 0.0, 0.0 # fallback

    reader = PdfReader(pdf_stream)
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
    
    return output_buffer
