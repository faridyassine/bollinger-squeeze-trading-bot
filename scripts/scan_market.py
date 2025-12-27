#!/usr/bin/env python3
"""Standalone market scanner script."""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path.parent))

from backend.scanner import MarketScanner
from backend.core.config import config
from backend.core.logging_config import setup_logging
import argparse


def main():
    """Run market scanner."""
    parser = argparse.ArgumentParser(description='Scan market for Bollinger Squeezes')
    parser.add_argument('--symbols', nargs='+', help='Symbols to scan (default: from config)')
    parser.add_argument('--top', type=int, default=10, help='Number of top results to show')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level='INFO')
    
    # Initialize scanner
    scanner = MarketScanner(symbols=args.symbols)
    
    print("🔍 Scanning market for Bollinger Squeezes...\n")
    
    # Run scan
    results = scanner.scan_market()
    
    if not results:
        print("No squeezes found.")
        return
    
    print(f"✅ Found {len(results)} squeezes\n")
    print("=" * 80)
    print(f"{'Symbol':<10} {'Price':<10} {'Strength':<10} {'Days':<8} {'Direction':<12} {'Confidence':<12}")
    print("=" * 80)
    
    for result in results[:args.top]:
        print(f"{result['symbol']:<10} ${result['price']:<9.2f} {result['squeeze_strength']:<10.0f} "
              f"{result['days_in_squeeze']:<8} {result['direction']:<12} {result['confidence']:<12.0f}%")
    
    print("=" * 80)
    print(f"\nShowing top {min(args.top, len(results))} of {len(results)} results")


if __name__ == '__main__':
    main()
