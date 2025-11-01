"""MCP server via TCP socket (isolated service)"""
import argparse, json, os, sys, pathlib, socket, threading
from tools.bundle import Bundle
from tools.qa import QA
from tools.net import Net
from tools.util import Util
from tools.adaptive_manager import AdaptiveManager

class SocketRPC:
    """RPC server over TCP socket"""
    def __init__(self, host='127.0.0.1', port=8003):
        self.host = host
        self.port = port
        self.handlers = {}
        self.sock = None
        
    def register(self, name, fn):
        self.handlers[name] = fn
    
    def _handle_client(self, client_sock, addr):
        """Handle a single client connection"""
        try:
            buffer = ""
            while True:
                data = client_sock.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                
                # Process complete lines (JSON-RPC messages)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip():
                        continue
                    
                    try:
                        req = json.loads(line)
                        method = req.get("method")
                        params = req.get("params", {})
                        req_id = req.get("id")
                        
                        if method in self.handlers:
                            result = self.handlers[method](params)
                            response = {"id": req_id, "result": result}
                        else:
                            response = {"id": req_id, "error": {"message": f"Unknown method: {method}"}}
                        
                        client_sock.sendall((json.dumps(response) + "\n").encode('utf-8'))
                    except json.JSONDecodeError as e:
                        error_resp = {"id": None, "error": {"message": f"Invalid JSON: {str(e)}"}}
                        client_sock.sendall((json.dumps(error_resp) + "\n").encode('utf-8'))
                    except Exception as e:
                        error_resp = {"id": req_id if 'req_id' in locals() else None, 
                                     "error": {"message": str(e)}}
                        client_sock.sendall((json.dumps(error_resp) + "\n").encode('utf-8'))
        except Exception as e:
            print(f"[MCP Server] Client {addr} error: {e}", file=sys.stderr)
        finally:
            client_sock.close()
    
    def run(self):
        """Start TCP server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        
        print(f"[MCP Server] Listening on {self.host}:{self.port}", file=sys.stderr)
        sys.stderr.flush()
        
        while True:
            try:
                client_sock, addr = self.sock.accept()
                print(f"[MCP Server] Client connected: {addr}", file=sys.stderr)
                sys.stderr.flush()
                # Handle each client in a separate thread
                thread = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
                thread.start()
            except KeyboardInterrupt:
                print("[MCP Server] Shutting down...", file=sys.stderr)
                break
            except Exception as e:
                print(f"[MCP Server] Error: {e}", file=sys.stderr)
                continue

def workspace_root():
    """Get workspace root - supports per-session workspaces via env var"""
    # Default to storage/workspace if not set
    default_workspace = pathlib.Path(__file__).parent / "storage" / "workspace"
    root = pathlib.Path(os.getenv("WORKSPACE_ROOT", str(default_workspace))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def cache_root():
    root = pathlib.Path(os.getenv("CACHE_ROOT","./mcp/storage/cache")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["bundle","all"], default="all")
    ap.add_argument("--host", default="127.0.0.1", help="Bind address")
    ap.add_argument("--port", type=int, default=8003, help="TCP port")
    args = ap.parse_args()

    root = workspace_root()
    cache_dir = cache_root()
    util = Util(root)
    
    # Initialize adaptive manager
    mcp_dir = pathlib.Path(__file__).parent.resolve()
    policies_dir = mcp_dir / "policies"
    adaptive_manager = AdaptiveManager(policies_dir)
    
    # Get allowed domains from adaptive manager
    allowed_domains = adaptive_manager.get_allowed_domains()
    
    # Initialize network layer with adaptive features
    net = Net(
        allowlist=allowed_domains,
        cache_root=cache_dir,
        adaptive_manager=adaptive_manager,
        circuit_threshold=5,
        cooldown_s=60
    )
    
    # Get policy file paths
    image_limits_path = os.getenv("IMAGE_LIMITS_JSON", str(policies_dir / "image_limits.json"))
    csp_template_path = os.getenv("CSP_TEMPLATE", str(policies_dir / "csp_default.txt"))
    
    # Load initial policies (adaptive manager will handle hot-reload)
    image_limits = util.load_json(image_limits_path)
    csp_template = util.read_text(csp_template_path)

    rpc = SocketRPC(host=args.host, port=args.port)

    if args.profile in ("bundle","all"):
        bundle = Bundle(root, util, csp_template, adaptive_manager)
        qa = QA(root, util, image_limits, adaptive_manager, cache_dir)
        rpc.register("bundle.write_files", bundle.write_files)
        rpc.register("bundle.inject_comment", bundle.inject_comment)
        rpc.register("qa.validate_static_bundle", qa.validate_static_bundle)
        rpc.register("util.hash_dir", util.hash_dir)

    rpc.register("net.head", net.head)
    rpc.run()

if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED","1")
    main()

