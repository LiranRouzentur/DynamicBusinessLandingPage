"""Generator agent implementation based on landing-page-agent-with-qa.md"""
import asyncio
from typing import Dict, Any
from pydantic import ValidationError
from agents.base_agent import BaseAgent, AgentError
from agents.generator.generator_prompt import GENERATOR_SYSTEM_PROMPT
from agents.generator.generator_schemas import GeneratorOutput, GENERATOR_RESPONSE_SCHEMA


class GeneratorAgent(BaseAgent):
    """Generator agent - produces static site files with QA/validation loop"""
    
    def __init__(self, client, model: str = "gpt-4o", temperature: float = 0.7):
        super().__init__(client, model, temperature, agent_name="Generator")
        self.max_retries = 3
    
    async def run(
        self,
        google_data: Dict[str, Any],
        mapper_data: Dict[str, Any],
        interactivity_tier: str = "enhanced",
        asset_budget: int = 3,
        brand_color_enforcement: bool = True,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Generate static landing page with QA/validation loop
        
        Args:
            google_data: Original Google Maps data
            mapper_data: Enriched data from mapper agent
            interactivity_tier: "basic" | "enhanced" (default) | "highend"
            asset_budget: Target number of images (3-6)
            brand_color_enforcement: Whether to enforce brand colors
            retry_count: Current retry attempt
            
        Returns:
            Generated bundle with index.html, styles.css, script.js, assets
        """
        user_message = {
            "google_data": google_data,
            "mapper_data": mapper_data,
            "interactivity_tier": interactivity_tier,
            "asset_budget": asset_budget,
            "brand_color_enforcement": brand_color_enforcement
        }
        
        try:
            result = await self._call_openai(
                system_prompt=GENERATOR_SYSTEM_PROMPT,
                user_message=user_message,
                response_schema=GENERATOR_RESPONSE_SCHEMA
            )
            
            # Validate output
            validated = GeneratorOutput.model_validate(result)
            output_dict = validated.model_dump()
            
            # Check QA report if present
            qa_report = output_dict.get("qa_report", {})
            
            if isinstance(qa_report, dict) and not qa_report.get("passed", True) and retry_count < self.max_retries:
                print(f"[Generator] QA checks failed, retrying (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(min(2 ** retry_count, 5))
                return await self.run(
                    google_data, mapper_data, interactivity_tier, 
                    asset_budget, brand_color_enforcement, retry_count + 1
                )
            
            return output_dict
            
        except ValidationError as e:
            print(f"[Generator] Validation error: {e}")
            if retry_count < self.max_retries:
                await asyncio.sleep(min(2 ** retry_count, 5))
                return await self.run(
                    google_data, mapper_data, interactivity_tier,
                    asset_budget, brand_color_enforcement, retry_count + 1
                )
            raise AgentError(f"Generator validation failed after {self.max_retries} retries: {e}")
        except Exception as e:
            print(f"[Generator] Error: {e}")
            raise AgentError(f"Generator failed: {e}")


# Export for convenience
__all__ = ["GeneratorAgent"]

