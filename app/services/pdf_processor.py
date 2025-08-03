import fitz  # PyMuPDF
import aiofiles
import tempfile
import os
from PIL import Image
from typing import List, Tuple, BinaryIO
from io import BytesIO
import time

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.exceptions import PDFProcessingError, InvalidFileError
from app.models.schemas import ProcessingMetadata

logger = get_logger(__name__)


class PDFProcessor:
    """Handles PDF parsing and image conversion."""

    def __init__(self):
        self.dpi = settings.image_dpi
        self.image_format = settings.image_format.upper()

    async def validate_pdf(self, file_content: bytes) -> None:
        """Validate PDF file."""
        if len(file_content) > settings.max_file_size:
            raise PDFProcessingError(
                f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )

        try:
            # Test if file can be opened as PDF
            doc = fitz.open(stream=file_content, filetype="pdf")
            if doc.page_count == 0:
                raise InvalidFileError("PDF file contains no pages")
            doc.close()
        except Exception as e:
            raise InvalidFileError(f"Invalid PDF file: {str(e)}")

    async def extract_pages_as_images(
        self, file_content: bytes
    ) -> List[Tuple[int, bytes, ProcessingMetadata]]:
        """Extract all pages from PDF as high-quality images."""
        start_time = time.time()

        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            pages_data = []

            logger.info("extracting_pdf_pages", total_pages=doc.page_count)

            # Process pages in batches to manage memory
            for page_num in range(doc.page_count):
                page_start = time.time()

                page = doc.load_page(page_num)

                # Create transformation matrix for high DPI
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)

                # Render page as pixmap
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convert to PIL Image for better compression
                img_data = pix.tobytes("png")
                pil_image = Image.open(BytesIO(img_data))

                # Optimize image
                output_buffer = BytesIO()
                pil_image.save(
                    output_buffer,
                    format=self.image_format,
                    optimize=True,
                    quality=95 if self.image_format == "JPEG" else None,
                )

                image_bytes = output_buffer.getvalue()

                # Create processing metadata
                metadata = ProcessingMetadata(
                    processing_time=time.time() - page_start,
                    image_dimensions=(pil_image.width, pil_image.height),
                    file_size=len(image_bytes),
                )

                pages_data.append((page_num + 1, image_bytes, metadata))

                # Clean up
                pix = None
                pil_image.close()
                output_buffer.close()

                logger.debug(
                    "page_extracted",
                    page_number=page_num + 1,
                    processing_time=metadata.processing_time,
                    image_size=len(image_bytes),
                )

            doc.close()

            total_time = time.time() - start_time
            logger.info(
                "pdf_extraction_complete",
                total_pages=len(pages_data),
                total_time=total_time,
            )

            return pages_data

        except Exception as e:
            logger.error("pdf_extraction_failed", error=str(e))
            raise PDFProcessingError(f"Failed to extract pages from PDF: {str(e)}")

    async def process_pdf_stream(
        self, file: BinaryIO
    ) -> List[Tuple[int, bytes, ProcessingMetadata]]:
        """Process PDF from file stream."""
        try:
            # Read file content
            content = await self._read_file_async(file)

            # Validate PDF
            await self.validate_pdf(content)

            # Extract pages
            return await self.extract_pages_as_images(content)

        except Exception as e:
            logger.error("pdf_stream_processing_failed", error=str(e))
            raise

    async def _read_file_async(self, file: BinaryIO) -> bytes:
        """Read file content asynchronously."""
        # Create temporary file to handle large uploads
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            try:
                # Read in chunks to handle large files
                chunk_size = 8192
                while chunk := file.read(chunk_size):
                    tmp_file.write(chunk)

                tmp_file.flush()

                # Read back the complete content
                async with aiofiles.open(tmp_file.name, "rb") as f:
                    content = await f.read()

                return content

            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass
