"""Orchestrator agent implementation based on orchestrator.md"""
import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv
from openai import OpenAI
from app.base_agent import BaseAgent, AgentError
from app.mapper.mapper_agent import MapperAgent
from app.generator.generator_agent import GeneratorAgent
from app.generator.generator_prompt import GENERATOR_SYSTEM_PROMPT
from app.generator.generator_schemas import GENERATOR_RESPONSE_SCHEMA
from app.core.pre_write_validator import validate_generator_output_structure
from app.core.iframe_validator import validate_in_iframe
from app.config.generator_config import (
    MAX_GENERATOR_ATTEMPTS,
    get_retry_config,
    format_errors_by_severity,
    should_continue_retrying,
    ErrorSeverity
)
# Note: ValidatorAgent completely removed - never used, was dead code (~500 lines deleted)
import sys
# Add agents directory to path to import mcp_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_client import MCPClient

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Orchestrator - Coordinates mapper, generator, and validator agents"""
    
    # Initializes orchestrator with OpenAI client and creates mapper + generator agent instances.
    # Temperature=0.3 for deterministic orchestration decisions; loads API key from environment.
    # SPDX-License-Identifier: Proprietary
    # Copyright © 2025 Liran Rouzentur. All rights reserved.
    # כל הזכויות שמורות © 2025 לירן רויזנטור.
    # קוד זה הינו קנייני וסודי. אין להעתיק, לערוך, להפיץ או לעשות בו שימוש ללא אישור מפורש.
    # © 2025 Лиран Ройзентур. Все права защищены.
    # Этот программный код является собственностью владельца.
    # Запрещается копирование, изменение, распространение или использование без явного разрешения.
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1",
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
        # Note: Validation handled by pre_write_validator (security) and MCP (structure)
        # LLM-based semantic validation removed - was never used
    
    # Coordinates full build workflow: mapper → generator → iframe + MCP validators (parallel).
    # Uses retry loop with severity-based decisions and visual feedback refinement; returns HTML + meta.
    async def orchestrate(
        self,
        google_data: Dict[str, Any],
        interactivity_tier: str = "enhanced",
        max_attempts: int = MAX_GENERATOR_ATTEMPTS,  # Now 3 attempts with severity-based retry
        cost_mode: str = "economy",
        asset_budget: int = 3,
        event_callback: Optional[Callable[[str, str], None]] = None,
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
            event_callback: Optional callback for progress events
            session_id: Session ID for proper artifact storage path
            
        Returns:
            Result dict with bundle, qa_report, orchestration_log, mapper_out
        """
        attempt = 1
        log = []
        # Initialize optional validator result placeholder
        val_result = None
        
        # Determine workdir path: use backend/artifacts/{session_id} if session_id provided
        # Otherwise fall back to relative "output" directory
        if session_id:
            # Calculate path to backend/artifacts/{session_id}
            # Get project root (assuming we're in agents/app/orchestrator)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            artifacts_base = project_root / "backend" / "artifacts"
            workdir = artifacts_base / session_id
        else:
            # Fallback for testing
            workdir = Path("output")
        
        workdir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[Orchestrator] Using workdir: {workdir.absolute()}")
        
        # Initialize MCP client for side-effects (connects to standalone TCP server)
        # CRITICAL: MCP server uses WORKSPACE_ROOT env var (global), but we write to per-session workdir
        # We must sync files to MCP workspace OR ensure MCP uses the same workspace
        # For now, we'll write files to MCP workspace via write_files after writing to workdir
        mcp_client = MCPClient(workspace_root=workdir)
        
        try:
            # Step 1: Plan & Normalize
            self._emit_event(event_callback, "ORCHESTRATING", "Understanding your brand and vision...")
            google_data = self._normalize_google_data(google_data)
            
            # Step 2: Run Mapper
            try:
                business_name = google_data.get("name", "Business")
                self._emit_event(event_callback, "ORCHESTRATING", f"Researching {business_name} to gather authentic content...")
                log.append({"step": "mapper", "attempt": attempt, "timestamp": self._timestamp()})
                logger.info(
                    f"[Orchestrator] Running mapper | "
                    f"business_name: {google_data.get('name', 'N/A')} | "
                    f"place_id: {google_data.get('place_id', 'N/A')}"
                )
                
                mapper_out = await self.mapper.run(google_data, session_id=session_id)
                
                if not self._basic_schema_ok(mapper_out):
                    logger.warning(
                        f"[Orchestrator] ✗ Mapper output schema invalid, retrying | "
                        f"missing_fields: {[k for k in ['business_summary', 'assats'] if k not in mapper_out]}"
                    )
                    self._emit_event(event_callback, "ORCHESTRATING", "Reorganizing content for better results...")
                    mapper_out = await self.mapper.run(google_data, session_id=session_id)
                
                if not self._basic_schema_ok(mapper_out):
                    raise AgentError("Mapper output failed schema validation after retry")
                
                log.append({"step": "mapper", "completed": True, "result": "success"})
                logger.info(
                    f"[Orchestrator] ✓ Mapper completed successfully | "
                    f"business_summary: {len(mapper_out.get('business_summary', ''))} chars | "
                    f"has_logo: {bool(mapper_out.get('assats', {}).get('logo_url'))}"
                )
                # Announce brand readiness - user-friendly message (no technical details)
                self._emit_event(event_callback, "GENERATING", "✓ Brand identity and content ready — now designing...")
                
            except AgentError as mapper_err:
                logger.error(
                    f"[Orchestrator] ✗ Mapper failed | "
                    f"error: {str(mapper_err)} | "
                    f"business_name: {google_data.get('name', 'N/A')}"
                )
                raise
            except Exception as mapper_err:
                logger.error(
                    f"[Orchestrator] ✗ Mapper failed with unexpected error | "
                    f"error_type: {type(mapper_err).__name__} | "
                    f"error: {str(mapper_err)}",
                    exc_info=True
                )
                raise AgentError(f"Mapper failed: {mapper_err}")
            
            # Step 3: Generate and Validate Loop
            tamplate: Optional[str] = None
            validator_errors: Optional[list] = None
            generator_response_id: Optional[str] = None  # NEW: Track response_id for stateful context
            while attempt <= max_attempts:
                final_attempt = (attempt == max_attempts)
                log.append({"step": "generator", "attempt": attempt, "timestamp": self._timestamp()})
                # Dynamic, attempt-specific messages for storytelling
                mapper_data = mapper_out if mapper_out else {}
                if attempt == 1:
                    # First attempt - creative design phase
                    style_keyword = mapper_data.get("design_style_keyword", "modern")
                    self._emit_event(event_callback, "GENERATING", f"Crafting a stunning {style_keyword} design with premium typography and spacing...")
                elif attempt == 2:
                    # Second attempt - refinement based on feedback
                    self._emit_event(event_callback, "GENERATING", "Polishing the design — perfecting colors, spacing, and visual hierarchy...")
                else:
                    # Third+ attempt - final touches
                    self._emit_event(event_callback, "GENERATING", f"Final touches (attempt {attempt}/{max_attempts}) — ensuring every detail is pixel-perfect...")
                
                # Run Generator FIRST - generator will use image URLs from mapper_data
                # Images will be downloaded AFTER files are written (non-blocking)
                try:
                    logger.info(
                        f"[Orchestrator] Running generator | "
                        f"attempt: {attempt}/{max_attempts} | "
                        f"final_attempt: {final_attempt} | "
                        f"tier: {interactivity_tier} | "
                        f"previous_response_id: {'Yes' if generator_response_id else 'No'} | "
                        f"session_id: {session_id}"
                    )
                    # Force flush logs
                    for handler in logging.root.handlers:
                        handler.flush()
                    
                    # PHASE 2: Use Responses API with stateful context for MCP retries
                    from app.base_agent import USE_RESPONSES_API
                    
                    if USE_RESPONSES_API and generator_response_id:
                        # RETRY with stateful context (MCP validation retry)
                        # Use dynamic model/temperature based on attempt number
                        retry_config = get_retry_config(attempt)
                        
                        logger.info(
                            f"[Orchestrator] Using Responses API for retry | "
                            f"attempt: {attempt}/{max_attempts} | "
                            f"model: {retry_config['model']} | "
                            f"temperature: {retry_config['temperature']} | "
                            f"previous_response_id: {generator_response_id[:20]}... | "
                            f"errors_count: {len(validator_errors or [])} | "
                            f"Expected token savings: ~80-90%"
                        )
                        
                        # Minimal payload - only validator errors
                        result, generator_response_id = await self.generator._call_responses_api(
                            system_prompt=GENERATOR_SYSTEM_PROMPT,
                            user_message={"validator_errors": validator_errors or []},
                            response_schema=GENERATOR_RESPONSE_SCHEMA,
                            temperature=retry_config['temperature'],
                            max_tokens=retry_config['max_output_tokens'],
                            previous_response_id=generator_response_id,
                            is_retry=True,
                            cache_key=f"generator_{session_id}" if session_id else None,
                            top_p=retry_config['top_p'],
                        )
                        
                        # Validate result with Pydantic and run QA checks
                        from app.generator.generator_schemas import GeneratorOutput
                        from app.generator.generator_agent import qa_html_css, explain_qa_error
                        
                        validated = GeneratorOutput.model_validate(result)
                        gen_out = validated.model_dump()
                        
                        # Run QA checks on the retry output (same as generator does)
                        html_content = gen_out.get("html", "")
                        qa_errors = qa_html_css(html_content)
                        if qa_errors:
                            logger.warning(
                                f"[Orchestrator] QA issues detected in retry output: {len(qa_errors)} | "
                                f"errors: {qa_errors}"
                            )
                            gen_out["_qa_errors"] = [explain_qa_error(err) for err in qa_errors]
                    else:
                        # FIRST ATTEMPT or fallback - use normal generator.run()
                        gen_out = await self.generator.run(
                            google_data=google_data,
                            mapper_data=mapper_out,
                            tamplate=tamplate,
                            validator_errors=validator_errors,
                            interactivity_tier=interactivity_tier,
                            asset_budget=asset_budget,
                            final_attempt=final_attempt,
                            session_id=session_id
                        )
                        
                        # Capture response_id if Responses API is enabled
                        if USE_RESPONSES_API and hasattr(self.generator, 'response_id_cache'):
                            # Try to get response_id from cache (generator may have stored it)
                            cache_key = f"generator_{session_id}" if session_id else None
                            if cache_key and cache_key in self.generator.response_id_cache:
                                generator_response_id = self.generator.response_id_cache[cache_key]
                    
                    logger.info(
                        f"[Orchestrator] ✓ Generator completed | "
                        f"has_html: {bool(gen_out.get('html'))} | "
                        f"has_meta: {bool(gen_out.get('meta'))} | "
                        f"response_id: {generator_response_id[:20] if generator_response_id else 'None'}..."
                    )
                    
                except AgentError as gen_err:
                    logger.error(
                        f"[Orchestrator] ✗ Generator failed | "
                        f"attempt: {attempt}/{max_attempts} | "
                        f"error: {str(gen_err)}"
                    )
                    if attempt < max_attempts:
                        self._emit_event(event_callback, "GENERATING", "Fixing generation issues...")
                        attempt += 1
                        continue
                    else:
                        raise
                except Exception as gen_err:
                    logger.error(
                        f"[Orchestrator] ✗ Generator failed with unexpected error | "
                        f"attempt: {attempt}/{max_attempts} | "
                        f"error_type: {type(gen_err).__name__} | "
                        f"error: {str(gen_err)}",
                        exc_info=True
                    )
                    if attempt < max_attempts:
                        attempt += 1
                        continue
                    else:
                        raise AgentError(f"Generator failed: {gen_err}")
                
                # Pre-write validation: check structure before file I/O
                # Also check for any remaining QA errors from generator
                # Initialize error collection for batching
                all_pre_validation_errors = []
                
                try:
                    is_valid, structure_errors = validate_generator_output_structure(gen_out, mapper_out)
                    
                    # Check if generator returned any unresolved QA errors
                    qa_errors_from_gen = gen_out.get("_qa_errors", [])
                    
                    # Collect ALL pre-write/QA errors together
                    if not is_valid:
                        all_pre_validation_errors.extend([
                            self._format_error_for_generator("pre_write", e) 
                            for e in structure_errors
                        ])
                    if qa_errors_from_gen:
                        all_pre_validation_errors.extend(qa_errors_from_gen)
                    
                    if all_pre_validation_errors:
                        error_msg = f"Pre-validation failed with {len(all_pre_validation_errors)} error(s)"
                        logger.warning(
                            f"[Orchestrator] {error_msg} | "
                            f"Will be batched with MCP errors for single retry"
                        )
                    
                    # Continue to MCP validation - errors will be batched there
                    
                    logger.debug(f"[Orchestrator] ✓ Pre-write validation passed (or errors will be batched)")
                    
                except AgentError:
                    raise
                except Exception as validation_err:
                    logger.error(
                        f"[Orchestrator] ✗ Pre-write validation check failed | "
                        f"error_type: {type(validation_err).__name__} | "
                        f"error: {str(validation_err)}",
                        exc_info=True
                    )
                    raise AgentError(f"Pre-write validation failed: {validation_err}")
                
                # Write attempt HTML and run MCP validator
                html_content = gen_out.get("html", "")
                
                # If generator returns empty HTML, it's a generation/schema failure
                # Let orchestrator retry handle it - don't add extra retry layer
                if not html_content:
                    logger.error(
                        f"[Orchestrator] ✗ Generator returned empty HTML | "
                        f"attempt: {attempt}/{max_attempts}"
                    )
                    if attempt < max_attempts:
                        # Let orchestrator loop retry with error feedback
                        tamplate = None  # No template since we have no HTML
                        validator_errors = ["Generator returned empty HTML - ensure complete HTML document is generated"]
                        # Specific message based on empty HTML issue
                        self._emit_event(
                            event_callback,
                            "GENERATING",
                            f"Regenerating the complete design structure (attempt {attempt + 1}/{max_attempts})..."
                        )
                        attempt += 1
                        continue
                    else:
                        raise AgentError("Generator returned empty HTML after all attempts")
                
                if html_content:
                    # Persist attempt-specific snapshot and current index to artifacts dir
                    attempt_path = workdir / f"index_attempt_{attempt}.html"
                    attempt_path.write_text(html_content, encoding="utf-8")
                    index_path = workdir / "index.html"
                    index_path.write_text(html_content, encoding="utf-8")
                    logger.info(f"[Orchestrator] ✓ Wrote index.html and attempt snapshot to {index_path}")

                # ========================================
                # PARALLEL VALIDATION: Run iframe + MCP concurrently
                # ========================================
                self._emit_event(event_callback, "GENERATING", "Running parallel validators (iframe + MCP)...")
                
                async def run_iframe_validation():
                    """Iframe validation task"""
                    try:
                        result = await validate_in_iframe(html_content, timeout_ms=15000)
                        logger.info(
                            f"[Orchestrator] ✓ Iframe validation complete | "
                            f"passed: {result.get('passed')} | "
                            f"errors: {len(result.get('errors', []))}"
                        )
                        return result
                    except Exception as e:
                        logger.error(f"[Orchestrator] ✗ Iframe validation failed: {e}")
                        return {"passed": True, "errors": [], "warning": str(e)}
                
                async def run_mcp_validation():
                    """MCP validation task (with file sync)"""
                    try:
                        # Sync file first
                        await asyncio.wait_for(
                            asyncio.to_thread(
                                mcp_client.write_files,
                                [{"path": "index.html", "content": html_content}]
                            ),
                            timeout=10.0
                        )
                        logger.debug(f"[Orchestrator] ✓ Synced to MCP workspace")
                        
                        # Run validation
                        qa = await asyncio.wait_for(
                            asyncio.to_thread(mcp_client.validate_static_bundle),
                            timeout=90.0
                        )
                        status = qa.get("status", "PASS")
                        violations = qa.get("violations", []) or []
                        mcp_errors = [
                            self._format_error_for_generator("mcp", v)
                            for v in violations if v.get("severity") == "error"
                        ]
                        logger.info(
                            f"[Orchestrator] ✓ MCP validation complete | "
                            f"status: {status} | "
                            f"errors: {len(mcp_errors)}"
                        )
                        return {"status": status, "errors": mcp_errors, "qa": qa}
                    except asyncio.TimeoutError:
                        logger.warning(f"[Orchestrator] MCP validation timed out, skipping")
                        return {"status": "PASS", "errors": [], "qa": None}
                    except Exception as e:
                        logger.warning(f"[Orchestrator] MCP validation failed: {e}, skipping")
                        return {"status": "PASS", "errors": [], "qa": None}
                
                # Run both validations in parallel
                iframe_result, mcp_result = await asyncio.gather(
                    run_iframe_validation(),
                    run_mcp_validation(),
                    return_exceptions=False
                )
                
                # Extract results
                iframe_errors = iframe_result.get("errors", [])
                iframe_screenshot = iframe_result.get("screenshot")
                mcp_errors = mcp_result.get("errors", [])
                status = mcp_result.get("status", "PASS")
                qa = mcp_result.get("qa")
                
                # Wrap remaining code in try-except for proper error handling
                try:
                    # CRITICAL: Batch ALL errors together (pre-validation + iframe + MCP)
                    # This ensures ONE Responses API call instead of multiple iterations
                    all_errors = list(all_pre_validation_errors) + iframe_errors + mcp_errors
                    passed = (status == "PASS" and not all_errors and iframe_result.get("passed", False))

                    # Classify errors by severity for intelligent retry decisions
                    errors_by_severity = format_errors_by_severity(all_errors)

                    # Log and decide
                    logger.info(
                        f"[Orchestrator] Combined Validation | attempt: {attempt}/{max_attempts} | "
                        f"status: {status} | "
                        f"pre_validation_errors: {len(all_pre_validation_errors)} | "
                        f"iframe_errors: {len(iframe_errors)} | "
                        f"mcp_errors: {len(mcp_errors)} | "
                        f"total_errors: {len(all_errors)} | "
                        f"critical: {len(errors_by_severity['critical'])} | "
                        f"major: {len(errors_by_severity['major'])} | "
                        f"minor: {len(errors_by_severity['minor'])}"
                    )

                    if passed:
                        # Optionally inject QA report comment
                        try:
                            self._inject_qa_report_via_mcp(workdir, qa, mcp_client)
                        except Exception:
                            pass
                        # Extract section info from HTML for final message
                        section_count = html_content.lower().count("<section")
                        self._emit_event(event_callback, "GENERATING", f"✓ Created {section_count} beautiful sections with perfect spacing and typography")
                        return {
                            "success": True,
                            "html": html_content,
                            "meta": gen_out.get("meta", {}),
                            "orchestration_log": log,
                            "bundle_path": str(workdir)
                        }

                    # Not passed → prepare retry with tamplate + ALL validator_errors batched
                    # Use severity-based retry decision
                    should_retry = should_continue_retrying(attempt, errors_by_severity)
                    
                    if attempt < max_attempts and should_retry:
                        tamplate = html_content
                        validator_errors = all_errors  # Send ALL errors in ONE batch
                        # Persist last failing for diff review
                        last_fail = workdir / "index_last_fail.html"
                        last_fail.write_text(html_content, encoding="utf-8")
                        
                        # VISUAL VALIDATION: If we have screenshot and errors, use visual feedback refinement
                        # This sends screenshot + errors to generator for visual tweaks
                        if iframe_screenshot and attempt > 1:
                            logger.info(
                                f"[Orchestrator] Using visual feedback refinement | "
                                f"attempt: {attempt}/{max_attempts} | "
                                f"screenshot_size: {len(iframe_screenshot)} bytes | "
                                f"errors: {len(all_errors)}"
                            )
                            self._emit_event(
                                event_callback,
                                "GENERATING",
                                "Analyzing visual layout with AI — refining design based on screenshot feedback..."
                            )
                            try:
                                # Call visual feedback refinement
                                gen_out, generator_response_id = await self.generator.run_with_visual_feedback(
                                    html_content=html_content,
                                    screenshot_base64=iframe_screenshot,
                                    validator_errors=all_errors,
                                    previous_response_id=generator_response_id
                                )
                                
                                # Continue to next iteration with visually refined output
                                attempt += 1
                                continue
                                
                            except Exception as visual_err:
                                logger.warning(
                                    f"[Orchestrator] Visual feedback refinement failed: {visual_err} | "
                                    f"Falling back to regular retry"
                                )
                                # Fall through to regular retry
                        
                        # Log detailed error breakdown for debugging
                        retry_config = get_retry_config(attempt + 1)
                        logger.info(
                            f"[Orchestrator] Preparing batched retry | "
                            f"total_errors: {len(all_errors)} | "
                            f"breakdown: pre-validation({len(all_pre_validation_errors)}), iframe({len(iframe_errors)}), mcp({len(mcp_errors)}) | "
                            f"severity: critical({len(errors_by_severity['critical'])}), major({len(errors_by_severity['major'])}), minor({len(errors_by_severity['minor'])}) | "
                            f"next_model: {retry_config['model']} | "
                            f"next_temp: {retry_config['temperature']}"
                        )
                        
                        # Create severity-aware message
                        if errors_by_severity['critical']:
                            severity_msg = f"{len(errors_by_severity['critical'])} critical"
                        elif errors_by_severity['major']:
                            severity_msg = f"{len(errors_by_severity['major'])} major"
                        else:
                            severity_msg = f"{len(errors_by_severity['minor'])} minor"
                        
                        # Dynamic retry message based on error types and attempt
                        retry_messages = [
                            f"Refining the design — addressing {severity_msg} feedback on layout and assets...",
                            f"Enhancing details — fixing {severity_msg} items to ensure perfect quality...",
                            f"Making final adjustments — {severity_msg} optimizations for a flawless result..."
                        ]
                        retry_idx = min(attempt - 1, len(retry_messages) - 1)
                        self._emit_event(event_callback, "GENERATING", retry_messages[retry_idx])
                        attempt += 1
                        continue
                    elif not should_retry:
                        # Only minor errors remain, accept the result
                        logger.info(
                            f"[Orchestrator] Accepting result with only minor errors | "
                            f"minor_errors: {len(errors_by_severity['minor'])} | "
                            f"attempt: {attempt}/{max_attempts}"
                        )
                        return {
                            "success": True,
                            "html": html_content,
                            "meta": gen_out.get("meta", {}),
                            "orchestration_log": log,
                            "bundle_path": str(workdir),
                            "warnings": errors_by_severity['minor']  # Include minor errors as warnings
                        }
                    else:
                        raise AgentError(
                            f"Validation did not pass within max attempts. "
                            f"Critical: {len(errors_by_severity['critical'])}, "
                            f"Major: {len(errors_by_severity['major'])}, "
                            f"Minor: {len(errors_by_severity['minor'])}. "
                            f"Sample errors: {all_errors[:5]}"
                        )
                except asyncio.TimeoutError as timeout_err:
                    logger.error(
                        f"[Orchestrator] ✗ MCP validation timed out after 60s | "
                        f"attempt: {attempt}/{max_attempts}"
                    )
                    # On timeout, treat as validation failure and retry if possible
                    if attempt < max_attempts:
                        tamplate = html_content
                        validator_errors = ["MCP validation timed out - retrying generation"]
                        # More user-friendly timeout message
                        self._emit_event(
                            event_callback,
                            "GENERATING",
                            f"Quality check took longer than expected — regenerating with optimizations..."
                        )
                        attempt += 1
                        continue
                    else:
                        raise AgentError("MCP validation timed out after multiple attempts")
                except AgentError:
                    raise
                except Exception as mcp_err:
                    logger.error(
                        f"[Orchestrator] ✗ MCP validation failed | error_type: {type(mcp_err).__name__} | error: {str(mcp_err)}",
                        exc_info=True
                    )
                    raise AgentError(f"MCP validation failed: {mcp_err}")
            
            # This code should never be reached (all paths above return)
            # But keep as safety fallback
            raise AgentError(f"Unexpected exit from orchestration loop after {max_attempts} attempts")
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self._emit_event(event_callback, "ERROR", f"An error occurred: {str(e)}")
            log.append({"step": "error", "error": str(e), "traceback": error_trace, "timestamp": self._timestamp()})
            logger.error(f"[Orchestrator] Exception: {e}\n{error_trace}")
            raise AgentError(f"Orchestration failed: {e}")
        finally:
            # Clean up MCP client
            try:
                mcp_client.close()
            except Exception as e:
                logger.warning(f"[Orchestrator] Error closing MCP client: {e}")
    
    # Ensures Google Place data has required fields (types, photos, reviews) with safe [] defaults.
    # Prevents downstream errors from missing keys in Google API responses.
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
    
    # Validates mapper output has required fields (business_summary, assats) before proceeding.
    # Returns False if schema invalid to trigger orchestrator retry logic.
    def _basic_schema_ok(self, mapper_out: Dict[str, Any]) -> bool:
        """Basic schema validation for mapper output"""
        return (
            "business_summary" in mapper_out and
            isinstance(mapper_out.get("business_summary"), str) and
            "assats" in mapper_out and
            isinstance(mapper_out["assats"], dict)
        )
    
    # Injects QA report HTML comment with validation results (status, warnings, tier) into index.html.
    # Non-blocking operation - logs warning if fails; provides traceability of validation history.
    def _inject_qa_report_via_mcp(self, workdir: Path, val_result: Dict[str, Any], mcp_client: MCPClient):
        """Inject QA REPORT comment into index.html via MCP (only side-effect path)"""
        # Create QA REPORT comment - handle missing fields gracefully
        qa_report = val_result.get("qa_report", {})
        violations = val_result.get("violations", [])
        warnings = [v.get("hint", "") for v in violations if v.get("severity") == "warn"]
        report_comment = f"""<!-- QA REPORT
timestamp: {self._timestamp()}
tier: {val_result.get("tier", "enhanced")}
status: {val_result.get("status", "PASS")}
fixed: {json.dumps(warnings)}
-->
"""
        try:
            result = mcp_client.inject_comment("index.html", report_comment)
            if result.get("applied"):
                logger.info("[Orchestrator] QA report comment injected via MCP")
        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to inject QA report comment via MCP: {e}")
    
    
    # Returns current UTC timestamp in ISO 8601 format with 'Z' suffix for QA reports.
    # Ensures consistent timestamping across all logs and artifact metadata.
    def _timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Converts validation errors from different sources (pre_write, mcp, iframe) into standardized format.
    # Adds severity, location, and explicit fix instructions for common errors like TARGET_BLANK_NO_NOOPENER.
    def _format_error_for_generator(self, error_source: str, error_data: any) -> str:
        """
        Standardize error format for consistent generator feedback
        
        Args:
            error_source: "pre_write" | "mcp" | "iframe"
            error_data: Error string (pre_write/iframe) or dict (mcp)
        
        Returns:
            Standardized error string with severity, ID, hint, and location
        
        Format: [SEVERITY] ID: Hint (Location: where)
        """
        if error_source == "pre_write":
            # Pre-write errors are already strings - pass through
            return str(error_data)
        
        elif error_source == "iframe":
            # Iframe validation errors - already formatted strings with emojis
            # These come from iframe_validator.py and are already user-friendly
            return str(error_data)
        
        elif error_source == "mcp":
            # Convert MCP dict to standardized readable format
            error_id = error_data.get("id", "UNKNOWN")
            hint = error_data.get("hint", "No hint provided")
            where = error_data.get("where", "Unknown location")
            severity = error_data.get("severity", "error")
            
            # Add explicit fix instructions for common errors
            if "TARGET_BLANK_NO_NOOPENER" in error_id:
                hint += ". CRITICAL: Find EVERY <a> tag with target=\"_blank\" and add rel=\"noopener noreferrer\" attribute. Check ALL links including footer, maps, social media, etc."
            
            return f"[{severity.upper()}] {error_id}: {hint} (Location: {where})"
        
        else:
            # Fallback for unknown sources
            return str(error_data)
    
    # Safely calls event callback with phase and message for progress tracking; catches and logs errors.
    # Prevents build failures from callback issues - event emission is non-blocking.
    def _emit_event(self, callback: Optional[Callable[[str, str], None]], phase: str, message: str):
        """Emit event via callback if provided"""
        if callback:
            try:
                callback(phase, message)
            except Exception as e:
                print(f"[Orchestrator] Event callback error: {e}")


# Export for convenience
__all__ = ["OrchestratorAgent"]
