from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import ast

SERVICE_NAME = "ast_validator"

app = FastAPI(title=f"Lucy {SERVICE_NAME}")

http_requests_total = Counter(
    f"{SERVICE_NAME}_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

@app.get("/health")
async def health():
    http_requests_total.labels("GET", "/health", 200).inc()
    return {"up": True, "service": SERVICE_NAME, "version": "0.1.0"}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

class AstRequest(BaseModel):
    code: str

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.reasons = []

    def visit_Call(self, node):
        # Check direct function calls like eval(), exec(), open()
        if isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "open"}:
                self.reasons.append(f"Forbidden builtin call: {node.func.id}")
        
        # Check attribute calls like os.system(), subprocess.run()
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                func_name = node.func.attr
                if module_name == "os" and func_name in {"system", "popen", "spawn"}:
                    self.reasons.append(f"Forbidden OS call: os.{func_name}")
                if module_name == "subprocess":
                    self.reasons.append(f"Forbidden subprocess call: subprocess.{func_name}")
                if module_name == "socket":
                    self.reasons.append(f"Forbidden socket call: socket.{func_name}")

        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in {"os", "subprocess", "socket", "sys"}:
                self.reasons.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in {"os", "subprocess", "socket", "sys"}:
            self.reasons.append(f"Forbidden import from: {node.module}")
        self.generic_visit(node)

@app.post("/ast/validate")
async def validate(req: AstRequest):
    http_requests_total.labels("POST", "/ast/validate", 200).inc()
    if not req.code.strip():
        return {"valid": True, "reasons": []}
        
    try:
        tree = ast.parse(req.code)
    except SyntaxError as e:
        return {"valid": False, "reasons": [f"Syntax error: {str(e)}"]}
        
    visitor = SecurityVisitor()
    visitor.visit(tree)
    
    if visitor.reasons:
        return {"valid": False, "reasons": visitor.reasons}
        
    return {"valid": True, "reasons": []}
