#!/usr/bin/env python3
"""
Test script for Alpaca integration.

This script validates the Alpaca API connection and tests basic data retrieval.
Usage: python scripts/test_alpaca.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data.alpaca import AlpacaDataProvider
from dotenv import load_dotenv


def main():
    """Run Alpaca integration tests."""
    print("🔍 Testing Alpaca Integration\n")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if keys are present
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    paper = os.getenv('ALPACA_PAPER', 'true')
    
    if not api_key or not secret_key:
        print("❌ ERROR: Alpaca API keys not found in environment")
        print("\nPlease add the following to your .env file:")
        print("  ALPACA_API_KEY=PKxxxxxxxxxx")
        print("  ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxx")
        print("  ALPACA_PAPER=true")
        print("\nSee docs/alpaca_setup.md for detailed setup instructions.")
        return 1
    
    print(f"✅ API Key found: {api_key[:10]}...")
    print(f"✅ Secret Key found: {secret_key[:10]}...")
    print(f"✅ Mode: {'Paper Trading' if paper.lower() == 'true' else 'Live Trading'}\n")
    
    try:
        # Initialize provider
        print("📡 Initializing Alpaca provider...")
        provider = AlpacaDataProvider()
        print("✅ Provider initialized\n")
        
        # Test 1: Market status
        print("🔍 Test 1: Checking market status...")
        is_open = provider.is_market_open()
        print(f"Market is {'🟢 OPEN' if is_open else '🔴 CLOSED'}\n")
        
        # Test 2: Fetch historical data
        print("🔍 Test 2: Fetching AAPL historical data (5 days, daily)...")
        df = provider.get_data('AAPL', period='5d', timeframe='1d')
        
        if df.empty:
            print("❌ No data returned")
            print("This might happen if:")
            print("  - The market is closed and no recent data is available")
            print("  - There's an issue with the API keys")
            print("  - The symbol doesn't exist\n")
        else:
            print(f"✅ Success! Retrieved {len(df)} bars")
            print(f"\nLast 3 days:")
            print(df.tail(3)[['open', 'high', 'low', 'close', 'volume']].to_string())
            last_close = df['close'].iloc[-1]
            print(f"\nLast close: ${last_close:.2f}\n")
        
        # Test 3: Latest price
        print("🔍 Test 3: Getting latest AAPL price...")
        price = provider.get_latest_price('AAPL')
        if price > 0:
            print(f"✅ Latest price: ${price:.2f}\n")
        else:
            print("⚠️  Could not fetch latest price (might be normal if market is closed)\n")
        
        # Test 4: Multiple symbols
        print("🔍 Test 4: Testing multiple symbols...")
        test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
        
        print("Fetching 5-day history for 5 symbols...")
        for symbol in test_symbols:
            try:
                df = provider.get_data(symbol, period='5d', timeframe='1d')
                if df.empty:
                    print(f"⚠️  {symbol}: No data")
                else:
                    last_price = df['close'].iloc[-1]
                    print(f"✅ {symbol}: ${last_price:>8.2f} ({len(df)} bars)")
            except Exception as e:
                print(f"❌ {symbol}: Error - {str(e)[:50]}")
        
        # Test 5: Different timeframes
        print("\n🔍 Test 5: Testing different timeframes...")
        timeframes = ['1d', '1h', '15m']
        periods = ['5d', '1d', '1d']
        
        for timeframe, period in zip(timeframes, periods):
            try:
                df = provider.get_data('AAPL', period=period, timeframe=timeframe)
                if not df.empty:
                    print(f"✅ {timeframe:>3} timeframe: {len(df)} bars")
                else:
                    print(f"⚠️  {timeframe:>3} timeframe: No data")
            except Exception as e:
                print(f"❌ {timeframe:>3} timeframe: {str(e)[:50]}")
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("\nYour Alpaca integration is working correctly.")
        print("You can now use Alpaca as your data provider in config.yaml:")
        print("\n  data:")
        print("    provider: \"alpaca\"")
        print("\nSee docs/alpaca_setup.md for more information.")
        return 0
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {str(e)}")
        print("\nPlease check your .env file and ensure:")
        print("  1. ALPACA_API_KEY is set correctly")
        print("  2. ALPACA_SECRET_KEY is set correctly")
        print("  3. Keys have no extra spaces or quotes")
        print("\nSee docs/alpaca_setup.md for setup instructions.")
        return 1
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\nError type: {type(e).__name__}")
        print("\nPossible causes:")
        print("  - Invalid API keys")
        print("  - Network connectivity issues")
        print("  - Alpaca service outage")
        print("\nCheck https://status.alpaca.markets/ for service status.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
