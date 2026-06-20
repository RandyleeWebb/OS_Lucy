#!/usr/bin/env python3
"""
HyperGraphRAG v5 - Main Entry Point

This is the main entry point for the HyperGraphRAG v5 system.
It provides a command-line interface for running different components.

Usage:
    python main.py serve                    # Start the API server
    python main.py setup                    # Run demo setup
    python main.py demo                     # Run demo scenarios
    python main.py benchmark                # Run performance benchmarks
    python main.py shell                    # Interactive shell
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import config
from src.database.graph_manager import GraphManager
from src.api.graphrag_api import app
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_setup():
    """Run the demo setup"""
    logger.info("Running HyperGraphRAG v5 setup...")
    
    try:
        from demo.setup_demo import setup_demo
        success = await setup_demo()
        
        if success:
            logger.info("✅ Setup completed successfully!")
            logger.info("🚀 Start the server with: python main.py serve")
        else:
            logger.error("❌ Setup failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Setup error: {e}")
        sys.exit(1)

def run_server(host="0.0.0.0", port=8000, reload=False):
    """Start the FastAPI server"""
    logger.info(f"🚀 Starting HyperGraphRAG v5 API server on {host}:{port}")
    logger.info(f"📖 API Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(
        "src.api.graphrag_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

async def run_demo():
    """Run demo scenarios"""
    logger.info("🎭 Running HyperGraphRAG v5 demo scenarios...")
    
    try:
        # Import demo components
        from demo.demo_data import DEMO_SCENARIOS, DEMO_QUERIES
        from src.database.graph_manager import GraphManager
        from src.embeddings.embedding_service import EmbeddingService
        
        # Initialize components
        graph_manager = GraphManager()
        if not graph_manager.connect():
            logger.error("Failed to connect to database")
            return
        
        embedding_service = EmbeddingService()
        
        # Run demo queries
        for i, query_data in enumerate(DEMO_QUERIES):
            logger.info(f"\n📝 Query {i+1}: {query_data['query']}")
            
            try:
                # Generate query embedding
                query_vector = embedding_service.encode_text(query_data['query'])
                
                # Perform semantic search
                results = graph_manager.semantic_graph_traversal(
                    query=query_data['query'],
                    access_level=query_data.get('required_access_level', 0),
                    max_depth=3
                )
                
                logger.info(f"🎯 Found {len(results)} results")
                for j, result in enumerate(results[:3]):
                    logger.info(f"  {j+1}. Path depth: {result['depth']}")
                
            except Exception as e:
                logger.error(f"❌ Query failed: {e}")
        
        logger.info("\n✅ Demo scenarios completed!")
        
    except Exception as e:
        logger.error(f"Demo error: {e}")

async def run_benchmark():
    """Run performance benchmarks"""
    logger.info("🏃 Running HyperGraphRAG v5 benchmarks...")
    
    try:
        import time
        from src.database.graph_manager import GraphManager
        from src.embeddings.embedding_service import EmbeddingService
        from demo.demo_data import DEMO_QUERIES
        
        # Initialize components
        graph_manager = GraphManager()
        if not graph_manager.connect():
            logger.error("Failed to connect to database")
            return
        
        embedding_service = EmbeddingService()
        
        # Benchmark queries
        results = []
        
        for query_data in DEMO_QUERIES:
            query = query_data['query']
            
            # Benchmark vector generation
            start_time = time.time()
            query_vector = embedding_service.encode_text(query)
            vector_time = time.time() - start_time
            
            # Benchmark semantic search
            start_time = time.time()
            search_results = graph_manager.semantic_graph_traversal(
                query=query,
                access_level=0,
                max_depth=3
            )
            search_time = time.time() - start_time
            
            results.append({
                'query': query[:50] + "...",
                'vector_time_ms': vector_time * 1000,
                'search_time_ms': search_time * 1000,
                'total_time_ms': (vector_time + search_time) * 1000,
                'result_count': len(search_results)
            })
        
        # Print benchmark results
        logger.info("\n📊 Benchmark Results:")
        logger.info("=" * 80)
        logger.info(f"{'Query':<50} {'Vector':<10} {'Search':<10} {'Total':<10} {'Results':<10}")
        logger.info("=" * 80)
        
        for result in results:
            logger.info(
                f"{result['query']:<50} "
                f"{result['vector_time_ms']:<10.2f} "
                f"{result['search_time_ms']:<10.2f} "
                f"{result['total_time_ms']:<10.2f} "
                f"{result['result_count']:<10}"
            )
        
        # Calculate averages
        avg_vector = sum(r['vector_time_ms'] for r in results) / len(results)
        avg_search = sum(r['search_time_ms'] for r in results) / len(results)
        avg_total = sum(r['total_time_ms'] for r in results) / len(results)
        
        logger.info("=" * 80)
        logger.info(f"{'AVERAGE':<50} {avg_vector:<10.2f} {avg_search:<10.2f} {avg_total:<10.2f} {'-':<10}")
        
    except Exception as e:
        logger.error(f"Benchmark error: {e}")

def run_shell():
    """Run interactive shell"""
    logger.info("🐚 Starting HyperGraphRAG v5 interactive shell...")
    
    try:
        import code
        from src.database.graph_manager import GraphManager
        from src.embeddings.embedding_service import EmbeddingService
        from src.art.art_engine import ARTEngine
        from demo.demo_data import DEMO_DOCUMENTS, DEMO_QUERIES
        
        # Initialize components
        graph_manager = GraphManager()
        graph_manager.connect()
        graph_manager.initialize_schema()
        
        embedding_service = EmbeddingService()
        art_engine = ARTEngine(graph_manager)
        
        # Create interactive namespace
        namespace = {
            'graph_manager': graph_manager,
            'embedding_service': embedding_service,
            'art_engine': art_engine,
            'DEMO_DOCUMENTS': DEMO_DOCUMENTS,
            'DEMO_QUERIES': DEMO_QUERIES,
            'config': config,
        }
        
        # Start interactive shell
        banner = """
╔══════════════════════════════════════════════════════════════╗
║           HyperGraphRAG v5 Interactive Shell                  ║
╠══════════════════════════════════════════════════════════════╣
║ Available objects:                                            ║
║   - graph_manager: Graph database interface                   ║
║   - embedding_service: Semantic embeddings                    ║
║   - art_engine: Automatic reasoning system                    ║
║   - DEMO_DOCUMENTS: Sample documents                          ║
║   - DEMO_QUERIES: Sample queries                              ║
║   - config: System configuration                              ║
║                                                                ║
║ Example:                                                       ║
║   results = graph_manager.semantic_graph_traversal(           ║
║       "What is GraphRAG?", access_level=0, max_depth=3)       ║
║   print(f"Found {len(results)} results")                      ║
╚══════════════════════════════════════════════════════════════╝
"""
        
        code.interact(banner=banner, local=namespace)
        
    except Exception as e:
        logger.error(f"Shell error: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="HyperGraphRAG v5 - Advanced GraphRAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py serve                    # Start API server
  python main.py serve --host 127.0.0.1   # Start on localhost
  python main.py setup                    # Run demo setup
  python main.py demo                     # Run demo scenarios
  python main.py benchmark                # Run benchmarks
  python main.py shell                    # Interactive shell
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start the API server')
    serve_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    serve_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    serve_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Run demo setup')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run demo scenarios')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Run performance benchmarks')
    
    # Shell command
    shell_parser = subparsers.add_parser('shell', help='Interactive shell')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'serve':
        run_server(args.host, args.port, args.reload)
    elif args.command == 'setup':
        asyncio.run(run_setup())
    elif args.command == 'demo':
        asyncio.run(run_demo())
    elif args.command == 'benchmark':
        asyncio.run(run_benchmark())
    elif args.command == 'shell':
        run_shell()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()