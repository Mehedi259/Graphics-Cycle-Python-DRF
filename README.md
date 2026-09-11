# PDF Editor APIs - Backend & Frontend

This repository contains the backend and frontend solutions for the PDF Editor APIs assignment.

## 1. Backend Setup (Django DRF)

The backend exposes two main API endpoints for PDF editing:
- `POST /api/translate-pdf`: Extracts text, translates it, and rebuilds a PDF.
- `POST /editor/pdf/watermark`: Adds a customizable text watermark to a PDF.

### Requirements
- Python 3.10+
- `pip`

### Installation Steps
1. Navigate to the backend directory:
   ```bash
   cd /path/to/Graphics-Cycle-Python-DRF
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```bash
   python manage.py runserver
   ```
   The APIs will be available at `http://127.0.0.1:8000`.

### Testing via Postman
You can use the provided endpoints as follows:

**API A: Translate PDF**
- **URL:** `http://127.0.0.1:8000/api/translate-pdf`
- **Method:** `POST`
- **Body (form-data):**
  - `file`: (File) The source PDF.
  - `source_language`: (Text) e.g., "en"
  - `target_language`: (Text) e.g., "bn"

**API B: Watermark PDF**
- **URL:** `http://127.0.0.1:8000/editor/pdf/watermark`
- **Method:** `POST`
- **Body (form-data):**
  - `file`: (File) The source PDF.
  - `text`: (Text) e.g., "CONFIDENTIAL"
  - `position`: (Text) one of: `top-left`, `top-center`, `top-right`, `center`, `bottom-left`, `bottom-center`, `bottom-right`
  - `opacity`: (Text) e.g., "0.5"
  - `color`: (Text) e.g., "#FF0000"

---

## 2. Frontend Setup (Flutter)

The Flutter app provides a user interface to interact with the Django APIs.

### Installation Steps
1. Navigate to the flutter app directory:
   ```bash
   cd /path/to/Graphics-Cycle-flutter
   ```
2. Get packages:
   ```bash
   flutter pub get
   ```
3. Run the app on an emulator/simulator or physical device:
   ```bash
   flutter run
   ```
   *Note: If running on Android emulator, change `127.0.0.1` to `10.0.2.2` in `lib/api_service.dart`.*

---

## 3. Design Choices & Write-up

### Libraries Used
- **Backend:**
  - `PyMuPDF` (`pymupdf`): Chosen for its speed and accuracy in extracting text from PDFs compared to PyPDF2.
  - `deep-translator`: A reliable wrapper for Google Translate API that does not require an API key for basic translations.
  - `reportlab`: Excellent for generating PDFs from scratch. It allows manual embedding of TTF fonts which is critical for complex scripts like Bengali.
  - `PyPDF2`: Used primarily for merging the watermark overlay onto the existing PDF pages.
- **Frontend:**
  - `file_picker`: Standard library for picking local files across platforms.
  - `http`: To handle `multipart/form-data` requests seamlessly.
  - `open_filex` & `path_provider`: Used to save the API response (PDF file) locally and open it immediately for the user.

### Handling Bangla Unicode Text
Rendering Bangla in PDFs is notoriously tricky because standard PDF fonts (like Helvetica) do not support the Bengali script. 
To solve this:
1. We downloaded a standard Bengali TrueType font (`Kalpurush.ttf`) and placed it in the `editor/fonts` directory.
2. We used `reportlab.pdfbase.pdfmetrics.registerFont` to load the font.
3. When rebuilding the translated PDF, if the target language is `bn` (Bangla), the `ParagraphStyle` explicitly uses the `Kalpurush` font. We also enabled `wordWrap='CJK'` to help `reportlab` manage wrapping for non-Latin characters.

### Known Limitations
- The Deep Translator API has a character limit per request (usually ~5000 characters). We chunk the extracted text into blocks of 4000 characters before translating. However, splitting text blindly might break sentences across chunks.
- Rebuilding a PDF solely through text extraction loses the original formatting, images, and layout. The resulting translated PDF is a continuous document of translated text. Rebuilding a PDF exactly with original layout + translated text requires complex coordinate mapping and layout recreation, which is beyond the scope of a basic REST API implementation.
