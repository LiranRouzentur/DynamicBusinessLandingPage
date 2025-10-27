"""OpenAI SDK wrapper - Product.md line 89"""

import json
from openai import OpenAI
from app.core.config import settings
from app.models.errors import ApplicationError, ErrorCode


class OpenAIClient:
    """
    Wrapper for OpenAI API client.
    
    All agents use this client to call OpenAI with their respective prompts.
    """
    
    def __init__(self):
        if not settings.openai_api_key:
            print("WARNING: OPENAI_API_KEY not set in .env file")
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
    
    def get_client(self):
        """Get OpenAI client instance"""
        return self.client
    
    async def call_agent(
        self,
        system_prompt: str,
        user_message: dict,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        response_format: dict = None
    ) -> dict:
        """
        Unified async function for all agents to call OpenAI.
        
        Args:
            system_prompt: The system message/prompt
            user_message: The user message/input (can be dict or str)
            model: OpenAI model to use
            temperature: Sampling temperature
            response_format: Format for response (e.g., {"type": "json_object"})
        
        Returns:
            Parsed JSON response as dict
            
        Raises:
            ApplicationError: If API key not configured or API call fails
        """
        if self.client is None:
            raise ApplicationError(
                code=ErrorCode.CONFIGURATION_ERROR,
                message="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file."
            )
        
        # Convert user_message to string if it's a dict
        if isinstance(user_message, dict):
            user_message = json.dumps(user_message, indent=2)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            print(f"[OpenAI] Calling {model}")
            response = self.client.chat.completions.create(**kwargs)
            
            result_text = response.choices[0].message.content
            print(f"[OpenAI] Response received ({response.usage.total_tokens} tokens, {len(result_text)} chars)")
            
            # Parse JSON if response_format was specified
            if response_format and response_format.get("type") == "json_object":
                parsed_result = json.loads(result_text)
                print(f"[OpenAI] Parsed JSON with {len(parsed_result)} keys: {list(parsed_result.keys())[:5]}")
                return parsed_result
            
            return result_text
            
        except Exception as e:
            raise ApplicationError(
                code=ErrorCode.ORCHESTRATION_ERROR,
                message=f"OpenAI API call failed: {str(e)}",
                retryable=True
            )
    
    async def create_completion(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        response_format: dict = None
    ):
        """
        Legacy async completion method for backwards compatibility.
        Use call_agent() for new code.
        """
        if self.client is None:
            raise ApplicationError(
                code=ErrorCode.CONFIGURATION_ERROR,
                message="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file."
            )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        return response


# Global client instance
openai_client = OpenAIClient()

