"""
Tests for retry logic fixes

These tests verify that the triple retry logic has been fixed:
1. Generator no longer retries internally for schema errors
2. Orchestrator doesn't double-retry on empty HTML
3. Maximum 2 generator calls per max_attempts=2 setting
4. Temperature=0 only used once on final attempt
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))

from app.generator.generator_agent import GeneratorAgent
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.base_agent import AgentError


class TestGeneratorRetryRemoval:
    """Test that generator internal retries have been removed"""
    
    @pytest.mark.asyncio
    async def test_generator_no_internal_schema_retry(self):
        """Generator should NOT retry internally on schema validation errors"""
        mock_client = Mock()
        generator = GeneratorAgent(mock_client)
        
        # Mock _call_openai to return malformed response (will fail schema validation)
        generator._call_openai = AsyncMock(return_value={"malformed": "response"})
        
        google_data = {"name": "Test Business"}
        mapper_data = {"business_summary": "Test", "assats": {}}
        
        # Generator should raise AgentError immediately without internal retries
        with pytest.raises(AgentError) as exc_info:
            await generator.run(google_data, mapper_data)
        
        # Verify error message mentions schema validation
        assert "schema validation failed" in str(exc_info.value).lower()
        
        # Verify _call_openai was called ONCE only (no internal retries)
        assert generator._call_openai.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generator_success_first_attempt(self):
        """Generator succeeds on first attempt with valid response"""
        mock_client = Mock()
        generator = GeneratorAgent(mock_client)
        
        # Mock successful response
        valid_response = {
            "html": "<!DOCTYPE html><html><body>Test</body></html>",
            "meta": {"design_rationale": "Test design"}
        }
        generator._call_openai = AsyncMock(return_value=valid_response)
        
        google_data = {"name": "Test Business"}
        mapper_data = {"business_summary": "Test", "assats": {}}
        
        result = await generator.run(google_data, mapper_data)
        
        # Should succeed and return result
        assert result["html"] == valid_response["html"]
        assert result["meta"] == valid_response["meta"]
        
        # Should call OpenAI exactly once
        assert generator._call_openai.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generator_temperature_control(self):
        """Generator uses correct temperature based on final_attempt flag"""
        mock_client = Mock()
        generator = GeneratorAgent(mock_client, temperature=0.7)
        
        valid_response = {
            "html": "<!DOCTYPE html><html><body>Test</body></html>",
            "meta": {}
        }
        generator._call_openai = AsyncMock(return_value=valid_response)
        
        google_data = {"name": "Test"}
        mapper_data = {"business_summary": "Test", "assats": {}}
        
        # Test non-final attempt (should use default temperature=0.7)
        await generator.run(google_data, mapper_data, final_attempt=False)
        call_args = generator._call_openai.call_args
        assert call_args.kwargs["temperature"] == 0.7
        
        # Reset mock
        generator._call_openai.reset_mock()
        
        # Test final attempt (should use temperature=0)
        await generator.run(google_data, mapper_data, final_attempt=True)
        call_args = generator._call_openai.call_args
        assert call_args.kwargs["temperature"] == 0.0


class TestOrchestratorRetryLogic:
    """Test orchestrator retry logic is correct"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_empty_html_no_double_retry(self):
        """Orchestrator should NOT add extra retry when generator returns empty HTML"""
        # This is harder to test without full integration
        # But we can verify the code path exists
        
        mock_client = Mock()
        orchestrator = OrchestratorAgent(api_key="sk-test123")
        
        # Patch the generator to return empty HTML
        orchestrator.generator.run = AsyncMock(return_value={"html": "", "meta": {}})
        
        # Patch mapper
        orchestrator.mapper.run = AsyncMock(return_value={
            "business_summary": "Test",
            "assats": {}
        })
        
        google_data = {"name": "Test", "place_id": "123"}
        
        # Should fail after max_attempts (2) without extra retries
        with pytest.raises(AgentError) as exc_info:
            with patch("agents.mcp_client.MCPClient"):
                await orchestrator.orchestrate(google_data, max_attempts=2, session_id="test")
        
        # Verify error is about empty HTML
        assert "empty html" in str(exc_info.value).lower()
        
        # Verify generator was called exactly 2 times (max_attempts=2)
        # NOT 4 times (2 × 2 with double-retry)
        assert orchestrator.generator.run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_format_standardization(self):
        """Test that errors are formatted consistently for generator"""
        mock_client = Mock()
        orchestrator = OrchestratorAgent(api_key="sk-test123")
        
        # Test pre-write error formatting
        pre_write_error = "SECURITY VIOLATION: inline handlers detected"
        formatted = orchestrator._format_error_for_generator("pre_write", pre_write_error)
        assert formatted == pre_write_error  # Pre-write errors pass through
        
        # Test MCP error formatting
        mcp_error = {
            "id": "SEC.INLINE_HANDLER",
            "severity": "error",
            "hint": "Remove inline handlers",
            "where": "index.html:45"
        }
        formatted = orchestrator._format_error_for_generator("mcp", mcp_error)
        assert "[ERROR]" in formatted
        assert "SEC.INLINE_HANDLER" in formatted
        assert "Remove inline handlers" in formatted
        assert "index.html:45" in formatted


class TestRetryCountVerification:
    """Integration-style tests to verify total retry counts"""
    
    @pytest.mark.asyncio
    async def test_max_attempts_2_means_2_calls(self):
        """With max_attempts=2, generator should be called at most 2 times"""
        mock_client = Mock()
        orchestrator = OrchestratorAgent(api_key="sk-test123")
        
        # Track generator call count
        call_count = 0
        
        async def mock_generator_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Always fail with schema error
            raise AgentError("Schema validation failed")
        
        orchestrator.generator.run = mock_generator_run
        
        # Patch mapper
        orchestrator.mapper.run = AsyncMock(return_value={
            "business_summary": "Test",
            "assats": {}
        })
        
        google_data = {"name": "Test", "place_id": "123"}
        
        # Should fail after 2 attempts
        with pytest.raises(AgentError):
            with patch("agents.mcp_client.MCPClient"):
                await orchestrator.orchestrate(google_data, max_attempts=2, session_id="test")
        
        # Verify EXACTLY 2 generator calls (not 4, 6, 8, or 12)
        assert call_count == 2, f"Expected 2 generator calls but got {call_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

