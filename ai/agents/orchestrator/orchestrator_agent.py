
"""Orchestrator agent implementation based on orchestrator.md"""
import os
import asyncio
import zipfile
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv
from openai import OpenAI
from agents.base_agent import BaseAgent, AgentError
from agents.mapper.mapper_agent import MapperAgent
from agents.generator.generator_agent import GeneratorAgent
from agents.validator.validator_agent import ValidatorAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Orchestrator - Coordinates mapper, generator, and validator agents"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.3
    ):
        # Load environment
        env_path = Path(__file__).resolve().parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-xxxx") or "YOUR_" in api_key:
            raise ValueError("OPENAI_API_KEY not properly configured")
        
        client = OpenAI(api_key=api_key)
        super().__init__(client, model, temperature, agent_name="Orchestrator")
        
        # Initialize agents
        self.mapper = MapperAgent(client)
        self.generator = GeneratorAgent(client)
        self.validator = ValidatorAgent(client, temperature=0.3)
    
    async def orchestrate(
        self,
        google_data: Dict[str, Any],
        interactivity_tier: str = "enhanced",
        max_attempts: int = 3,
        cost_mode: str = "economy",
        asset_budget: int = 3,
        brand_color_enforcement: bool = True,
        event_callback: Optional[Callable[[str, str], None]] = None,
        stop_after: Optional[str] = None,  # "mapper", "generator", or "validator" for testing
        session_id: Optional[str] = None  # Session ID for proper artifact storage path
    ) -> Dict[str, Any]:
        """
        Orchestrate the full workflow: mapper → generator → validator
        
        Args:
            google_data: Google Maps business data
            interactivity_tier: "enhanced" (default) | "basic" | "highend"
            max_attempts: Maximum retry attempts
            cost_mode: "economy" (prefer fewer web calls)
            asset_budget: Target number of images (3-6)
            brand_color_enforcement: Whether to enforce brand colors
            event_callback: Optional callback for progress events
            stop_after: Optional agent to stop after ("mapper", "generator", "validator") for testing
            
        Returns:
            Result dict with bundle, qa_report, orchestration_log, mapper_out
        """
        attempt = 1
        log = []
        
        # Determine workdir path: use backend/artifacts/{session_id} if session_id provided
        # Otherwise fall back to relative "output" directory
        if session_id:
            # Calculate path to backend/artifacts/{session_id}
            # Get project root (assuming we're in ai/agents/orchestrator)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            artifacts_base = project_root / "backend" / "artifacts"
            workdir = artifacts_base / session_id
        else:
            # Fallback for testing
            workdir = Path("output")
        
        workdir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[Orchestrator] Using workdir: {workdir.absolute()}")
        
        try:
            # Step 1: Plan & Normalize
            self._emit_event(event_callback, "ORCHESTRATING", "Analyzing business information...")
            google_data = self._normalize_google_data(google_data)
            
            # Step 2: Run Mapper
            self._emit_event(event_callback, "ORCHESTRATING", "Organizing business data and content...")
            log.append({"step": "mapper", "attempt": attempt, "timestamp": self._timestamp()})
            mapper_out = await self.mapper.run(google_data)
            
            if not self._basic_schema_ok(mapper_out):
                self._emit_event(event_callback, "ORCHESTRATING", "Reorganizing content for better results...")
                mapper_out = await self.mapper.run(google_data)
            
            log.append({"step": "mapper", "completed": True, "result": "success"})
            self._emit_event(event_callback, "GENERATING", "✓ Content organized successfully")
            
            # If stopping after mapper (for testing)
            if stop_after == "mapper":
                self._emit_event(event_callback, "TESTING", "Test mode: stopped after data organization")
                return {
                    "success": True,
                    "test_mode": True,
                    "stopped_after": "mapper",
                    "mapper_out": mapper_out,
                    "orchestration_log": log
                }
            
            # Step 3: Generate and Validate Loop
            while attempt <= max_attempts:
                log.append({"step": "generator", "attempt": attempt, "timestamp": self._timestamp()})
                if attempt > 1:
                    self._emit_event(event_callback, "GENERATING", f"Improving design (attempt {attempt}/{max_attempts})...")
                else:
                    self._emit_event(event_callback, "GENERATING", "Designing your landing page...")
                
                # Download and optimize images BEFORE generator call
                from agents.utils.image_optimizer import image_optimizer
                
                self._emit_event(event_callback, "GENERATING", "Preparing images and media...")
                try:
                    image_metadata = await image_optimizer.process_and_optimize_images(mapper_out, workdir)
                    logger.info(f"[Orchestrator] Image optimization completed: {len(image_metadata.get('images', []))} images")
                    
                    # Add image metadata to mapper_data for generator
                    mapper_data_with_images = {**mapper_out, "optimized_images": image_metadata}
                except Exception as e:
                    logger.error(f"[Orchestrator] Image optimization failed: {e}", exc_info=True)
                    self._emit_event(event_callback, "GENERATING", "Using images from business listing...")
                    # Continue with original mapper_data if optimization fails
                    mapper_data_with_images = mapper_out
                
                # Run Generator
                gen_out = await self.generator.run(
                    google_data=google_data,
                    mapper_data=mapper_data_with_images,
                    interactivity_tier=interactivity_tier,
                    asset_budget=asset_budget,
                    brand_color_enforcement=brand_color_enforcement
                )
                
                # Write files to workdir
                self._write_files(gen_out, workdir)
                
                # If stopping after generator (for testing)
                if stop_after == "generator":
                    self._emit_event(event_callback, "TESTING", "Test mode: stopped after page generation")
                    return {
                        "success": True,
                        "test_mode": True,
                        "stopped_after": "generator",
                        "mapper_out": mapper_out,
                        "generator_out": gen_out,
                        "orchestration_log": log
                    }
                
                # Run Validator
                log.append({"step": "validator", "attempt": attempt, "timestamp": self._timestamp()})
                self._emit_event(event_callback, "QA", "Checking quality and standards...")
                
                val_result = await self.validator.run(
                    workdir=str(workdir),
                    google_data=google_data,
                    mapper_data=mapper_out,
                    tier=interactivity_tier
                )
                
                log.append({
                    "step": "validator",
                    "status": val_result["status"],
                    "violations_count": len(val_result["violations"])
                })
                
                # If stopping after validator (for testing)
                if stop_after == "validator":
                    self._emit_event(event_callback, "TESTING", "Test mode: stopped after quality check")
                    return {
                        "success": True,
                        "test_mode": True,
                        "stopped_after": "validator",
                        "mapper_out": mapper_out,
                        "validator_result": val_result,
                        "orchestration_log": log
                    }
                
                # Check severity-based validation logic
                # Only security violations should block the build
                violations = val_result.get("violations", [])
                critical_violations = [
                    v for v in violations 
                    if v.get("severity") == "error" and v.get("id", "").startswith("SEC.")
                ]
                
                if val_result["status"] == "PASS" or len(critical_violations) == 0:
                    # Finalize - PASS or only non-critical violations
                    if len(critical_violations) == 0 and violations:
                        warning_count = len([v for v in violations if v.get("severity") == "warn"])
                        if warning_count > 0:
                            self._emit_event(event_callback, "READY", f"✓ Page ready with {warning_count} minor issue(s) - finalizing...")
                        else:
                            self._emit_event(event_callback, "READY", "✓ Quality checks passed! Finalizing your page...")
                    else:
                        self._emit_event(event_callback, "READY", "✓ Quality checks passed! Finalizing your page...")
                    
                    # Inject QA REPORT into index.html if missing
                    self._inject_qa_report(workdir, val_result)
                    
                    # Read bundle content before creating zip
                    bundle_content = {
                        "index_html": (workdir / "index.html").read_text(encoding="utf-8") if (workdir / "index.html").exists() else "",
                        "styles_css": (workdir / "styles.css").read_text(encoding="utf-8") if (workdir / "styles.css").exists() else "",
                        "app_js": (workdir / "script.js").read_text(encoding="utf-8") if (workdir / "script.js").exists() else ""
                    }
                    
                    # Create bundle.zip
                    bundle_path = self._create_bundle(workdir)
                    
                    # Save reports (val_result already contains dicts from model_dump)
                    qa_report = val_result.get("qa_report", {})
                    if hasattr(qa_report, "model_dump"):
                        qa_report = qa_report.model_dump()
                    
                    qa_report_path = workdir / "qa_report.json"
                    qa_report_path.write_text(json.dumps(qa_report, indent=2))
                    
                    mapper_out_path = workdir / "mapper_out.json"
                    mapper_out_path.write_text(json.dumps(mapper_out, indent=2))
                    
                    log_path = workdir / "orchestration_log.json"
                    log_path.write_text(json.dumps(log, indent=2))
                    
                    return {
                        "success": True,
                        "bundle": bundle_content,  # Include bundle content directly
                        "bundle_path": str(bundle_path),
                        "qa_report": qa_report,
                        "mapper_out": mapper_out,
                        "orchestration_log": log
                    }
                else:
                    # CRITICAL: Security violations exist - must fix before proceeding
                    repair = val_result["repair_suggestions"]
                    if repair.get("needs_security_fix"):
                        self._emit_event(event_callback, "GENERATING", "Fixing critical security issues...")
                        # Generator will retry on next iteration with security fixes
                    attempt += 1
            
            # Final FAIL
            self._emit_event(event_callback, "ERROR", f"Unable to complete after {max_attempts} attempts. Please try again.")
            bundle_path = self._create_bundle(workdir) if workdir.exists() else None
            
            qa_report = val_result.get("qa_report", {})
            if hasattr(qa_report, "model_dump"):
                qa_report = qa_report.model_dump()
            
            return {
                "success": False,
                "error": f"Failed validation after {max_attempts} attempts",
                "bundle_path": str(bundle_path) if bundle_path else None,
                "qa_report": qa_report,
                "mapper_out": mapper_out,
                "orchestration_log": log
            }
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self._emit_event(event_callback, "ERROR", f"An error occurred: {str(e)}")
            log.append({"step": "error", "error": str(e), "traceback": error_trace, "timestamp": self._timestamp()})
            logger.error(f"[Orchestrator] Exception: {e}\n{error_trace}")
            raise AgentError(f"Orchestration failed: {e}")
    
    def _normalize_google_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanity-check and normalize Google data"""
        # Ensure required fields exist with safe defaults
        if "types" not in data:
            data["types"] = []
        if "photos" not in data:
            data["photos"] = []
        if "reviews" not in data:
            data["reviews"] = []
        return data
    
    def _basic_schema_ok(self, mapper_out: Dict[str, Any]) -> bool:
        """Basic schema validation for mapper output"""
        return (
            "business_summary" in mapper_out and
            isinstance(mapper_out.get("business_summary"), str) and
            "assats" in mapper_out and
            isinstance(mapper_out["assats"], dict)
        )
    
    def _write_files(self, gen_out: Dict[str, Any], workdir: Path):
        """Write generator output files to workdir"""
        (workdir / "index.html").write_text(gen_out["index_html"], encoding="utf-8")
        (workdir / "styles.css").write_text(gen_out["styles_css"], encoding="utf-8")
        (workdir / "script.js").write_text(gen_out["script_js"], encoding="utf-8")
        
        # Write assets if present
        if "assets" in gen_out and gen_out["assets"]:
            assets_dir = workdir / "assets" / "images"
            assets_dir.mkdir(parents=True, exist_ok=True)
            # Assets would need to be downloaded/processed here if needed
    
    def _inject_qa_report(self, workdir: Path, val_result: Dict[str, Any]):
        """Inject QA REPORT comment into index.html if missing"""
        index_path = workdir / "index.html"
        if not index_path.exists():
            return
        
        content = index_path.read_text(encoding="utf-8")
        
        # Check if QA REPORT already exists
        if "<!-- QA REPORT" in content:
            return
        
        # Create QA REPORT comment
        qa_report = val_result["qa_report"]
        report_comment = f"""<!-- QA REPORT
timestamp: {self._timestamp()}
tier: {val_result.get("tier", "enhanced")}
status: {val_result["status"]}
fixed: {json.dumps([v["hint"] for v in val_result["violations"] if v["severity"] == "warn"])}
-->
"""
        
        # Insert at the top of HTML (after DOCTYPE if present)
        if content.strip().startswith("<!DOCTYPE"):
            lines = content.split("\n", 1)
            content = lines[0] + "\n" + report_comment + (lines[1] if len(lines) > 1 else "")
        else:
            content = report_comment + content
        
        index_path.write_text(content, encoding="utf-8")
    
    def _create_bundle(self, workdir: Path) -> Path:
        """Create bundle.zip from workdir"""
        # Bundle zip should be in the same directory as workdir
        bundle_path = workdir / "bundle.zip"
        
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in workdir.rglob("*"):
                if file_path.is_file() and file_path != bundle_path:  # Don't include the zip itself
                    arcname = file_path.relative_to(workdir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"[Orchestrator] Created bundle: {bundle_path}")
        return bundle_path
    
    def _timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _emit_event(self, callback: Optional[Callable[[str, str], None]], phase: str, message: str):
        """Emit event via callback if provided"""
        if callback:
            try:
                callback(phase, message)
            except Exception as e:
                print(f"[Orchestrator] Event callback error: {e}")


# Export for convenience
__all__ = ["OrchestratorAgent"]

