Compilation Worker (HLL -> WASM)
================================

This directory will host the compilation scaffolds to transform high-level languages
into WASM artifacts. Options:

- Python -> WASM: pyodide toolchain (heavy), or project-specific micro-transpiler.
- Rust -> WASM: use wasm-pack or cargo + target wasm32-unknown-unknown + wasm-bindgen.
- JS -> WASM: QuickJS/WASM toolchains or AssemblyScript.

For now, we prefer models to emit WASM directly. A compilation worker can be added
as an optional service that accepts code, compiles to WASM, and returns base64.
