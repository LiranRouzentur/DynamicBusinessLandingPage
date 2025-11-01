"""Simple test script to verify the agents build works with Responses API changes"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent))

from app.orchestrator.orchestrator_agent import OrchestratorAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv(Path(__file__).parent / ".env")

async def test_build():
    """Test the build with sample data"""
    print("\n" + "="*60)
    print("Testing Agents Build with Responses API")
    print("="*60 + "\n")
    
    # Load test data from simple_request.json
    simple_request_path = Path(__file__).parent.parent / "simple_openai_server" / "simple_request.json"
    
    if not simple_request_path.exists():
        print(f"[X] Test data not found at {simple_request_path}")
        return False
    
    with open(simple_request_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    google_data = test_data.get("google_data", {})
    
    print(f"[*] Loaded test data for: {google_data.get('name', 'N/A')}")
    print(f"[*] Business type: {google_data.get('primary_type', 'N/A')}")
    print(f"[*] Location: {google_data.get('formatted_address', 'N/A')}")
    print()
    
    # Create orchestrator
    try:
        orchestrator = OrchestratorAgent()
        print("[OK] Orchestrator initialized")
    except Exception as e:
        print(f"[X] Failed to initialize orchestrator: {e}")
        return False
    
    # Event callback for progress
    def event_callback(phase: str, message: str):
        print(f"[{phase}] {message}")
    
    # Run orchestration
    print("\n[*] Starting orchestration...\n")
    
    try:
        result = await orchestrator.orchestrate(
            google_data=google_data,
            interactivity_tier="enhanced",
            max_attempts=2,  # Limit attempts for testing
            asset_budget=3,
            event_callback=event_callback,
            session_id="test_session_001"
        )
        
        print("\n" + "="*60)
        print("Build Result")
        print("="*60 + "\n")
        
        if result.get("success"):
            print("[OK] Build completed successfully!")
            
            # Check for html output
            if "html" in result:
                html_length = len(result["html"])
                print(f"[OK] Generated HTML: {html_length} characters")
                
                # Check for quality gates
                qa_errors = result.get("qa_errors", [])
                if qa_errors:
                    print(f"[!] QA errors present: {qa_errors}")
                else:
                    print("[OK] All quality gates passed")
            else:
                print("[!] No HTML output in result")
            
            # Check metadata
            if "meta" in result:
                meta = result["meta"]
                print(f"[OK] Metadata: theme={meta.get('theme', 'N/A')}")
                if "qa_gate_errors" in meta:
                    print(f"[!] QA gate errors in meta: {meta['qa_gate_errors']}")
            
            # Save output for inspection
            output_dir = Path(__file__).parent / "test_output"
            output_dir.mkdir(exist_ok=True)
            
            # Save full result
            result_file = output_dir / "test_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "success": result.get("success"),
                    "meta": result.get("meta", {}),
                    "qa_errors": result.get("qa_errors", []),
                    "html_length": len(result.get("html", "")),
                    "mapper_summary": result.get("mapper_out", {}).get("business_summary", "N/A") if "mapper_out" in result else "N/A"
                }, f, indent=2, ensure_ascii=False)
            print(f"[*] Full result saved to: {result_file}")
            
            # Save HTML if present
            if "html" in result:
                html_file = output_dir / "test_output.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(result["html"])
                print(f"[*] HTML saved to: {html_file}")
                
                # Create preview
                preview_file = output_dir / "test_preview.html"
                escaped_html = result["html"].replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
                preview_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Build Preview</title>
    <style>
        body {{ margin: 0; padding: 0; font-family: system-ui; background: #f5f5f5; }}
        .header {{ background: #333; color: white; padding: 1rem; text-align: center; }}
        .iframe-container {{ margin: 20px auto; max-width: 1400px; height: calc(100vh - 100px); 
                            border: 2px solid #ccc; border-radius: 8px; background: white; overflow: hidden; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Build Preview - Responses API</h1>
        <p>Generated with OpenAI Responses API + Quality Gates + Stock Image Fallback</p>
    </div>
    <div class="iframe-container">
        <iframe id="preview" sandbox="allow-scripts allow-same-origin"></iframe>
    </div>
    <script>
        const html = `{escaped_html}`;
        document.getElementById('preview').setAttribute('srcdoc', html);
    </script>
</body>
</html>"""
                with open(preview_file, 'w', encoding='utf-8') as f:
                    f.write(preview_html)
                print(f"[*] Preview saved to: {preview_file}")
            
            print("\n[OK] Test completed successfully!")
            return True
            
        else:
            error = result.get("error", "Unknown error")
            print(f"[X] Build failed: {error}")
            return False
            
    except Exception as e:
        print(f"\n[X] Build failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("[X] OPENAI_API_KEY not found in environment")
        sys.exit(1)
    
    # Run test
    success = asyncio.run(test_build())
    sys.exit(0 if success else 1)

