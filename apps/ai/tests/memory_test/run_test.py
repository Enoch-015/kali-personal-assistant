"""
Main test runner for the L1/L2 memory cache benchmark.
Orchestrates preloading, benchmarking, and visualization.
"""

import asyncio
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_preload():
    """Pre-load Graphiti data into L2 cache."""
    from preload_cache import preload_l2_cache
    
    logger.info("=" * 60)
    logger.info("PHASE 1: PRELOADING L2 CACHE")
    logger.info("=" * 60)
    
    await preload_l2_cache()


async def run_benchmark(num_trials: int = 5, visualize: bool = True):
    """Run the A/B benchmark comparing L1 cache vs direct Graphiti."""
    from benchmark import run_full_benchmark
    
    logger.info("=" * 60)
    logger.info("PHASE 2: RUNNING A/B BENCHMARK")
    logger.info("L1/L2 Cache vs Direct Graphiti Comparison")
    logger.info("=" * 60)
    
    # Run the full benchmark which handles initialization, trials, and visualization
    await run_full_benchmark()


async def run_verify():
    """Verify cache contents."""
    from preload_cache import verify_l2_cache
    
    logger.info("=" * 60)
    logger.info("VERIFYING L2 CACHE CONTENTS")
    logger.info("=" * 60)
    
    await verify_l2_cache()


async def main():
    """Main entry point."""
    
    usage = """
Memory Cache Benchmark Runner
==============================

Usage:
    python run_test.py <command> [options]

Commands:
    preload    - Pre-load L2 cache with tagged episodes from Graphiti data
    verify     - Verify L2 cache contents
    benchmark  - Run benchmark with default 5 trials
    full       - Run preload + benchmark (full test)
    
Options for 'benchmark' and 'full':
    --trials=N     Number of trials (default: 5)
    --no-viz       Skip visualization

Examples:
    python run_test.py preload
    python run_test.py benchmark --trials=10
    python run_test.py full --trials=3
    """
    
    if len(sys.argv) < 2:
        print(usage)
        return
    
    command = sys.argv[1].lower()
    
    # Parse options
    num_trials = 5
    visualize = True
    
    for arg in sys.argv[2:]:
        if arg.startswith("--trials="):
            try:
                num_trials = int(arg.split("=")[1])
            except ValueError:
                print(f"Invalid trials value: {arg}")
                return
        elif arg == "--no-viz":
            visualize = False
    
    # Execute command
    if command == "preload":
        await run_preload()
    
    elif command == "verify":
        await run_verify()
    
    elif command == "benchmark":
        await run_benchmark(num_trials=num_trials, visualize=visualize)
    
    elif command == "full":
        await run_preload()
        print("\n" + "=" * 60)
        print("PAUSING BEFORE BENCHMARK...")
        print("=" * 60)
        await asyncio.sleep(1)
        await run_benchmark(num_trials=num_trials, visualize=visualize)
    
    else:
        print(f"Unknown command: {command}")
        print(usage)


if __name__ == "__main__":
    asyncio.run(main())
