"""Base class for all agents with JSON response file handling"""
import json
import asyncio
import os
import logging
import inspect
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)

# Enable debug file writing via environment variable
ENABLE_DEBUG_FILES = os.getenv("AGENTS_DEBUG_FILES", "false").lower() == "true"

# Feature flag: Enable Responses API (stateful context) - gradual rollout
# ENABLED: OpenAI Python SDK 2.6.1+ supports Responses API
USE_RESPONSES_API = os.getenv("USE_RESPONSES_API", "true").lower() == "true"

# Checks if OpenAI SDK supports response_format parameter in responses.create() via runtime inspection.
# Returns True if supported, False otherwise.
def _check_response_format_support(client: OpenAI) -> bool:
    """
    Runtime check if the current OpenAI SDK supports response_format parameter
    in responses.create(). Returns True if supported, False otherwise.
    """
    try:
        sig = inspect.signature(client.responses.create)
        return 'response_format' in sig.parameters
    except Exception as e:
        logger.warning(f"Could not detect response_format support: {e}")
        return False

# Checks if OpenAI SDK supports tools parameter for custom function calling in responses.create().
# Returns True if supported, False otherwise - determines if strict function calling is available.
def _check_tools_support(client: OpenAI) -> bool:
    """
    Runtime check if the current OpenAI SDK supports tools parameter
    in responses.create(). Returns True if supported, False otherwise.
    """
    try:
        sig = inspect.signature(client.responses.create)
        return 'tools' in sig.parameters
    except Exception as e:
        logger.warning(f"Could not detect tools support: {e}")
        return False

# Converts JSON schema to OpenAI tool/function calling format for Responses API.
# Removes 'title' field and returns flat structure with 'strict: True' for schema validation.
def _convert_schema_to_tool(schema: Dict[str, Any], tool_name: str = None) -> Dict[str, Any]:
    """
    Convert a JSON schema to OpenAI tool/function calling format
    
    Args:
        schema: JSON schema with 'type', 'properties', 'required', etc.
        tool_name: Name for the tool (defaults to schema['title'] or 'emit_result')
    
    Returns:
        Tool definition for OpenAI API
    """
    # Extract tool name from schema title or use default
    name = tool_name or schema.get("title", "emit_result")
    
    # Build tool definition for Responses API custom function calling
    # Note: "title" field must be REMOVED from parameters schema for strict mode
    parameters_schema = {k: v for k, v in schema.items() if k != "title"}
    
    # Responses API tool format (FLAT structure from official OpenAI example):
    # All fields at root level - NO nested "function" object
    tool = {
        "type": "function",
        "name": name,  # At root level (Responses API format)
        "description": f"Return the final {name} result as structured JSON",
        "parameters": parameters_schema,  # Schema without "title" field
        "strict": True  # Enable strict schema validation
    }
    
    return tool

# Telemetry utilities removed - were never used in production


class AgentError(Exception):
    """Base exception for agent errors"""
    pass


class BaseAgent:
    """Base class for all agents with JSON response file support and Responses API (stateful context)"""
    
    # Initializes base agent with OpenAI client, model config, and response file handling.
    # Detects SDK capabilities (tools, response_format) and sets up response_id caching for stateful context.
    def __init__(
        self, 
        client: OpenAI, 
        model: str = "gpt-4.1", 
        temperature: float = 0.7, 
        agent_name: str = "Agent"
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.timeout = 300  # 5 minute timeout (generation can take longer for complex pages)
        self.agent_name = agent_name
        
        # NEW: Response ID cache for stateful context (Responses API)
        self.response_id_cache: Dict[str, str] = {}  # cache_key -> latest_response_id
        
        # Runtime capability detection: Check SDK capabilities
        # NOTE: With SDK 2.6.1+, Responses API supports:
        # - Built-in tools: web_search, code_interpreter, file_search, image_generation
        # - Custom function calling: For structured JSON outputs
        # Reference: https://platform.openai.com/docs/api-reference/responses
        # 
        # Test custom function calling first (best for structured outputs)
        # If it fails, fall back to embedded schema method
        self.supports_response_format = _check_response_format_support(client)
        self.supports_tools = _check_tools_support(client)
        
        if self.supports_tools:
            logger.info(f"[{agent_name}] ✓ SDK supports tools/function calling (PREFERRED for structured outputs)")
        elif self.supports_response_format:
            logger.info(f"[{agent_name}] ✓ SDK supports response_format (structured outputs)")
        else:
            logger.warning(f"[{agent_name}] ⚠ SDK lacks structured output support, using embedded schema fallback")
        
        # Determine agent directory - check if we're in a subdirectory
        # Get the calling module's path by inspecting stack
        import inspect
        frame = inspect.currentframe().f_back
        caller_file = Path(frame.f_globals.get('__file__', __file__))
        
        # If caller is in a subdirectory (e.g., mapper/mapper_agent.py), use that directory
        if caller_file.parent.name != Path(__file__).parent.name:
            agent_dir = caller_file.parent
        else:
            # Fallback to agent_name directory
            base_dir = Path(__file__).parent
            agent_dir = base_dir / agent_name.lower()
        
        agent_dir.mkdir(parents=True, exist_ok=True)
        self.response_file = agent_dir / f"{agent_name.lower()}_response.json"
        self.request_file = agent_dir / f"{agent_name.lower()}_request.json"
    
    # Clears response JSON file before new request (only if AGENTS_DEBUG_FILES=true).
    # Used for debugging agent outputs without cluttering production environments.
    def _clear_response_file(self):
        """Clear the response file before each request (only if debug enabled)"""
        if not ENABLE_DEBUG_FILES:
            return
        if self.response_file.exists():
            self.response_file.write_text("{}", encoding="utf-8")
    
    # Clears request JSON file before new request (only if AGENTS_DEBUG_FILES=true).
    # Prevents old debug data from being confused with current request data.
    def _clear_request_file(self):
        """Clear the request file before each request (only if debug enabled)"""
        if not ENABLE_DEBUG_FILES:
            return
        if self.request_file.exists():
            self.request_file.write_text("{}", encoding="utf-8")
    
    # Writes complete agent request payload to JSON file for debugging (only if AGENTS_DEBUG_FILES=true).
    # Includes model, temperature, messages/instructions, and schema config.
    def _write_request(self, request_data: Dict[str, Any]):
        """Write agent request to JSON file (only if debug enabled)"""
        if not ENABLE_DEBUG_FILES:
            return
        self.request_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.request_file, "w", encoding="utf-8") as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)
    
    # Writes agent response to JSON file with request metadata for debugging (only if AGENTS_DEBUG_FILES=true).
    # Combines request and response data to understand full context of API calls.
    def _write_response(self, response: Dict[str, Any], request_metadata: Optional[Dict[str, Any]] = None):
        """Write agent response to JSON file with optional request metadata (only if debug enabled)"""
        if not ENABLE_DEBUG_FILES:
            return
        self.response_file.parent.mkdir(parents=True, exist_ok=True)
        
        # If request metadata provided, include it for debugging
        if request_metadata:
            full_response = {
                "request": request_metadata,
                "response": response,
                "timestamp": response.get("timestamp") if isinstance(response, dict) else None
            }
            with open(self.response_file, "w", encoding="utf-8") as f:
                json.dump(full_response, f, indent=2, ensure_ascii=False)
        else:
            # Fallback to original behavior
            with open(self.response_file, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2, ensure_ascii=False)
    
    # Calls OpenAI Responses API with stateful context support for token-efficient retries (80-90% savings).
    # Uses strict tool calling or response_format for guaranteed valid JSON; returns (result_dict, response_id).
    async def _call_responses_api(
        self,
        system_prompt: str,
        user_message: Dict[str, Any],
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 12000,
        previous_response_id: Optional[str] = None,
        is_retry: bool = False,
        cache_key: Optional[str] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Call OpenAI Responses API with stateful context support.
        
        Phase 1: Minimal implementation for Generator QA retry loop only.
        
        Args:
            system_prompt: System prompt content
            user_message: User message dict (full context OR minimal fix instructions if is_retry=True)
            response_schema: Optional JSON schema for structured output
            temperature: Temperature override
            max_tokens: Maximum output tokens
            previous_response_id: ID from previous response (enables stateful context)
            is_retry: If True, user_message should contain only fix instructions (not full context)
            cache_key: Unique key for tracking this conversation chain
            
        Returns:
            Tuple of (result_dict, response_id) - response_id can be used for next retry
        """
        # Clear files before request
        self._clear_request_file()
        self._clear_response_file()
        
        # Use provided temperature or default
        temp = temperature if temperature is not None else self.temperature
        
        # Build Responses API payload using responses.create()
        # SDK 2.6+ supports responses.create() directly
        # Responses API uses 'instructions' for system prompt and 'input' for user message
        if is_retry and previous_response_id:
            # RETRY MODE: Minimal payload - only fix instructions
            # Model maintains full context via previous_response_id
            user_content = json.dumps({
                "validator_errors": user_message.get("validator_errors", []),
                "note": "Please fix the issues in your previous response. All original context is preserved via stateful context."
            }, indent=2, ensure_ascii=False)
            logger.info(
                f"[{self.agent_name}] Responses API RETRY mode | "
                f"previous_response_id: {previous_response_id[:20]}... | "
                f"errors_count: {len(user_message.get('validator_errors', []))}"
            )
        else:
            # FIRST ATTEMPT: Full context
            user_content = json.dumps(user_message, indent=2, ensure_ascii=False)
        
        kwargs = {
            "model": self.model,
            "instructions": system_prompt,  # System prompt goes here
            "input": user_content,  # User message (can be string or messages array)
            "temperature": temp,
            "max_output_tokens": max_tokens,  # Responses API uses 'max_output_tokens'
        }
        
        # Add creativity-enhancing sampling parameters
        # Note: Responses API has limited parameter support compared to Chat Completions
        # Only temperature and top_p are supported (no presence/frequency penalties)
        if top_p is not None:
            kwargs["top_p"] = top_p
        # presence_penalty and frequency_penalty are NOT supported by Responses API
        # We rely on prompt engineering and higher temperature/top_p instead
        
        # Add previous_response_id for stateful context
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
            logger.debug(f"[{self.agent_name}] Using stateful context with previous_response_id: {previous_response_id[:20]}...")
        
        # CRITICAL: Use structured outputs for guaranteed valid JSON
        # Priority: tools > response_format > embedded schema
        # Reference: https://platform.openai.com/docs/api-reference/responses/create
        if response_schema:
            schema_name = response_schema.get("title", "GeneratorResponse")
            
            if self.supports_tools:
                # BEST: Use strict tool/function calling (most compatible and reliable)
                tool = _convert_schema_to_tool(response_schema, tool_name=schema_name)
                kwargs["tools"] = [tool]
                # Responses API: tool_choice can be "auto", "required", "none", or object
                # For structured outputs, use "required" to force tool call
                # Note: If specific tool selection is needed, format may differ from Chat Completions
                kwargs["tool_choice"] = "required"  # Force the model to call one of the tools
                logger.info(
                    f"[{self.agent_name}] Using strict tool calling | "
                    f"tool: {schema_name} | "
                    f"strict: True | "
                    f"tool_choice: required | "
                    f"required_fields: {response_schema.get('required', [])}"
                )
            elif self.supports_response_format:
                # GOOD: Use structured outputs (response_format parameter)
                json_schema_config = {
                    "name": schema_name,
                    "schema": response_schema,
                    "strict": True  # CRITICAL: Enforces exact schema compliance
                }
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": json_schema_config
                }
                logger.info(
                    f"[{self.agent_name}] Using structured outputs (response_format) | "
                    f"schema: {schema_name} | "
                    f"strict: True | "
                    f"required_fields: {response_schema.get('required', [])}"
                )
            else:
                # FALLBACK: Embed schema in instructions (less reliable but compatible)
                schema_json = json.dumps(response_schema, indent=2)
                schema_instructions = (
                    f"\n\n=== CRITICAL: JSON OUTPUT REQUIREMENTS ===\n"
                    f"You MUST return ONLY valid JSON matching this EXACT schema.\n"
                    f"Include ALL required fields. No additional fields.\n"
                    f"No explanations, no markdown, ONLY the JSON object.\n\n"
                    f"IMPORTANT: When including HTML in JSON strings:\n"
                    f"- Properly escape all quotes (use \\\\ before \\\" and ')\n"
                    f"- Ensure all string values are terminated\n"
                    f"- No unescaped newlines in string values\n"
                    f"- Use \\\\n for line breaks within strings\n\n"
                    f"Required Schema:\n{schema_json}\n"
                    f"========================================\n"
                )
                kwargs["instructions"] += schema_instructions
                logger.warning(
                    f"[{self.agent_name}] Using embedded schema fallback (SDK doesn't support response_format) | "
                    f"schema: {response_schema.get('title', 'Unknown')}"
                )
        
        # Write request for debugging
        self._write_request(kwargs)
        
        # COMPREHENSIVE LOGGING: Log complete request for analysis
        logger.info("=" * 80)
        logger.info(f"[{self.agent_name}] === GENERATOR REQUEST START ===")
        logger.info(f"[{self.agent_name}] Model: {self.model}")
        logger.info(f"[{self.agent_name}] Temperature: {temp}, Top-P: {kwargs.get('top_p', 'default')}")
        logger.info(f"[{self.agent_name}] Max Output Tokens: {max_tokens}")
        logger.info(f"[{self.agent_name}] Previous Response ID: {previous_response_id[:20] + '...' if previous_response_id else 'None'}")
        logger.info(f"[{self.agent_name}] Is Retry: {is_retry}")
        logger.info(f"[{self.agent_name}] Has Schema: {response_schema is not None}")
        logger.info(f"[{self.agent_name}] Uses Tools: {bool(kwargs.get('tools'))}")
        logger.info(f"[{self.agent_name}] Uses Response Format: {bool(kwargs.get('response_format'))}")
        logger.info(f"[{self.agent_name}] Instructions Length: {len(kwargs.get('instructions', ''))} chars")
        logger.info(f"[{self.agent_name}] Input Length: {len(str(kwargs.get('input', '')))} chars")
        if kwargs.get('tools'):
            # Responses API has FLAT structure: name and strict at root level (not nested in 'function')
            logger.info(f"[{self.agent_name}] Tool Name: {kwargs['tools'][0]['name']}")
            logger.info(f"[{self.agent_name}] Tool Strict: {kwargs['tools'][0]['strict']}")
        logger.info(f"[{self.agent_name}] === GENERATOR REQUEST END ===")
        logger.info("=" * 80)
        
        try:
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.responses.create,
                    **kwargs
                ),
                timeout=self.timeout
            )
            
            # Extract response data (Responses API has different structure)
            # Priority: tool_calls > output_parsed > text extraction
            result = None
            result_text = None
            
            # PRIORITY 1: Extract function call (strict function calling - most reliable)
            if self.supports_tools and response_schema:
                schema_name = response_schema.get("title", "GeneratorResponse")
                # Navigate response structure to find function call
                # Responses API structure: response.output is a list with type "function_call"
                logger.debug(f"[{self.agent_name}] Looking for function call: {schema_name}")
                logger.debug(f"[{self.agent_name}] Response has output attr: {hasattr(response, 'output')}")
                logger.debug(f"[{self.agent_name}] Response.output is None: {response.output is None}")
                logger.debug(f"[{self.agent_name}] Response output items: {len(response.output or [])}")
                if response.output:
                    logger.debug(f"[{self.agent_name}] Response.output type: {type(response.output)}")
                
                for idx, output_item in enumerate(response.output or []):
                    # Log full item structure for debugging
                    logger.debug(f"[{self.agent_name}] Output item #{idx}: {type(output_item)}")
                    logger.debug(f"[{self.agent_name}] Output item #{idx} repr: {repr(output_item)[:500]}")
                    
                    # Get type - handle both object and dict access
                    item_type = getattr(output_item, 'type', None) or (output_item.get('type') if isinstance(output_item, dict) else None)
                    logger.debug(f"[{self.agent_name}] Output item #{idx} type: {item_type}")
                    
                    # Responses API uses "function_call" type (not "tool_call")
                    if item_type == "function_call":
                        # Get function name - data is at root level in Responses API
                        func_name = getattr(output_item, 'name', None) or (output_item.get('name') if isinstance(output_item, dict) else None)
                        logger.debug(f"[{self.agent_name}] Found function call: {func_name}")
                        
                        if func_name == schema_name:
                            # Found the function call - extract arguments JSON
                            args_text = getattr(output_item, 'arguments', None) or (output_item.get('arguments') if isinstance(output_item, dict) else None)
                            if args_text:
                                # Check for truncation before parsing
                                # Get finish_reason from the output item or response
                                finish_reason = getattr(output_item, 'finish_reason', None) or getattr(output_item, 'status', None)
                                logger.debug(f"[{self.agent_name}] Function call finish_reason/status: {finish_reason}")
                                
                                # Detect truncation
                                args_str = str(args_text).strip()
                                is_truncated = (
                                    finish_reason == "length" or 
                                    not (args_str.startswith("{") and args_str.endswith("}")) or
                                    args_str.count('"') % 2 != 0  # Odd number of quotes suggests unterminated string
                                )
                                
                                if is_truncated:
                                    logger.error(f"[{self.agent_name}] ✗ Function call arguments appear truncated | finish_reason={finish_reason} | length={len(args_text)} | starts_with_brace={args_str.startswith('{')} | ends_with_brace={args_str.endswith('}')}")
                                    logger.error(f"[{self.agent_name}] Last 100 chars: ...{args_text[-100:]}")
                                    raise AgentError(f"Model hit output token limit (finish_reason={finish_reason}). Response truncated. Retry with higher max_output_tokens.")
                                
                                try:
                                    result = json.loads(args_text)  # Server-validated JSON
                                    result_text = args_text
                                    logger.info(f"[{self.agent_name}] ✓ Extracted function call: {schema_name} (server-validated JSON, {len(args_text)} chars)")
                                    break
                                except json.JSONDecodeError as e:
                                    logger.error(f"[{self.agent_name}] ✗ JSON decode error: {e} | First 200 chars: {args_text[:200]}")
                                    logger.error(f"[{self.agent_name}] Last 200 chars: ...{args_text[-200:]}")
                                    raise AgentError(f"Failed to parse function arguments: {e}. Likely truncated response.")
                            else:
                                logger.error(f"[{self.agent_name}] ✗ Function call '{func_name}' has no arguments")
                
                if not result:
                    # Function call missing - this is an error when using tool_choice="required"
                    logger.error(f"[{self.agent_name}] ✗ Function call '{schema_name}' not found in response")
                    logger.error(f"[{self.agent_name}] Response output: {response.output}")
                    raise AgentError(f"Expected function call '{schema_name}' not found in API response")
            
            # PRIORITY 2: Use output_parsed for response_format (structured outputs)
            elif not result and self.supports_response_format and hasattr(response, 'output_parsed') and response.output_parsed is not None:
                result = response.output_parsed
                result_text = json.dumps(result, ensure_ascii=False)
                logger.info(f"[{self.agent_name}] ✓ Using output_parsed (pre-validated JSON)")
            
            # PRIORITY 3: Fallback to text extraction (for non-structured responses)
            elif not result:
                # Try to extract text from output
                try:
                    if response.output and len(response.output) > 0:
                        first_output = response.output[0]
                        # Check if it has text content
                        if hasattr(first_output, 'type') and first_output.type == "text":
                            result_text = getattr(first_output, 'text', None)
                        elif hasattr(first_output, 'content') and first_output.content:
                            # Try extracting from content
                            for content_item in first_output.content:
                                if hasattr(content_item, 'text'):
                                    result_text = content_item.text
                                    break
                    
                    if result_text:
                        logger.debug(f"[{self.agent_name}] Extracting text content for manual parsing")
                    else:
                        logger.error(f"[{self.agent_name}] ✗ No extractable content found in response")
                        raise AgentError("No valid response content found")
                except Exception as e:
                    logger.error(f"[{self.agent_name}] ✗ Failed to extract response content: {e}")
                    raise AgentError(f"Failed to extract response content: {e}")
            
            response_id = response.id  # Save for stateful context
            
            # Token counts are in usage object, not directly on response
            # The Responses API may use different field names than Chat Completions
            if hasattr(response, 'usage') and response.usage:
                # Try both naming conventions (Responses API may differ from Chat Completions)
                prompt_tokens = getattr(response.usage, 'input_tokens', None) or getattr(response.usage, 'prompt_tokens', 0)
                completion_tokens = getattr(response.usage, 'output_tokens', None) or getattr(response.usage, 'completion_tokens', 0)
                total_tokens = getattr(response.usage, 'total_tokens', prompt_tokens + completion_tokens)
            else:
                # Fallback if usage not available
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0
                logger.warning(f"[{self.agent_name}] No usage data in response")
            
            # COMPREHENSIVE LOGGING: Log complete response for analysis
            logger.info("=" * 80)
            logger.info(f"[{self.agent_name}] === GENERATOR RESPONSE START ===")
            logger.info(f"[{self.agent_name}] Response ID: {response_id[:40]}...")
            logger.info(f"[{self.agent_name}] Tokens - Total: {total_tokens}, Prompt: {prompt_tokens}, Completion: {completion_tokens}")
            logger.info(f"[{self.agent_name}] Result Type: {'tool_call' if result else 'text'}")
            logger.info(f"[{self.agent_name}] Response Length: {len(result_text) if result_text else 0} chars")
            if result:
                logger.info(f"[{self.agent_name}] Parsed Result Keys: {list(result.keys())}")
                logger.info(f"[{self.agent_name}] HTML Length: {len(result.get('html', ''))} chars")
            if result_text:
                logger.info(f"[{self.agent_name}] Response Preview (first 500 chars):")
                logger.info(f"[{self.agent_name}] {result_text[:500]}...")
            logger.info(f"[{self.agent_name}] === GENERATOR RESPONSE END ===")
            logger.info("=" * 80)
            
            # Log token savings if this was a retry
            if is_retry and previous_response_id:
                # Estimate original payload would have been ~5x larger
                estimated_original_tokens = prompt_tokens * 5
                token_savings = estimated_original_tokens - prompt_tokens
                savings_pct = (token_savings / estimated_original_tokens) * 100 if estimated_original_tokens > 0 else 0
                
                # Token savings logging removed - telemetry module was unused
                
                logger.info(
                    f"[{self.agent_name}] 💰 TOKEN_SAVINGS | "
                    f"actual={prompt_tokens} | "
                    f"estimated_without_cache={estimated_original_tokens} | "
                    f"saved={token_savings} ({savings_pct:.1f}%) | "
                    f"cache_key={cache_key} | "
                    f"response_id={previous_response_id[:20]}..."
                )
            
            # Prepare metadata
            request_metadata = {
                "model": self.model,
                "temperature": temp,
                "max_tokens": max_tokens,
                "previous_response_id": previous_response_id,
                "is_retry": is_retry,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                "response_id": response_id
            }
            
            # Parse JSON response (skip parsing if we already have output_parsed from structured outputs)
            if result is not None:
                # Already parsed and validated by structured outputs (output_parsed)
                self._write_response(result, request_metadata)
                logger.debug(f"[{self.agent_name}] Using pre-validated result from output_parsed")
            else:
                # Manual JSON parsing (fallback for embedded schema or older SDK)
                try:
                    cleaned_text = result_text.strip()
                    # Remove markdown code blocks if present
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[7:]
                    elif cleaned_text.startswith("```"):
                        cleaned_text = cleaned_text[3:]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    cleaned_text = cleaned_text.strip()
                    
                    result = json.loads(cleaned_text)
                    self._write_response(result, request_metadata)
                    logger.debug(f"[{self.agent_name}] JSON response parsed (keys: {list(result.keys())})")
                except json.JSONDecodeError as json_err:
                    error_msg = f"Failed to parse JSON response: {json_err}"
                    logger.error(
                        f"[{self.agent_name}] ✗ {error_msg} | "
                        f"response_preview: {result_text[:200]}... | "
                        f"response_length: {len(result_text)}"
                    )
                    self._write_response({"error": error_msg, "raw_response": result_text}, request_metadata)
                    raise AgentError(error_msg)
            
            # Cache response_id for this conversation
            if cache_key:
                self.response_id_cache[cache_key] = response_id
                # Cache usage logging removed - telemetry module was unused
            
            return result, response_id
            
        except asyncio.TimeoutError as timeout_err:
            error_msg = f"Agent timeout after {self.timeout}s"
            logger.error(f"[{self.agent_name}] ✗ {error_msg}")
            try:
                self._write_response({"error": error_msg, "error_type": "timeout"})
            except Exception:
                pass
            raise AgentError(error_msg)
        except Exception as e:
            error_msg = f"Agent call failed: {str(e)}"
            
            # Enhanced error logging with context
            error_context = {
                "agent": self.agent_name,
                "model": self.model,
                "temperature": temp,
                "previous_response_id": previous_response_id[:20] if previous_response_id else None,
                "is_retry": is_retry,
                "cache_key": cache_key
            }
            
            logger.error(
                f"[{self.agent_name}] ✗ AGENT_ERROR | "
                f"error_type={type(e).__name__} | "
                f"message={error_msg[:200]} | "
                f"context={error_context}",
                exc_info=True
            )
            
            try:
                self._write_response({
                    "error": error_msg, 
                    "error_type": type(e).__name__,
                    "context": error_context
                })
            except Exception:
                pass
            raise AgentError(error_msg)
    
    # Calls OpenAI Chat Completions API with optional JSON schema validation (fallback method).
    # Returns parsed JSON dict; responses_api_mode=True allows large HTML output without schema truncation.
    async def _call_openai(
        self,
        system_prompt: str,
        user_message: Dict[str, Any],
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,  # Override default temperature
        responses_api_mode: bool = False  # If True, don't use JSON schema constraints (for HTML generation)
    ) -> Dict[str, Any]:
        """
        Common OpenAI call logic
        
        Args:
            system_prompt: System prompt content
            user_message: User message dict
            response_schema: Optional JSON schema for structured output
            temperature: Optional temperature override
            responses_api_mode: If True, use Responses API pattern (no JSON schema constraints, higher max_tokens)
        """
        # Clear request and response files before each call
        self._clear_request_file()
        self._clear_response_file()
        
        # Use provided temperature or default to instance temperature
        temp = temperature if temperature is not None else self.temperature
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_message, indent=2, ensure_ascii=False)}
        ]
        
        # Build the actual OpenAI API payload
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": 6000  # Reduced for faster responses and lower costs
        }
        
        # In Responses API mode, don't add JSON schema constraints
        # This allows the model to output large HTML blobs without truncation
        if response_schema and not responses_api_mode:
            schema_json = json.dumps(response_schema, indent=2)
            schema_note = (
                f"\n\n*** RESPONSE FORMAT REQUIREMENTS ***\n"
                f"You must return valid JSON matching this exact schema structure.\n"
                f"Include ALL required fields shown below.\n\nSchema:\n{schema_json}"
            )
            messages[0]["content"] += schema_note
            kwargs["response_format"] = {"type": "json_object"}
        elif responses_api_mode:
            # Responses API mode: request JSON wrapping in the prompt but don't enforce via schema
            # This allows larger output without schema truncation
            logger.info(f"[{self.agent_name}] Using Responses API mode (no JSON schema constraints)")
        
        # Write request to file in EXACT OpenAI API format (for debugging)
        self._write_request(kwargs)
        
        try:
            logger.info(
                f"[{self.agent_name}] Calling {self.model} | "
                f"temperature={temp} | "
                f"max_tokens={kwargs.get('max_tokens', 'default')} | "
                f"timeout={self.timeout}s | "
                f"responses_api_mode={responses_api_mode} | "
                f"has_schema={response_schema is not None and not responses_api_mode}"
            )
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    **kwargs
                ),
                timeout=self.timeout
            )
            
            result_text = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            logger.info(
                f"[{self.agent_name}] ✓ Response received successfully | "
                f"tokens: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens}) | "
                f"response_length: {len(result_text)} chars"
            )
            
            try:
                # Prepare request metadata for debugging
                request_metadata = {
                    "model": self.model,
                    "temperature": temp,
                    "max_tokens": kwargs.get("max_tokens"),
                    "messages": [
                        {
                            "role": msg["role"],
                            "content_length": len(msg["content"]) if isinstance(msg["content"], str) else 0,
                            "content_preview": msg["content"][:200] + "..." if isinstance(msg["content"], str) and len(msg["content"]) > 200 else msg["content"]
                        } for msg in messages
                    ],
                    "response_format": kwargs.get("response_format"),
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens
                    }
                }
                
                # In Responses API mode, try to parse JSON but handle markdown-wrapped responses
                if responses_api_mode or response_schema:
                    # Clean markdown code blocks if present
                    cleaned_text = result_text.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[7:]
                    elif cleaned_text.startswith("```"):
                        cleaned_text = cleaned_text[3:]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    cleaned_text = cleaned_text.strip()
                    
                    try:
                        result = json.loads(cleaned_text)
                        # Write response to JSON file with request metadata
                        self._write_response(result, request_metadata)
                        logger.debug(f"[{self.agent_name}] JSON response parsed and saved (keys: {list(result.keys())})")
                        return result
                    except json.JSONDecodeError as json_err:
                        logger.error(
                            f"[{self.agent_name}] JSON parse failed | "
                            f"error: {str(json_err)} | "
                            f"response_preview: {cleaned_text[:200]}..."
                        )
                        if responses_api_mode:
                            # In Responses API mode, if JSON parse fails, wrap the raw text
                            logger.warning(f"[{self.agent_name}] Wrapping raw text as HTML fallback")
                            wrapped = {"html": cleaned_text, "meta": {"warning": "JSON parse failed, using raw response"}}
                            self._write_response(wrapped, request_metadata)
                            return wrapped
                        else:
                            # Not in Responses API mode, so JSON parse failure is a critical error
                            # Provide detailed error message for debugging
                            raise AgentError(f"Failed to parse JSON response: {str(json_err)}")
                
                # Write response even if no schema
                self._write_response({"response": result_text}, request_metadata)
                logger.debug(f"[{self.agent_name}] Text response saved (length: {len(result_text)} chars)")
                return result_text
                
            except json.JSONDecodeError as json_err:
                error_msg = f"Failed to parse JSON response: {json_err}"
                logger.error(
                    f"[{self.agent_name}] ✗ {error_msg} | "
                    f"response_preview: {result_text[:200]}... | "
                    f"response_length: {len(result_text)}"
                )
                # Save error with request metadata
                request_metadata = {
                    "model": self.model,
                    "temperature": temp,
                    "max_tokens": kwargs.get("max_tokens"),
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens
                    }
                }
                self._write_response({"error": error_msg, "raw_response": result_text}, request_metadata)
                raise AgentError(error_msg)
            except Exception as save_err:
                error_msg = f"Failed to save response: {save_err}"
                logger.error(f"[{self.agent_name}] ✗ {error_msg}")
                raise AgentError(error_msg)
            
        except asyncio.TimeoutError as timeout_err:
            error_msg = f"Agent timeout after {self.timeout}s"
            logger.error(
                f"[{self.agent_name}] ✗ {error_msg} | "
                f"model: {self.model} | "
                f"agent: {self.agent_name}"
            )
            try:
                self._write_response({"error": error_msg, "error_type": "timeout"})
            except Exception as write_err:
                logger.warning(f"[{self.agent_name}] Failed to write error response: {write_err}")
            raise AgentError(error_msg)
        except Exception as e:
            error_msg = f"Agent call failed: {str(e)}"
            logger.error(
                f"[{self.agent_name}] ✗ {error_msg} | "
                f"error_type: {type(e).__name__} | "
                f"model: {self.model} | "
                f"agent: {self.agent_name}",
                exc_info=True
            )
            try:
                self._write_response({"error": error_msg, "error_type": type(e).__name__})
            except Exception as write_err:
                logger.warning(f"[{self.agent_name}] Failed to write error response: {write_err}")
            raise AgentError(error_msg)

