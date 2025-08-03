import aiohttp
import asyncio
import time
from typing import Dict, Any, Optional
import base64

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.exceptions import APICallError
from app.models.schemas import ProcessingMetadata

logger = get_logger(__name__)


class OpenAIClient:
    """Handles OpenAI API integration."""

    def __init__(self):
        self.api_url = settings.openai_api_url
        self.api_key = settings.openai_api_key
        self.timeout = settings.openai_timeout
        self.mmlm_model = settings.mmlm_model
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    async def process_image(
        self, image_data: bytes, page_number: int, metadata: ProcessingMetadata
    ) -> tuple[Dict[str, Any], ProcessingMetadata]:
        """Send image to OpenAI API and return response."""

        async with self.semaphore:
            start_time = time.time()

            try:
                # Encode image as base64
                image_b64 = base64.b64encode(image_data).decode("utf-8")
                instruction = (
                    "Please extract and transcribe only the raw text content from the following page image. "
                    "Your response must be formatted in **Markdown**. "
                    "If the image contains tables, convert them into valid Markdown table format. "
                    "Do not add any extra commentary, explanation, or formatting beyond what is in the image."
                )
                # Prepare request payload
                payload = {
                    "model": self.mmlm_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": instruction},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    },
                                },
                            ],
                        }
                    ],
                    "max_tokens": 1000,
                }

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                # Make API request
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as session:
                    logger.info(
                        "sending_api_request", page_number=page_number, url=self.api_url
                    )

                    async with session.post(
                        self.api_url, json=payload, headers=headers
                    ) as response:
                        response_data = await response.json()

                        if response.status != 200:
                            error_msg = response_data.get("error", {}).get(
                                "message", "Unknown API error"
                            )
                            raise APICallError(
                                f"OpenAI API request failed: {error_msg}"
                            )

                        # Update metadata with API call info
                        api_processing_time = time.time() - start_time
                        updated_metadata = ProcessingMetadata(
                            confidence_score=metadata.confidence_score,
                            processing_time=metadata.processing_time
                            + api_processing_time,
                            image_dimensions=metadata.image_dimensions,
                            file_size=metadata.file_size,
                            additional_data={
                                **(metadata.additional_data or {}),
                                "api_processing_time": api_processing_time,
                                "api_response_tokens": response_data.get(
                                    "usage", {}
                                ).get("total_tokens", 0),
                            },
                        )

                        logger.info(
                            "api_request_successful",
                            page_number=page_number,
                            processing_time=api_processing_time,
                            tokens_used=response_data.get("usage", {}).get(
                                "total_tokens", 0
                            ),
                        )

                        return response_data, updated_metadata

            except asyncio.TimeoutError:
                raise APICallError(
                    f"API request timed out after {self.timeout} seconds"
                )
            except aiohttp.ClientError as e:
                raise APICallError(f"Network error during API request: {str(e)}")
            except Exception as e:
                logger.error(
                    "api_request_failed", page_number=page_number, error=str(e)
                )
                raise APICallError(f"Unexpected error during API request: {str(e)}")

    async def process_batch(
        self, pages_data: list[tuple[int, bytes, ProcessingMetadata]]
    ) -> list[tuple[int, Dict[str, Any], ProcessingMetadata, Optional[str]]]:
        """Process multiple pages concurrently."""

        logger.info("starting_batch_processing", total_pages=len(pages_data))

        # Create tasks for concurrent processing
        tasks = []
        for page_num, image_data, metadata in pages_data:
            task = self._process_single_page(page_num, image_data, metadata)
            tasks.append(task)

        # Process with controlled concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results and exceptions
        processed_results = []
        for i, result in enumerate(results):
            page_num = pages_data[i][0]

            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error(
                    "page_processing_failed", page_number=page_num, error=error_msg
                )
                processed_results.append((page_num, {}, pages_data[i][2], error_msg))
            else:
                processed_results.append((*result, None))

        logger.info("batch_processing_complete", total_pages=len(processed_results))
        return processed_results

    async def _process_single_page(
        self, page_num: int, image_data: bytes, metadata: ProcessingMetadata
    ) -> tuple[int, Dict[str, Any], ProcessingMetadata]:
        """Process a single page with error handling."""
        try:
            api_response, updated_metadata = await self.process_image(
                image_data, page_num, metadata
            )
            return page_num, api_response, updated_metadata
        except Exception as e:
            # Re-raise to be caught by gather
            raise e
