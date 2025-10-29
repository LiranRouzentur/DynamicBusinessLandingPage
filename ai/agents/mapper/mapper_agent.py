"""Mapper agent implementation based on mapper_agent_prompt_with_qa.md"""
import asyncio
from typing import Dict, Any, Optional
from pydantic import ValidationError
from agents.base_agent import BaseAgent, AgentError
from agents.mapper.mapper_prompt import MAPPER_SYSTEM_PROMPT
from agents.mapper.mapper_schemas import MapperOutput, MAPPER_RESPONSE_SCHEMA


class MapperAgent(BaseAgent):
    """Mapper agent - enriches Google Maps business data with web research"""
    
    def __init__(self, client, model: str = "gpt-4o", temperature: float = 0.7):
        super().__init__(client, model, temperature, agent_name="Mapper")
        self.max_retries = 3
    
    async def run(
        self,
        google_data: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Run mapper agent with QA/validator and self-healing loop
        
        Args:
            google_data: Google Maps business data (schema from markdown)
            retry_count: Current retry attempt
            
        Returns:
            Mapper output with business_summary, logo, images, colors, and QA report
        """
        user_message = {
            "google_data": google_data
        }
        
        try:
            result = await self._call_openai(
                system_prompt=MAPPER_SYSTEM_PROMPT,
                user_message=user_message,
                response_schema=MAPPER_RESPONSE_SCHEMA
            )
            
            # Validate output
            validated = MapperOutput.model_validate(result)
            output_dict = validated.model_dump()
            
            # Run QA checks (if QA report shows failures, retry)
            qa_report = output_dict.get("qa_report", {})
            
            if not qa_report.get("passed", True) and retry_count < self.max_retries:
                print(f"[Mapper] QA checks failed, retrying (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(min(2 ** retry_count, 5))  # Exponential backoff
                return await self.run(google_data, retry_count + 1)
            
            return output_dict
            
        except ValidationError as e:
            print(f"[Mapper] Validation error: {e}")
            if retry_count < self.max_retries:
                await asyncio.sleep(min(2 ** retry_count, 5))
                return await self.run(google_data, retry_count + 1)
            raise AgentError(f"Mapper validation failed after {self.max_retries} retries: {e}")
        except Exception as e:
            print(f"[Mapper] Error: {e}")
            raise AgentError(f"Mapper failed: {e}")


# Export for convenience
__all__ = ["MapperAgent"]

