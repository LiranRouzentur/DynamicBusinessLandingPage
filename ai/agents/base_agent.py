"""Base class for all agents with JSON response file handling"""
import json
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI


class AgentError(Exception):
    """Base exception for agent errors"""
    pass


class BaseAgent:
    """Base class for all agents with JSON response file support"""
    
    def __init__(
        self, 
        client: OpenAI, 
        model: str = "gpt-4o", 
        temperature: float = 0.7, 
        agent_name: str = "Agent"
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.timeout = 180  # 3 minute timeout
        self.agent_name = agent_name
        
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
    
    def _clear_response_file(self):
        """Clear the response file before each request"""
        if self.response_file.exists():
            self.response_file.write_text("{}", encoding="utf-8")
    
    def _clear_request_file(self):
        """Clear the request file before each request"""
        if self.request_file.exists():
            self.request_file.write_text("{}", encoding="utf-8")
    
    def _write_request(self, request_data: Dict[str, Any]):
        """Write agent request to JSON file"""
        self.request_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.request_file, "w", encoding="utf-8") as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)
    
    def _write_response(self, response: Dict[str, Any]):
        """Write agent response to JSON file"""
        self.response_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.response_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
    
    async def _call_openai(
        self,
        system_prompt: str,
        user_message: Dict[str, Any],
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Common OpenAI call logic"""
        # Clear request and response files before each call
        self._clear_request_file()
        self._clear_response_file()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_message, indent=2)}
        ]
        
        # Write request to file
        request_data = {
            "model": self.model,
            "temperature": self.temperature,
            "system_prompt": system_prompt,
            "user_message": user_message,
            "has_response_schema": response_schema is not None
        }
        self._write_request(request_data)
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        
        # Add response format for structured output
        if response_schema:
            kwargs["response_format"] = {"type": "json_object"}
            schema_json = json.dumps(response_schema, indent=2)
            schema_note = (
                f"\n\n*** RESPONSE FORMAT REQUIREMENTS ***\n"
                f"You must return valid JSON matching this exact schema structure.\n"
                f"Include ALL required fields shown below.\n\nSchema:\n{schema_json}"
            )
            messages[0]["content"] += schema_note
        
        try:
            print(f"[{self.agent_name}] Calling {self.model}")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    **kwargs
                ),
                timeout=self.timeout
            )
            
            result_text = response.choices[0].message.content
            print(f"[{self.agent_name}] Response received ({response.usage.total_tokens} tokens)")
            
            if response_schema:
                result = json.loads(result_text)
                # Write response to JSON file
                self._write_response(result)
                return result
            
            # Write response even if no schema
            self._write_response({"response": result_text})
            return result_text
            
        except asyncio.TimeoutError:
            error_msg = f"Agent timeout after {self.timeout}s"
            self._write_response({"error": error_msg})
            raise AgentError(error_msg)
        except Exception as e:
            error_msg = f"Agent call failed: {str(e)}"
            self._write_response({"error": error_msg})
            raise AgentError(error_msg)

