import argparse, json, os, sys, pathlib
from tools.bundle import Bundle
from tools.qa import QA
from tools.net import Net
from tools.util import Util
from tools.adaptive_manager import AdaptiveManager

class StdioRPC:
    def __init__(self): self.handlers = {}
    def register(self, name, fn): self.handlers[name] = fn
    def run(self):
        for line in sys.stdin:
            if not line.strip(): continue
            req = json.loads(line)
            try:
                method = req["method"]; params = req.get("params", {})
                res = self.handlers[method](params)
                out = {"id": req.get("id"), "result": res}
            except Exception as e:
                out = {"id": req.get("id"), "error": {"message": str(e)}}
            sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()

def workspace_root():
    root = pathlib.Path(os.getenv("WORKSPACE_ROOT","./mcp/storage/workspace")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def cache_root():
    root = pathlib.Path(os.getenv("CACHE_ROOT","./mcp/storage/cache")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["bundle","all"], default="all")
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

    rpc = StdioRPC()

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
