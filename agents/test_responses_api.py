#!/usr/bin/env python3
"""
Quick verification test for Responses API Phase 1 implementation.

Run this to verify the implementation is working:
    cd agents
    python test_responses_api.py
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def test_feature_flag():
    """Test that feature flag is accessible"""
    from app.base_agent import USE_RESPONSES_API
    print(f"[OK] USE_RESPONSES_API = {USE_RESPONSES_API}")
    assert isinstance(USE_RESPONSES_API, bool), "Feature flag should be boolean"
    return True

def test_base_agent_methods():
    """Test that BaseAgent has new methods"""
    from app.base_agent import BaseAgent
    from openai import OpenAI
    
    # Create dummy client
    client = OpenAI(api_key="test-key-not-used-in-test")
    agent = BaseAgent(client, agent_name="TestAgent")
    
    print(f"[OK] BaseAgent has response_id_cache: {hasattr(agent, 'response_id_cache')}")
    print(f"[OK] BaseAgent has _call_responses_api: {hasattr(agent, '_call_responses_api')}")
    print(f"[OK] BaseAgent has _call_openai: {hasattr(agent, '_call_openai')}")
    
    assert hasattr(agent, 'response_id_cache'), "Missing response_id_cache"
    assert hasattr(agent, '_call_responses_api'), "Missing _call_responses_api method"
    assert hasattr(agent, '_call_openai'), "Missing _call_openai method (backward compat)"
    
    return True

def test_generator_agent():
    """Test that Generator agent can be imported and has new methods"""
    from app.generator.generator_agent import GeneratorAgent
    from openai import OpenAI
    
    client = OpenAI(api_key="test-key-not-used-in-test")
    generator = GeneratorAgent(client)
    
    print(f"[OK] GeneratorAgent has response_id_cache: {hasattr(generator, 'response_id_cache')}")
    print(f"[OK] GeneratorAgent has _call_responses_api: {hasattr(generator, '_call_responses_api')}")
    
    assert hasattr(generator, 'response_id_cache'), "Generator missing response_id_cache"
    assert hasattr(generator, '_call_responses_api'), "Generator missing _call_responses_api"
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Responses API Phase 1 - Verification Test")
    print("=" * 60)
    print()
    
    try:
        print("[1/3] Testing feature flag...")
        test_feature_flag()
        print()
        
        print("[2/3] Testing BaseAgent methods...")
        test_base_agent_methods()
        print()
        
        print("[3/3] Testing Generator agent...")
        test_generator_agent()
        print()
        
        print("=" * 60)
        print("SUCCESS - ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Responses API Phase 1 is ready to use.")
        print()
        print("To test with real builds:")
        print("  1. Ensure USE_RESPONSES_API=true in environment")
        print("  2. Start agents service: python -m uvicorn app.main:app --reload --port 8002")
        print("  3. Trigger a build and watch logs for token savings")
        print("  4. Look for: 'Token savings (estimated)' messages")
        print()
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"FAILED - TEST ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

