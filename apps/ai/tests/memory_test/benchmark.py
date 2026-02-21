"""
Benchmark harness for memory cache performance testing.
Compares L1/L2 cache performance against direct Graphiti queries.

A/B Test Design:
- Mode A (Direct): Query goes straight to Graphiti, no cache involved
- Mode B (Cached): Query uses L1/L2 cache with Graphiti fallback

Measures:
- Speed: Time to first result (ms)
- Accuracy: Domain/facet match quality
- Efficiency: Cache hit rates and speedup factor
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from retriever import MemoryRetriever, RetrievalResult, create_retriever
from memory_cache import MemoryCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrialResult:
    """Single trial result for one mode (direct or cached)."""
    trial_id: int
    query: str
    expected_domain: str
    expected_facet: str
    mode: str  # "direct" or "cached"
    hit_source: str
    l1_count: int
    l2_count: int
    graphiti_count: int
    promoted_count: int
    demoted_count: int
    total_time_ms: float
    cache_time_ms: float
    graphiti_time_ms: float
    tagging_time_ms: float
    accuracy: float
    top_result_content: str = ""


@dataclass
class ComparisonTrial:
    """A/B comparison for a single query."""
    trial_id: int
    query: str
    expected_domain: str
    expected_facet: str
    expected_keywords: list[str]
    
    # Direct mode results (Graphiti only)
    direct_time_ms: float
    direct_accuracy: float
    direct_content_accuracy: float  # Keyword match score
    direct_result_count: int
    direct_top_content: str
    
    # Cached mode results (L1/L2 + Graphiti fallback)
    cached_time_ms: float
    cached_accuracy: float
    cached_content_accuracy: float  # Keyword match score  
    cached_hit_source: str
    cached_l1_count: int
    cached_l2_count: int
    cached_graphiti_count: int
    cached_top_content: str
    
    # Computed metrics
    speedup: float  # direct_time / cached_time
    accuracy_delta: float  # cached_accuracy - direct_accuracy
    content_accuracy_delta: float  # cached_content_accuracy - direct_content_accuracy


@dataclass
class BenchmarkSummary:
    """Summary statistics for the A/B benchmark."""
    total_trials: int
    
    # Direct mode (baseline)
    avg_direct_time_ms: float
    avg_direct_accuracy: float
    avg_direct_content_accuracy: float  # Keyword-based content match
    
    # Cached mode
    avg_cached_time_ms: float
    avg_cached_accuracy: float
    avg_cached_content_accuracy: float  # Keyword-based content match
    
    # Cache efficiency
    l1_hit_rate: float
    l2_hit_rate: float
    graphiti_fallback_rate: float
    
    # Comparison metrics
    avg_speedup: float
    max_speedup: float
    avg_accuracy_delta: float
    avg_content_accuracy_delta: float  # Cache vs Direct content match
    
    # Warm cache metrics (after L1 population)
    warm_l1_hit_rate: float
    warm_avg_speedup: float
    warm_content_accuracy: float  # Content accuracy when cache is warm


# Conversational test queries simulating voice assistant usage
# Each query includes expected_keywords from the actual Graphiti episodes for content matching
CONVERSATION_QUERIES = [
    # Health domain conversation
    {
        "query": "How much did I weigh last week?",
        "expected_domain": "health",
        "expected_facet": "weight_log",
        "expected_keywords": ["165 lbs", "weighed", "down 2 lbs"],
    },
    {
        "query": "Did I have any headaches recently?",
        "expected_domain": "health",
        "expected_facet": "symptom_tracking",
        "expected_keywords": ["migraine", "after lunch", "2:00 PM"],
    },
    {
        "query": "What was my last run time?",
        "expected_domain": "health",
        "expected_facet": "activity_log",
        "expected_keywords": ["5k run", "28 minutes", "Saturday"],
    },
    
    # Finance domain conversation
    {
        "query": "When is my car insurance payment due?",
        "expected_domain": "finance",
        "expected_facet": "bill_reminder",
        "expected_keywords": ["insurance renewal", "$600", "15th", "next month"],
    },
    {
        "query": "How much did I spend at Whole Foods?",
        "expected_domain": "finance",
        "expected_facet": "expense_log",
        "expected_keywords": ["$120", "groceries", "Whole Foods"],
    },
    {
        "query": "What's happening with my stock portfolio?",
        "expected_domain": "finance",
        "expected_facet": "investment_summary",
        "expected_keywords": ["45000", "NVDA", "TSLA", "+1.2%"],
    },
    
    # Travel domain conversation
    {
        "query": "What's my flight number to Chicago?",
        "expected_domain": "travel",
        "expected_facet": "flight_itinerary",
        "expected_keywords": ["UA455", "Chicago", "8:30 AM", "Gate B12"],
    },
    {
        "query": "Which hotel am I staying at in Tokyo?",
        "expected_domain": "travel",
        "expected_facet": "accommodation",
        "expected_keywords": ["Grand Hyatt Tokyo", "GH-998877", "2024-03-10"],
    },
    {
        "query": "What's my train seat for the Rome trip?",
        "expected_domain": "travel",
        "expected_facet": "train_reservation",
        "expected_keywords": ["Rome", "Florence", "seat 4A", "carriage 3"],
    },
    
    # Smart home domain
    {
        "query": "What's the living room temperature set to?",
        "expected_domain": "smart_home",
        "expected_facet": "thermostat_log",
        "expected_keywords": ["72 degrees", "living room", "thermostat", "6:00 PM"],
    },
    {
        "query": "Is there a problem with the robot vacuum?",
        "expected_domain": "smart_home",
        "expected_facet": "device_error",
        "expected_keywords": ["Robot Vacuum", "Stuck", "Master Bedroom", "E4"],
    },
    {
        "query": "Was the garage door left open?",
        "expected_domain": "smart_home",
        "expected_facet": "security_alert",
        "expected_keywords": ["Garage door", "left open", "30 minutes"],
    },
    
    # Work domain
    {
        "query": "When is my meeting with the engineering team?",
        "expected_domain": "work",
        "expected_facet": "calendar_event",
        "expected_keywords": ["engineering team", "Q3 roadmap", "Tuesday"],
    },
    {
        "query": "What's the deadline for Project Apollo?",
        "expected_domain": "work",
        "expected_facet": "project_deadline",
        "expected_keywords": ["Project Apollo", "design review", "next Friday"],
    },
    {
        "query": "What feedback did my boss give me?",
        "expected_domain": "work",
        "expected_facet": "performance_feedback",
        "expected_keywords": ["Feedback", "boss", "user retention", "metrics"],
    },
    
    # Social domain
    {
        "query": "When is Sarah's birthday?",
        "expected_domain": "social",
        "expected_facet": "birthday_reminder",
        "expected_keywords": ["Sarah", "birthday", "November 12th"],
    },
    {
        "query": "What did I learn about John from Marketing?",
        "expected_domain": "social",
        "expected_facet": "person_detail",
        "expected_keywords": ["John", "Marketing", "hiking", "vintage wines"],
    },
    {
        "query": "Who's coming to the college reunion?",
        "expected_domain": "social",
        "expected_facet": "event_planning",
        "expected_keywords": ["College Reunion", "Boston", "Mike", "Jessica", "Sam"],
    },
    
    # Shopping domain
    {
        "query": "What do I need to buy at the store?",
        "expected_domain": "shopping",
        "expected_facet": "shopping_list",
        "expected_keywords": ["olive oil", "laundry detergent"],
    },
    {
        "query": "When will my Amazon order arrive?",
        "expected_domain": "shopping",
        "expected_facet": "order_confirmation",
        "expected_keywords": ["AMZ-112233", "HDMI Cable", "USB-C Hub", "Tomorrow"],
    },
    {
        "query": "Do I need to return those headphones?",
        "expected_domain": "shopping",
        "expected_facet": "errand",
        "expected_keywords": ["Return", "headphones", "Best Buy", "Saturday"],
    },
    
    # Vehicle domain
    {
        "query": "What was that warning light on my car?",
        "expected_domain": "vehicle",
        "expected_facet": "vehicle_alert",
        "expected_keywords": ["check engine light", "highway"],
    },
    {
        "query": "Where did I park at the airport?",
        "expected_domain": "vehicle",
        "expected_facet": "parking_location",
        "expected_keywords": ["level 3", "spot 305", "airport"],
    },
    {
        "query": "When is my next oil change due?",
        "expected_domain": "vehicle",
        "expected_facet": "service_history",
        "expected_keywords": ["Oil Change", "Jiffy Lube", "$89.99", "2024-05-20"],
    },
    
    # Entertainment domain
    {
        "query": "What show did I watch last night?",
        "expected_domain": "entertainment",
        "expected_facet": "watch_history",
        "expected_keywords": ["Succession", "season finale"],
    },
    {
        "query": "What's on my movie watchlist?",
        "expected_domain": "entertainment",
        "expected_facet": "watchlist",
        "expected_keywords": ["Dune", "Part Two", "watchlist"],
    },
    {
        "query": "Remember I don't like jump scares",
        "expected_domain": "entertainment",
        "expected_facet": "user_preference",
        "expected_keywords": ["jump scares", "Don't recommend"],
    },
    
    # Education domain
    {
        "query": "How far am I in the Python course?",
        "expected_domain": "education",
        "expected_facet": "course_progress",
        "expected_keywords": ["Chapter 4", "Introduction to Python", "Coursera"],
    },
    {
        "query": "What page am I on in that Kahneman book?",
        "expected_domain": "education",
        "expected_facet": "reading_tracker",
        "expected_keywords": ["Thinking, Fast and Slow", "Kahneman", "page 120", "499"],
    },
    {
        "query": "What Spanish words did I learn?",
        "expected_domain": "education",
        "expected_facet": "language_learning",
        "expected_keywords": ["Spanish", "Gato", "Perro", "Casa", "Biblioteca"],
    },
    
    # Repeat queries to test cache hits (should hit L1 with same content)
    {
        "query": "Remind me about my weight again",
        "expected_domain": "health",
        "expected_facet": "weight_log",
        "expected_keywords": ["165 lbs", "weighed", "down 2 lbs"],
    },
    {
        "query": "When was my car insurance due again?",
        "expected_domain": "finance",
        "expected_facet": "bill_reminder",
        "expected_keywords": ["insurance renewal", "$600", "15th"],
    },
    {
        "query": "What's my Tokyo hotel called?",
        "expected_domain": "travel",
        "expected_facet": "accommodation",
        "expected_keywords": ["Grand Hyatt Tokyo", "GH-998877"],
    },
]


class BenchmarkRunner:
    """
    Runs A/B benchmark comparing L1/L2 cache vs direct Graphiti.
    
    For each query, runs:
    1. Direct mode: skip_cache=True (Graphiti only)
    2. Cached mode: normal cache flow with L1/L2
    
    Then compares speed and accuracy between modes.
    """

    def __init__(
        self,
        retriever: MemoryRetriever,
        output_dir: Path = Path("benchmark_results"),
    ):
        self.retriever = retriever
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.comparisons: list[ComparisonTrial] = []

    async def run_benchmark(
        self,
        queries: list[dict] = None,
        session_id: str = "benchmark_session",
        delay_between_queries: float = 0.5,
        warmup_rounds: int = 1,
    ) -> BenchmarkSummary:
        """
        Run A/B comparison benchmark.
        
        For each query:
        1. Run in DIRECT mode (skip_cache=True) to get baseline
        2. Run in CACHED mode (normal) to get cache performance
        3. Compare times and accuracy
        
        Args:
            queries: List of query dicts
            session_id: Session ID for L1 cache
            delay_between_queries: Pause between queries
            warmup_rounds: How many times to run queries to warm the cache first
        """
        queries = queries or CONVERSATION_QUERIES
        self.comparisons = []
        
        # Warm up the cache with initial runs
        if warmup_rounds > 0:
            logger.info(f"Warming up cache with {warmup_rounds} round(s)...")
            for round_num in range(warmup_rounds):
                for q in queries[:10]:  # Warm with first 10 queries
                    await self.retriever.retrieve(
                        query=q["query"],
                        session_id=session_id,
                    )
                    await asyncio.sleep(0.1)
            logger.info("Cache warmup complete")
        
        logger.info(f"\nStarting A/B benchmark with {len(queries)} queries")
        logger.info("=" * 70)
        
        for i, q in enumerate(queries):
            logger.info(f"\n[{i+1}/{len(queries)}] Query: {q['query']}")
            
            expected_keywords = q.get("expected_keywords", [])
            
            # === MODE A: Direct Graphiti (baseline) ===
            direct_result = await self.retriever.retrieve(
                query=q["query"],
                session_id=f"{session_id}_direct",  # Separate session to avoid pollution
                skip_cache=True,
            )
            direct_accuracy = self._calculate_accuracy(
                direct_result, q["expected_domain"], q["expected_facet"]
            )
            direct_content_accuracy = self._calculate_content_accuracy(
                direct_result, expected_keywords
            )
            direct_top_content = self._get_top_content(direct_result)
            
            # === MODE B: Cached (L1/L2 + Graphiti fallback) ===
            cached_result = await self.retriever.retrieve(
                query=q["query"],
                session_id=session_id,
                skip_cache=False,
            )
            cached_accuracy = self._calculate_accuracy(
                cached_result, q["expected_domain"], q["expected_facet"]
            )
            cached_content_accuracy = self._calculate_content_accuracy(
                cached_result, expected_keywords
            )
            cached_top_content = self._get_top_content(cached_result)
            
            # Compute speedup (avoid division by zero)
            cached_time = cached_result.total_time_ms
            direct_time = direct_result.total_time_ms
            speedup = direct_time / max(cached_time, 0.1)
            
            comparison = ComparisonTrial(
                trial_id=i + 1,
                query=q["query"],
                expected_domain=q["expected_domain"],
                expected_facet=q["expected_facet"],
                expected_keywords=expected_keywords,
                direct_time_ms=direct_time,
                direct_accuracy=direct_accuracy,
                direct_content_accuracy=direct_content_accuracy,
                direct_result_count=len(direct_result.graphiti_hits),
                direct_top_content=direct_top_content,
                cached_time_ms=cached_time,
                cached_accuracy=cached_accuracy,
                cached_content_accuracy=cached_content_accuracy,
                cached_hit_source=cached_result.hit_source,
                cached_l1_count=len(cached_result.l1_hits),
                cached_l2_count=len(cached_result.l2_hits),
                cached_graphiti_count=len(cached_result.graphiti_hits),
                cached_top_content=cached_top_content,
                speedup=speedup,
                accuracy_delta=cached_accuracy - direct_accuracy,
                content_accuracy_delta=cached_content_accuracy - direct_content_accuracy,
            )
            self.comparisons.append(comparison)
            
            # Log comparison with content accuracy
            logger.info(
                f"  DIRECT: {direct_time:.1f}ms | Acc: {direct_accuracy:.0%} | "
                f"Content: {direct_content_accuracy:.0%}"
            )
            logger.info(
                f"  CACHED: {cached_time:.1f}ms | Acc: {cached_accuracy:.0%} | "
                f"Content: {cached_content_accuracy:.0%} | "
                f"Source: {cached_result.hit_source} | Speedup: {speedup:.1f}x"
            )
            
            await asyncio.sleep(delay_between_queries)
        
        summary = self._compute_summary()
        self._save_results(summary)
        self._generate_plots()
        
        return summary

    def _get_top_content(self, result: RetrievalResult) -> str:
        """Get content from top result for logging."""
        if result.all_results:
            return result.all_results[0].content[:150]
        return ""

    def _calculate_content_accuracy(
        self,
        result: RetrievalResult,
        expected_keywords: list[str],
    ) -> float:
        """
        Calculate content accuracy based on keyword matching.
        
        Checks if expected keywords from the ground truth (graphiti.py episodes)
        are present in the returned results.
        
        Returns: Score between 0.0 and 1.0
        """
        if not result.all_results or not expected_keywords:
            return 0.0
        
        # Combine content from top 3 results
        combined_content = " ".join(
            entry.content.lower() for entry in result.all_results[:3]
        )
        
        # Count keyword matches
        matches = 0
        for keyword in expected_keywords:
            if keyword.lower() in combined_content:
                matches += 1
        
        return matches / len(expected_keywords) if expected_keywords else 0.0

    def _calculate_accuracy(
        self,
        result: RetrievalResult,
        expected_domain: str,
        expected_facet: str,
    ) -> float:
        """Calculate accuracy based on whether expected domain/facet were found."""
        if not result.all_results:
            return 0.0
        
        score = 0.0
        
        # Check query tagging accuracy
        if expected_domain in result.query_tags.get("domains", []):
            score += 0.3
        
        # Check if any result has matching domain
        for entry in result.all_results[:3]:  # Top 3 results
            entry_domains = entry.tags.get("domains", [])
            
            if expected_domain in entry_domains:
                score += 0.35
                break
        
        # Check facet match
        for entry in result.all_results[:3]:
            entry_facets = entry.tags.get("facets", [])
            if expected_facet in entry_facets:
                score += 0.35
                break
        
        return min(1.0, score)

    def _compute_summary(self) -> BenchmarkSummary:
        """Compute A/B comparison summary statistics."""
        n = len(self.comparisons)
        if n == 0:
            return BenchmarkSummary(
                total_trials=0,
                avg_direct_time_ms=0,
                avg_direct_accuracy=0,
                avg_direct_content_accuracy=0,
                avg_cached_time_ms=0,
                avg_cached_accuracy=0,
                avg_cached_content_accuracy=0,
                l1_hit_rate=0,
                l2_hit_rate=0,
                graphiti_fallback_rate=0,
                avg_speedup=0,
                max_speedup=0,
                avg_accuracy_delta=0,
                avg_content_accuracy_delta=0,
                warm_l1_hit_rate=0,
                warm_avg_speedup=0,
                warm_content_accuracy=0,
            )
        
        # Hit source distribution
        l1_hits = sum(1 for c in self.comparisons if c.cached_hit_source == "L1")
        l2_hits = sum(1 for c in self.comparisons if c.cached_hit_source == "L2")
        graphiti_fallbacks = sum(1 for c in self.comparisons if c.cached_hit_source == "Graphiti")
        
        # Warm cache analysis (second half of trials when cache is populated)
        midpoint = n // 2
        warm_trials = self.comparisons[midpoint:]
        warm_l1_hits = sum(1 for c in warm_trials if c.cached_hit_source == "L1")
        warm_speedups = [c.speedup for c in warm_trials]
        warm_content_accuracies = [c.cached_content_accuracy for c in warm_trials]
        
        return BenchmarkSummary(
            total_trials=n,
            avg_direct_time_ms=np.mean([c.direct_time_ms for c in self.comparisons]),
            avg_direct_accuracy=np.mean([c.direct_accuracy for c in self.comparisons]),
            avg_direct_content_accuracy=np.mean([c.direct_content_accuracy for c in self.comparisons]),
            avg_cached_time_ms=np.mean([c.cached_time_ms for c in self.comparisons]),
            avg_cached_accuracy=np.mean([c.cached_accuracy for c in self.comparisons]),
            avg_cached_content_accuracy=np.mean([c.cached_content_accuracy for c in self.comparisons]),
            l1_hit_rate=l1_hits / n,
            l2_hit_rate=l2_hits / n,
            graphiti_fallback_rate=graphiti_fallbacks / n,
            avg_speedup=np.mean([c.speedup for c in self.comparisons]),
            max_speedup=max(c.speedup for c in self.comparisons),
            avg_accuracy_delta=np.mean([c.accuracy_delta for c in self.comparisons]),
            avg_content_accuracy_delta=np.mean([c.content_accuracy_delta for c in self.comparisons]),
            warm_l1_hit_rate=warm_l1_hits / len(warm_trials) if warm_trials else 0,
            warm_avg_speedup=np.mean(warm_speedups) if warm_speedups else 0,
            warm_content_accuracy=np.mean(warm_content_accuracies) if warm_content_accuracies else 0,
        )

    def _save_results(self, summary: BenchmarkSummary) -> None:
        """Save A/B comparison results to JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comparisons
        comparisons_file = self.output_dir / f"ab_comparisons_{timestamp}.json"
        with open(comparisons_file, "w") as f:
            json.dump([asdict(c) for c in self.comparisons], f, indent=2)
        
        # Save summary
        summary_file = self.output_dir / f"ab_summary_{timestamp}.json"
        with open(summary_file, "w") as f:
            json.dump(asdict(summary), f, indent=2)
        
        logger.info(f"Results saved to {self.output_dir}")

    def _generate_plots(self) -> None:
        """Generate A/B comparison visualization plots."""
        if not self.comparisons:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Plot 1: Direct vs Cached response time comparison
        ax1 = axes[0, 0]
        trial_ids = [c.trial_id for c in self.comparisons]
        direct_times = [c.direct_time_ms for c in self.comparisons]
        cached_times = [c.cached_time_ms for c in self.comparisons]
        
        ax1.plot(trial_ids, direct_times, 'r-', label='Direct (Graphiti only)', linewidth=2, marker='o', markersize=4)
        ax1.plot(trial_ids, cached_times, 'g-', label='Cached (L1/L2)', linewidth=2, marker='s', markersize=4)
        ax1.fill_between(trial_ids, cached_times, direct_times, alpha=0.3, color='green', where=[c >= d for c, d in zip(direct_times, cached_times)])
        ax1.set_xlabel('Trial #')
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_title('A/B Comparison: Direct vs Cached Response Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Speedup over trials (shows cache warming effect)
        ax2 = axes[0, 1]
        speedups = [c.speedup for c in self.comparisons]
        colors = ['#2ecc71' if s >= 2 else '#f39c12' if s >= 1 else '#e74c3c' for s in speedups]
        ax2.bar(trial_ids, speedups, color=colors)
        ax2.axhline(y=1.0, color='black', linestyle='--', linewidth=1, label='Break-even (1x)')
        ax2.axhline(y=np.mean(speedups), color='blue', linestyle='-', linewidth=2, label=f'Avg: {np.mean(speedups):.1f}x')
        ax2.set_xlabel('Trial #')
        ax2.set_ylabel('Speedup (x)')
        ax2.set_title('Speedup Factor (Direct Time / Cached Time)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Cache hit source distribution
        ax3 = axes[1, 0]
        sources = ['L1 (Hot)', 'L2 (Warm)', 'Graphiti Fallback']
        counts = [
            sum(1 for c in self.comparisons if c.cached_hit_source == "L1"),
            sum(1 for c in self.comparisons if c.cached_hit_source == "L2"),
            sum(1 for c in self.comparisons if c.cached_hit_source == "Graphiti"),
        ]
        colors = ['#2ecc71', '#f39c12', '#e74c3c']
        bars = ax3.bar(sources, counts, color=colors)
        ax3.set_ylabel('Query Count')
        ax3.set_title('Cache Hit Distribution (Cached Mode)')
        for bar, count in zip(bars, counts):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{count} ({count/len(self.comparisons)*100:.0f}%)', 
                    ha='center', fontweight='bold')
        
        # Plot 4: Accuracy comparison
        ax4 = axes[1, 1]
        direct_accs = [c.direct_accuracy for c in self.comparisons]
        cached_accs = [c.cached_accuracy for c in self.comparisons]
        x = np.arange(len(trial_ids))
        width = 0.35
        ax4.bar(x - width/2, direct_accs, width, label='Direct', color='#e74c3c', alpha=0.7)
        ax4.bar(x + width/2, cached_accs, width, label='Cached', color='#2ecc71', alpha=0.7)
        ax4.set_xlabel('Trial #')
        ax4.set_ylabel('Accuracy')
        ax4.set_title('Accuracy Comparison: Direct vs Cached')
        ax4.legend()
        ax4.set_ylim(0, 1.1)
        ax4.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / f"ab_benchmark_{timestamp}.png", dpi=150)
        plt.close()
        
        logger.info(f"Plots saved to {self.output_dir}")


async def run_full_benchmark():
    """Main entry point for running the A/B benchmark."""
    
    # Configuration
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"
    GEMINI_API_KEY = "Your api key."
    REDIS_URL = "redis://localhost:6379/0"
    
    logger.info("=" * 70)
    logger.info("MEMORY CACHE A/B BENCHMARK (OPTIMIZED)")
    logger.info("Comparing L1/L2 cache performance vs direct Graphiti queries")
    logger.info("Now with Gemini tag caching for faster queries!")
    logger.info("=" * 70)
    
    logger.info("\nInitializing memory retrieval system...")
    
    retriever = await create_retriever(
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD,
        gemini_api_key=GEMINI_API_KEY,
        redis_url=REDIS_URL,
    )
    
    # Only clear L1 session cache, keep L2 preloaded data
    # await retriever.cache.clear_all()  # Don't clear L2!
    await retriever.cache.l1_clear_session("voice_session_001")
    await retriever.cache.l1_clear_session("voice_session_001_direct")
    logger.info("L1 session cache cleared (L2 data preserved)")
    
    # Reset tagger stats for clean measurement
    retriever.tagger.cache_hits = 0
    retriever.tagger.cache_misses = 0
    
    runner = BenchmarkRunner(
        retriever=retriever,
        output_dir=Path("benchmark_results"),
    )
    
    summary = await runner.run_benchmark(
        queries=CONVERSATION_QUERIES,
        session_id="voice_session_001",
        delay_between_queries=0.3,
        warmup_rounds=1,
    )
    
    # Get tagger stats
    tag_hits = retriever.tagger.cache_hits
    tag_misses = retriever.tagger.cache_misses
    tag_total = tag_hits + tag_misses
    tag_hit_rate = tag_hits / tag_total if tag_total > 0 else 0
    
    # Print A/B comparison summary
    print("\n" + "=" * 70)
    print("A/B BENCHMARK SUMMARY: CACHE vs DIRECT GRAPHITI")
    print("=" * 70)
    print(f"Total Trials:              {summary.total_trials}")
    print("-" * 70)
    print("DIRECT MODE (Graphiti Only - Baseline):")
    print(f"  Avg Response Time:       {summary.avg_direct_time_ms:.1f} ms")
    print(f"  Avg Accuracy (Tags):     {summary.avg_direct_accuracy:.1%}")
    print(f"  Avg Content Accuracy:    {summary.avg_direct_content_accuracy:.1%}")
    print("-" * 70)
    print("CACHED MODE (L1/L2 + Graphiti Fallback):")
    print(f"  Avg Response Time:       {summary.avg_cached_time_ms:.1f} ms")
    print(f"  Avg Accuracy (Tags):     {summary.avg_cached_accuracy:.1%}")
    print(f"  Avg Content Accuracy:    {summary.avg_cached_content_accuracy:.1%}")
    print("-" * 70)
    print("CACHE EFFICIENCY:")
    print(f"  L1 Hit Rate:             {summary.l1_hit_rate:.1%}")
    print(f"  L2 Hit Rate:             {summary.l2_hit_rate:.1%}")
    print(f"  Graphiti Fallback Rate:  {summary.graphiti_fallback_rate:.1%}")
    print("-" * 70)
    print("GEMINI TAG CACHE (NEW OPTIMIZATION):")
    print(f"  Tag Cache Hits:          {tag_hits}")
    print(f"  Tag Cache Misses:        {tag_misses}")
    print(f"  Tag Cache Hit Rate:      {tag_hit_rate:.1%}")
    print(f"  Gemini API Calls Saved:  {tag_hits} (~{tag_hits * 1.5:.0f}s saved)")
    print("-" * 70)
    print("PERFORMANCE COMPARISON:")
    print(f"  Average Speedup:         {summary.avg_speedup:.1f}x")
    print(f"  Maximum Speedup:         {summary.max_speedup:.1f}x")
    print(f"  Tag Accuracy Delta:      {summary.avg_accuracy_delta:+.1%}")
    print(f"  Content Accuracy Delta:  {summary.avg_content_accuracy_delta:+.1%}")
    print("-" * 70)
    print("WARM CACHE ANALYSIS (2nd half of trials):")
    print(f"  Warm L1 Hit Rate:        {summary.warm_l1_hit_rate:.1%}")
    print(f"  Warm Avg Speedup:        {summary.warm_avg_speedup:.1f}x")
    print(f"  Warm Content Accuracy:   {summary.warm_content_accuracy:.1%}")
    print("=" * 70)
    
    # Final verdict
    if summary.avg_speedup >= 2.0 and summary.avg_cached_content_accuracy >= 0.6:
        print("\n✅ CACHE PROVIDES SIGNIFICANT SPEEDUP WITH GOOD ACCURACY!")
    elif summary.avg_speedup >= 1.5:
        print("\n✅ Cache provides good speedup.")
        if summary.avg_cached_content_accuracy < 0.5:
            print("   ⚠️  Content accuracy needs improvement.")
    elif summary.avg_speedup >= 1.0:
        print("\n⚠️  Cache provides marginal speedup. Consider tuning.")
    else:
        print("\n❌ Cache is SLOWER than direct. Review implementation.")
        if tag_hit_rate < 0.5:
            print("   💡 Tip: Tag cache hit rate is low. Run warmup first to populate tag cache.")
    
    if summary.warm_content_accuracy >= 0.7:
        print("✅ Warm cache achieves GOOD content accuracy!")
    elif summary.warm_content_accuracy >= 0.5:
        print("⚠️  Warm cache content accuracy is fair.")
    else:
        print("❌ Warm cache content accuracy is low - check tagging/promotion logic.")
    
    # Cleanup
    await retriever.cache.close()
    await retriever.graphiti.close()
    
    return summary


if __name__ == "__main__":
    asyncio.run(run_full_benchmark())
