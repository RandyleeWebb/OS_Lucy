//! Security Fabric core library

use hmac::{Hmac, Mac};
use sha2::Sha256;
use serde::{Serialize, Deserialize};
use parking_lot::RwLock;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Token {
    pub agent_id: String,
    pub scopes: Vec<String>,
    pub issued_at: u64,
    pub expires_at: u64,
    pub signature: String,
}

pub struct TokenService {
    secret: Vec<u8>,
    // In‑memory revocation list (could be persisted)
    revoked: RwLock<HashMap<String, bool>>, // token signature -> revoked
}

impl TokenService {
    pub fn new(secret: Vec<u8>) -> Self {
        Self { secret, revoked: RwLock::new(HashMap::new()) }
    }

    pub fn issue_token(&self, agent_id: &str, scopes: Vec<String>, ttl_secs: u64) -> Token {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        let expires = now + ttl_secs;
        let payload = serde_json::json!({
            "agent_id": agent_id,
            "scopes": scopes,
            "issued_at": now,
            "expires_at": expires,
        })
        .to_string();
        let mut mac = HmacSha256::new_from_slice(&self.secret).expect("HMAC can take key of any size");
        mac.update(payload.as_bytes());
        let result = mac.finalize().into_bytes();
        let signature = hex::encode(result);
        Token {
            agent_id: agent_id.to_string(),
            scopes,
            issued_at: now,
            expires_at: expires,
            signature,
        }
    }

    pub fn verify(&self, token: &Token, required_scopes: &[&str]) -> Result<(), String> {
        // Check revocation
        if self.revoked.read().get(&token.signature).copied().unwrap_or(false) {
            return Err("Token revoked".into());
        }
        // Check expiry
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        if token.expires_at < now {
            return Err("Token expired".into());
        }
        // Re‑compute signature
        let payload = serde_json::json!({
            "agent_id": token.agent_id,
            "scopes": token.scopes,
            "issued_at": token.issued_at,
            "expires_at": token.expires_at,
        })
        .to_string();
        let mut mac = HmacSha256::new_from_slice(&self.secret).unwrap();
        mac.update(payload.as_bytes());
        let expected = hex::encode(mac.finalize().into_bytes());
        if expected != token.signature {
            return Err("Invalid signature".into());
        }
        // Scope check
        for &req in required_scopes {
            if !token.scopes.iter().any(|s| s == req) {
                return Err(format!("Missing required scope: {}", req));
            }
        }
        Ok(())
    }

    pub fn revoke(&self, signature: &str) {
        self.revoked.write().insert(signature.to_string(), true);
    }
}

// Placeholder for Wasmtime integration – load a Wasm module and enforce a sandbox profile
pub async fn run_wasm_with_profile(module_path: &str, profile: &str) -> Result<(), String> {
    use wasmtime::{Engine, Module, Store, Config};
    let mut config = Config::new();
    // Basic hardening – limit memory, disable wasi stdout/stderr unless profile allows
    config.consume_fuel(true);
    // Profile handling could be expanded – for now we just log the chosen profile
    println!("Running WASM module '{}' under profile '{}'", module_path, profile);
    let engine = Engine::new(&config).map_err(|e| e.to_string())?;
    let module = Module::from_file(&engine, module_path).map_err(|e| e.to_string())?;
    let mut store = Store::new(&engine, ());
    // Set a fuel budget to prevent runaway execution (e.g., 10 million instructions)
    store.add_fuel(10_000_000).map_err(|e| e.to_string())?;
    let instance = wasmtime::Instance::new(&mut store, &module, &[]).map_err(|e| e.to_string())?;
    // Assume the module exports a `_start` function (WASI convention)
    if let Ok(start) = instance.get_typed_func::<(), (), _>(&mut store, "_start") {
        start.call_async(&mut store, ()).await.map_err(|e| e.to_string())?;
    }
    Ok(())
}
