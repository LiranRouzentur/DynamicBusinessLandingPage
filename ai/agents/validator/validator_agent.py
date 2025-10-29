"""Validator agent implementation based on validator_agent.md"""
import os
import gzip
from pathlib import Path
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentError
from agents.validator.validator_prompt import VALIDATOR_SYSTEM_PROMPT
from agents.validator.validator_schemas import ValidatorOutput, VALIDATOR_RESPONSE_SCHEMA


class ValidatorAgent(BaseAgent):
    """Validator agent - independent, strict final QA for generated bundle"""
    
    def __init__(self, client, model: str = "gpt-4o", temperature: float = 0.3):
        super().__init__(client, model, temperature, agent_name="Validator")
        # Lower temperature for more deterministic validation
    
    async def run(
        self,
        workdir: str,
        google_data: Dict[str, Any],
        mapper_data: Dict[str, Any],
        tier: str = "enhanced"
    ) -> Dict[str, Any]:
        """
        Validate generated bundle
        
        Args:
            workdir: Path to directory containing index.html, styles.css, script.js, /assets/...
            google_data: Original Google Maps data
            mapper_data: Mapper agent output
            tier: Interactivity tier expected
            
        Returns:
            Validator output with status, violations, and repair suggestions
        """
        # Read files from workdir
        workdir_path = Path(workdir)
        
        files_data = {}
        for filename in ["index.html", "styles.css", "script.js"]:
            filepath = workdir_path / filename
            if filepath.exists():
                files_data[filename] = filepath.read_text(encoding="utf-8")
            else:
                files_data[filename] = ""
        
        # List assets if directory exists
        assets_dir = workdir_path / "assets" / "images"
        assets_list = []
        if assets_dir.exists() and assets_dir.is_dir():
            assets_list = [f.name for f in assets_dir.iterdir() if f.is_file()]
        
        # Calculate metrics
        metrics = self._calculate_metrics(workdir_path, files_data)
        
        user_message = {
            "workdir": str(workdir),
            "files": files_data,
            "assets": assets_list,
            "google_data": google_data,
            "mapper_data": mapper_data,
            "tier": tier,
            "metrics": metrics
        }
        
        try:
            result = await self._call_openai(
                system_prompt=VALIDATOR_SYSTEM_PROMPT,
                user_message=user_message,
                response_schema=VALIDATOR_RESPONSE_SCHEMA
            )
            
            # Validate output
            validated = ValidatorOutput.model_validate(result)
            return validated.model_dump()
            
        except Exception as e:
            print(f"[Validator] Error: {e}")
            raise AgentError(f"Validator failed: {e}")
    
    def _calculate_metrics(self, workdir_path: Path, files_data: Dict[str, str]) -> Dict[str, Any]:
        """Calculate basic metrics for validation"""
        metrics = {}
        
        # Calculate JS gzip size
        if "script.js" in files_data:
            js_bytes = files_data["script.js"].encode("utf-8")
            js_gzip_bytes = gzip.compress(js_bytes)
            metrics["js_gzip_kb"] = round(len(js_gzip_bytes) / 1024.0, 2)
        
        # Calculate CSS size
        if "styles.css" in files_data:
            css_bytes = files_data["styles.css"].encode("utf-8")
            metrics["css_size_kb"] = round(len(css_bytes) / 1024.0, 2)
        
        # Count images
        assets_dir = workdir_path / "assets" / "images"
        image_count = 0
        total_image_weight_mb = 0.0
        
        if assets_dir.exists() and assets_dir.is_dir():
            for img_file in assets_dir.iterdir():
                if img_file.is_file():
                    image_count += 1
                    total_image_weight_mb += img_file.stat().st_size / (1024 * 1024)
        
        metrics["image_count"] = image_count
        metrics["total_image_weight_mb"] = round(total_image_weight_mb, 2)
        
        return metrics


# Export for convenience
__all__ = ["ValidatorAgent"]

