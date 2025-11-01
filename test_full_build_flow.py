"""Test the full build flow end-to-end"""
import requests
import json
import time
import sys

# Test place_id - using a real Domino's Pizza location
TEST_PLACE_ID = "ChIJuzL4KZ5LHRURmodwHUMNVPQ"  # Domino's Pizza in Tel Aviv

def test_build_flow():
    """Test the full build flow"""
    print("\n" + "="*70)
    print("Testing Full Build Flow")
    print("="*70 + "\n")
    
    backend_url = "http://localhost:8000"
    
    # Step 1: Start build
    print("[1/4] Starting build...")
    try:
        response = requests.post(
            f"{backend_url}/api/build",
            json={"place_id": TEST_PLACE_ID},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        session_id = data.get("session_id")
        print(f"     [OK] Build started | session_id: {session_id}")
    except Exception as e:
        print(f"     [ERROR] Failed to start build: {e}")
        return False
    
    # Step 2: Monitor progress via SSE
    print(f"\n[2/4] Monitoring progress (session: {session_id})...")
    events_received = []
    error_occurred = False
    
    try:
        sse_url = f"{backend_url}/sse/progress/{session_id}"
        response = requests.get(sse_url, stream=True, timeout=350)  # 5 min timeout + buffer
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                    phase = event_data.get('phase')
                    detail = event_data.get('detail', '')
                    
                    events_received.append(event_data)
                    
                    # Print important events (sanitize Unicode for Windows console)
                    if phase in ['FETCHING', 'ORCHESTRATING', 'GENERATING', 'QA', 'READY', 'ERROR']:
                        # Replace Unicode characters with ASCII equivalents
                        safe_detail = detail.replace('✓', '[OK]').replace('✗', '[ERROR]').replace('•', '*')
                        print(f"     [{phase}] {safe_detail[:100]}")
                    
                    if phase == 'ERROR':
                        error_occurred = True
                        print(f"\n     [ERROR] Build failed: {detail}")
                        break
                    
                    if phase == 'READY':
                        print(f"\n     [OK] Build completed successfully!")
                        break
                        
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"     [ERROR] SSE stream error: {e}")
        error_occurred = True
    
    if error_occurred:
        return False
    
    # Step 3: Check result
    print(f"\n[3/4] Checking result...")
    try:
        result_response = requests.get(
            f"{backend_url}/api/result/{session_id}",
            timeout=10
        )
        result_response.raise_for_status()
        html_content = result_response.text
        print(f"     [OK] Result retrieved | HTML length: {len(html_content)} chars")
        
        # Verify it's valid HTML
        if html_content.startswith('<!DOCTYPE html>') or html_content.startswith('<html'):
            print(f"     [OK] Valid HTML detected")
        else:
            print(f"     [WARN] HTML might be invalid (doesn't start with <!DOCTYPE> or <html)")
            
    except Exception as e:
        print(f"     [ERROR] Failed to get result: {e}")
        return False
    
    # Step 4: Summary
    print(f"\n[4/4] Summary:")
    print(f"     - Events received: {len(events_received)}")
    print(f"     - Final phase: {events_received[-1].get('phase') if events_received else 'N/A'}")
    print(f"     - HTML generated: {len(html_content)} chars")
    
    print("\n" + "="*70)
    print("[OK] Full build flow test completed successfully!")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    success = test_build_flow()
    sys.exit(0 if success else 1)

