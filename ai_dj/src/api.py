import os
import uuid
import subprocess
import hmac
import hashlib
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import List

# Secret key for HMAC (in production use env variable secure storage)
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

app = FastAPI(title="Lucy AI‑DJ Backend API")

# Simple user model with roles
class User(BaseModel):
    username: str
    roles: List[str] = []

# In‑memory user store (replace with DB in production)
USER_DB = {
    "admin": {"password": "admin", "roles": ["admin", "builder", "validator"]},
    "Lucy": {"password": "[Jasmine@17", "roles": ["builder"]},
}

def verify_password(plain_password: str, stored_password: str) -> bool:
    # In real code use hashing (bcrypt, argon2)
    return plain_password == stored_password

def authenticate_user(username: str, password: str):
    user = USER_DB.get(username)
    if not user or not verify_password(password, user["password"]):
        return None
    return User(username=username, roles=user["roles"])

def create_access_token(data: dict):
    to_encode = data.copy()
    # No expiration handling for brevity
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
async def login(form_data: dict = Body(...)):
    # Expecting JSON body: {'username': str, 'password': str}
    username = form_data.get("username")
    password = form_data.get("password")
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username, "roles": user.roles})
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise credentials_exception
        token_data = User(username=username, roles=roles)
    except JWTError:
        raise credentials_exception
    return token_data

def role_required(required_role: str):
    async def role_checker(user: User = Depends(get_current_user)):
        if required_role not in user.roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return role_checker

@app.get("/tracks", dependencies=[Depends(role_required("builder"))])
async def list_tracks():
    # Placeholder: In production query SQLite library index DB
    return [{"id": 1, "title": "Sample Track", "artist": "Artist"}]

# Additional endpoints (recommendations, AI skits, etc.) would be added here.

class SkitRequest(BaseModel):
    agent_id: str
    script: str
    voice: str | None = None
    capability_token: str

def _verify_capability_token(agent_id: str, token: str) -> bool:
    """Validate HMAC token for the given agent."""
    secret = os.getenv("SKIT_HMAC_SECRET", "default-secret")
    expected = hmac.new(secret.encode(), agent_id.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)

@app.post("/skit", dependencies=[Depends(role_required("builder"))])
async def create_skit(request: SkitRequest):
    # Verify token
    if not _verify_capability_token(request.agent_id, request.capability_token):
        raise HTTPException(status_code=403, detail="Invalid capability token")
    # Generate unique skit ID and paths
    skit_id = uuid.uuid4().hex
    base_dir = Path(__file__).resolve().parents[2]
    incoming_dir = base_dir / "skits" / "incoming"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    # Call TTS generation script
    script_path = base_dir / "scripts" / "generate_skit.py"
    proc = subprocess.run(
        ["python", str(script_path), request.script],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {proc.stderr}")
    # Locate generated file (script creates <topic>.mp3 in skits folder)
    generated_file = base_dir / "skits" / f"{request.script.replace(' ', '_')}.mp3"
    if not generated_file.is_file():
        raise HTTPException(status_code=500, detail="Generated audio file not found")
    target_path = incoming_dir / f"{skit_id}.wav"
    generated_file.rename(target_path)
    # Log audit event
    audit_log = base_dir / "audit_events.log"
    with audit_log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()}Z {{\"event\": \"skit_created\", \"skit_id\": \"{skit_id}\", \"agent_id\": \"{request.agent_id}\"}}\n")
    return {"status": "queued", "skit_id": skit_id, "path": str(target_path)}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
