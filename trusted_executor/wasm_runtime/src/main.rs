use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use prometheus::{Encoder, TextEncoder, Registry, Counter};

static SERVICE_NAME: &str = "wasm_runtime";

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

#[post("/wasm_runtime/stub")]
async fn stub(body: web::Json<serde_json::Value>) -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "ok",
        "service": SERVICE_NAME,
        "input": body.into_inner()
    }))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let port: u16 = std::env::var("PORT").unwrap_or_else(|_| "8400".to_string()).parse().unwrap();
    println!("{} listening on port {}", SERVICE_NAME, port);

    HttpServer::new(|| {
        App::new()
            .service(health)
            .service(metrics)
            .service(stub)
    })
    .bind(("0.0.0.0", port))?
    .run()
    .await
}
