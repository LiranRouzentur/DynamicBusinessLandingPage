"""Simple test script to verify the agents build works with Responses API changes (no MCP validation)"""
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
    """Test the build with sample data (stop after generator, skip MCP validation)"""
    print("\n" + "="*60)
    print("Testing Agents Build with Responses API (No MCP)")
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
        # Filter out unicode characters for Windows console
        try:
            print(f"[{phase}] {message}")
        except UnicodeEncodeError:
            print(f"[{phase}] {message.encode('ascii', 'ignore').decode('ascii')}")
    
    # Run orchestration (stop after generator to skip MCP validation)
    print("\n[*] Starting orchestration (stopping after generation)...\n")
    
    try:
        result = await orchestrator.orchestrate(
            google_data=google_data,
            interactivity_tier="enhanced",
            max_attempts=2,  # Limit attempts for testing
            asset_budget=3,
            event_callback=event_callback,
            session_id="test_session_no_mcp",
            stop_after="generator"  # Skip MCP validation
        )
        
        print("\n" + "="*60)
        print("Build Result")
        print("="*60 + "\n")
        
        # Handle test mode (stop_after parameter)
        if result.get("test_mode"):
            print("[OK] Test mode: stopped after", result.get("stopped_after"))
            
            # Check mapper output
            mapper_out = result.get("mapper_out", {})
            if mapper_out:
                print(f"[OK] Mapper output: {len(mapper_out.get('business_summary', ''))} char summary")
            
            # Check generator output
            generator_out = result.get("generator_out", {})
            if generator_out:
                html = generator_out.get("html", "")
                meta = generator_out.get("meta", {})
                print(f"[OK] Generator output: {len(html)} characters")
                print(f"[*] Theme: {meta.get('theme', 'N/A')}")
                
                # Check for qa_gate_errors in meta
                if "qa_gate_errors" in meta:
                    print(f"[!] QA gate errors in meta: {meta['qa_gate_errors']}")
                else:
                    print("[OK] No QA gate errors in meta (all gates passed or retries exhausted)")
                
                # Save output for inspection
                output_dir = Path(__file__).parent / "test_output"
                output_dir.mkdir(exist_ok=True)
                
                # Save full result
                result_file = output_dir / "test_result_no_mcp.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "test_mode": True,
                        "stopped_after": result.get("stopped_after"),
                        "mapper_out": {
                            "business_summary": mapper_out.get("business_summary", "N/A"),
                            "has_logo": bool(mapper_out.get("assats", {}).get("logo_url")),
                            "business_images": len(mapper_out.get("assats", {}).get("business_images_urls", [])),
                            "stock_images": len(mapper_out.get("assats", {}).get("stock_images_urls", []))
                        },
                        "generator_out": {
                            "html_length": len(html),
                            "meta": meta
                        }
                    }, f, indent=2, ensure_ascii=False)
                print(f"[*] Full result saved to: {result_file}")
                
                # Save HTML if present
                if html:
                    html_file = output_dir / "test_output_no_mcp.html"
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                    print(f"[*] HTML saved to: {html_file}")
                    
                    # Create preview
                    preview_file = output_dir / "test_preview_no_mcp.html"
                    escaped_html = html.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
                    preview_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Build Preview (No MCP)</title>
    <style>
        body {{ margin: 0; padding: 0; font-family: system-ui; background: #f5f5f5; }}
        .header {{ background: #333; color: white; padding: 1rem; text-align: center; }}
        .iframe-container {{ margin: 20px auto; max-width: 1400px; height: calc(100vh - 100px); 
                            border: 2px solid #ccc; border-radius: 8px; background: white; overflow: hidden; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.5rem; margin: 0.25rem; 
                  background: #4CAF50; color: white; border-radius: 4px; font-size: 0.875rem; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Build Preview - Responses API</h1>
        <p>Generated with OpenAI Responses API + Quality Gates + Stock Image Fallback</p>
        <div>
            <span class="badge">Responses API Mode</span>
            <span class="badge">Quality Gates Enabled</span>
            <span class="badge">Stock Fallback Active</span>
        </div>
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
                    print(f"\n[*] Open {preview_file} in your browser to view the generated page!")
                
                print("\n[OK] Test completed successfully!")
                return True
            else:
                print("[X] No generator output found")
                return False
        else:
            print("[X] Expected test mode but got full orchestration result")
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

