use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use prometheus::{Encoder, TextEncoder, Registry, Counter};
use serde::{Deserialize, Serialize};
use serde_json::Value;

static SERVICE_NAME: &str = "executor_api";

#[derive(Deserialize, Debug)]
struct ExecuteRequest {
    intent_id: String,
    action: String,
    parameters: Value,
    timestamp: String,
    metadata: Value,
}

#[derive(Serialize)]
struct ExecuteResponse {
    status: String,
    intent_id: String,
    result: Value,
    fuel_used: u64,
    memory_pages: u64,
}

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "up": true,
        "service": SERVICE_NAME,
        "version": "0.1.0"
    }))
}

#[get("/metrics")]
async fn metrics() -> impl Responder {
    let registry = Registry::new();
    let counter = Counter::new(format!("{}_requests_total", SERVICE_NAME), "Total requests").unwrap();
    registry.register(Box::new(counter.clone())).unwrap();
    counter.inc();

    let encoder = TextEncoder::new();
    let mut buffer = Vec::new();
    encoder.encode(&registry.gather(), &mut buffer).unwrap();

    HttpResponse::Ok()
        .content_type("text/plain; charset=utf-8")
        .body(buffer)
}

#[post("/executor/execute")]
async fn execute(req: web::Json<ExecuteRequest>) -> impl Responder {
    // Echo the action and params back
    let response = ExecuteResponse {
        status: "success".to_string(),
        intent_id: req.intent_id.clone(),
        result: serde_json::json!({
            "executed_action": req.action,
            "echo_params": req.parameters
        }),
        fuel_used: 1500,
        memory_pages: 2,
    };

    HttpResponse::Ok().json(response)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let port: u16 = std::env::var("PORT").unwrap_or_else(|_| "8403".to_string()).parse().unwrap();
    println!("{} listening on port {}", SERVICE_NAME, port);

    HttpServer::new(|| {
        App::new()
            .service(health)
            .service(metrics)
            .service(execute)
    })
    .bind(("0.0.0.0", port))?
    .run()
    .await
}
