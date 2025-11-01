"""Mapper agent implementation based on mapper_agent_prompt_with_qa.md"""
import asyncio
import logging
from typing import Dict, Any, Optional
from pydantic import ValidationError
from app.base_agent import BaseAgent, AgentError
from app.mapper.mapper_prompt import MAPPER_SYSTEM_PROMPT
from app.mapper.mapper_schemas import MapperOutput, MAPPER_RESPONSE_SCHEMA

logger = logging.getLogger(__name__)


class MapperAgent(BaseAgent):
    """Mapper agent - enriches Google Maps business data with web research"""
    
    # Initializes mapper with OpenAI client and retry config (max 3 attempts with backoff).
    # Extracts business summary, logo, images, colors from Google data enriched with AI reasoning.
    def __init__(self, client, model: str = "gpt-4.1", temperature: float = 0.7):
        super().__init__(client, model, temperature, agent_name="Mapper")
        self.max_retries = 3
    
    # Runs mapper with self-healing retry loop (up to 3 attempts with exponential backoff).
    # Uses Responses API with stateful context for token savings; validates output with Pydantic + QA checks.
    async def run(
        self,
        google_data: Dict[str, Any],
        retry_count: int = 0,
        session_id: Optional[str] = None  # NEW: Session ID for stateful context tracking
    ) -> Dict[str, Any]:
        """
        Run mapper agent with QA/validator and self-healing loop
        
        Args:
            google_data: Google Maps business data (schema from markdown)
            retry_count: Current retry attempt
            
        Returns:
            Mapper output with business_summary, logo, images, colors, and QA report
        """
        business_name = google_data.get("name", "N/A")
        place_id = google_data.get("place_id", "N/A")
        
        logger.info(
            f"[Mapper] Starting data enrichment | "
            f"business_name: {business_name} | "
            f"place_id: {place_id} | "
            f"retry_count: {retry_count} | "
            f"max_retries: {self.max_retries}"
        )
        
        try:
            # Determine if this is a retry
            from app.base_agent import USE_RESPONSES_API
            is_retry = retry_count > 0
            cache_key = f"mapper_{session_id}" if session_id else None
            
            # Get previous response_id if retrying
            previous_response_id = None
            if USE_RESPONSES_API and is_retry and cache_key:
                previous_response_id = self.response_id_cache.get(cache_key)
            
            if USE_RESPONSES_API and previous_response_id:
                # RETRY with stateful context
                logger.info(
                    f"[Mapper] Using Responses API for retry | "
                    f"previous_response_id: {previous_response_id[:20]}... | "
                    f"retry_count: {retry_count}"
                )
                
                # Minimal payload for retry
                user_message = {
                    "note": "Please retry with corrected output. QA checks failed on previous attempt."
                }
                
                result, _ = await self._call_responses_api(
                    system_prompt=MAPPER_SYSTEM_PROMPT,
                    user_message=user_message,
                    response_schema=MAPPER_RESPONSE_SCHEMA,
                    previous_response_id=previous_response_id,
                    is_retry=True,
                    cache_key=cache_key,
                )
            else:
                # FIRST ATTEMPT or fallback
                user_message = {
                    "google_data": google_data
                }
                
                if USE_RESPONSES_API:
                    result, _ = await self._call_responses_api(
                        system_prompt=MAPPER_SYSTEM_PROMPT,
                        user_message=user_message,
                        response_schema=MAPPER_RESPONSE_SCHEMA,
                        cache_key=cache_key,
                    )
                else:
                    result = await self._call_openai(
                        system_prompt=MAPPER_SYSTEM_PROMPT,
                        user_message=user_message,
                        response_schema=MAPPER_RESPONSE_SCHEMA
                    )
            
            # Validate output
            try:
                validated = MapperOutput.model_validate(result)
                output_dict = validated.model_dump()
                
                # Extract key info for logging
                business_summary = output_dict.get("business_summary", "N/A")
                logo_url = output_dict.get("assats", {}).get("logo_url")
                # Some providers may explicitly return null for arrays; coalesce to []
                assats = output_dict.get("assats", {}) or {}
                business_images_list = assats.get("business_images_urls") or []
                stock_images_list = assats.get("stock_images_urls") or []
                business_images = len(business_images_list)
                stock_images = len(stock_images_list)
                
                logger.info(
                    f"[Mapper] ✓ Mapping completed successfully | "
                    f"business_summary_length: {len(business_summary)} chars | "
                    f"logo_url: {'✓' if logo_url else '✗'} | "
                    f"business_images: {business_images} | "
                    f"stock_images: {stock_images} | "
                    f"retry_count: {retry_count}"
                )
                
                # Run QA checks (if QA report shows failures, retry)
                qa_report = output_dict.get("qa_report") or {}  # Handle None properly
                qa_passed = qa_report.get("passed", True)
                
                if not qa_passed and retry_count < self.max_retries:
                    backoff_seconds = min(2 ** retry_count, 5)
                    logger.warning(
                        f"[Mapper] ✗ QA checks failed, retrying | "
                        f"attempt: {retry_count + 1}/{self.max_retries} | "
                        f"backoff: {backoff_seconds}s | "
                        f"qa_report: {qa_report}"
                    )
                    await asyncio.sleep(backoff_seconds)
                    return await self.run(google_data, retry_count + 1, session_id)
                
                if qa_passed:
                    logger.info(f"[Mapper] ✓ QA checks passed")
                else:
                    logger.warning(f"[Mapper] QA checks failed but max retries reached, proceeding")
                
                return output_dict
                
            except ValidationError as validation_err:
                error_details = str(validation_err)
                logger.warning(
                    f"[Mapper] ✗ Validation error | "
                    f"retry_count: {retry_count} | "
                    f"error: {error_details[:200]} | "
                    f"response_keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                )
                
                if retry_count < self.max_retries:
                    backoff_seconds = min(2 ** retry_count, 5)
                    logger.info(f"[Mapper] Retrying after {backoff_seconds}s (attempt {retry_count + 1}/{self.max_retries})")
                    await asyncio.sleep(backoff_seconds)
                    return await self.run(google_data, retry_count + 1, session_id)
                
                logger.error(
                    f"[Mapper] ✗ Validation failed after {self.max_retries} retries | "
                    f"final_error: {error_details}"
                )
                raise AgentError(f"Mapper validation failed after {self.max_retries} retries: {validation_err}")
            
        except AgentError:
            # Re-raise AgentError (already logged)
            raise
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"[Mapper] ✗ Mapping failed with unexpected error | "
                f"business_name: {business_name} | "
                f"error_type: {error_type} | "
                f"error: {str(e)} | "
                f"retry_count: {retry_count}",
                exc_info=True
            )
            raise AgentError(f"Mapper failed: {e}")


# Export for convenience
__all__ = ["MapperAgent"]

