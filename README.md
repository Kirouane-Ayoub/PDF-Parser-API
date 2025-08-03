# PDF Processor API

A production-grade FastAPI service for processing PDF files, extracting page images, and transcribing their content using OpenAI-compatible multimodal models.

## Features

- Upload PDF files and extract each page as a high-quality image.
- Transcribe page images using OpenAI (or compatible) multimodal models.
- Returns structured Markdown output, including tables as Markdown.
- Batch processing with concurrency control.
- Health check and structured error responses.
- Configurable via `.env` file.

## Quickstart

### 1. Install dependencies

```sh
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your API keys and settings.

### 3. Run the API server

```sh
python -m uvicorn app.main:app --reload
```

### 4. Process a PDF

Use [`client_test.py`](client_test.py) to send a PDF to the API:

```sh
python client_test.py
```

## API Endpoints

- `POST /api/v1/process-pdf`
  Upload and process a PDF file.

- `GET /api/v1/health`
  Health check endpoint.

- `GET /api/v1/`
  API info.

## Configuration

All settings are managed via environment variables in `.env`. See `.env.example` for details.
