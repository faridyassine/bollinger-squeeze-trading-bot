#!/usr/bin/env python3
"""Backtest runner script."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path.parent))

from backend.strategies import BollingerSqueezeStrategy
from backend.backtesting import BacktestEngine, generate_html_report
from backend.data import YahooFinanceProvider
from backend.core.config import config
from backend.core.logging_config import setup_logging
import argparse


def main():
    """Run backtest."""
    parser = argparse.ArgumentParser(description='Run strategy backtest')
    parser.add_argument('symbol', help='Stock symbol to backtest')
    parser.add_argument('--start', default='2020-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default=datetime.now().strftime('%Y-%m-%d'), help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--report', action='store_true', help='Generate HTML report')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level='INFO')
    
    print(f"\n🧪 Running backtest for {args.symbol}")
    print(f"Period: {args.start} to {args.end}")
    print(f"Initial Capital: ${args.capital:,.2f}\n")
    
    # Download data
    print("📥 Downloading data...")
    data_provider = YahooFinanceProvider()
    data = data_provider.get_historical_data(
        args.symbol,
        start_date=datetime.strptime(args.start, '%Y-%m-%d'),
        end_date=datetime.strptime(args.end, '%Y-%m-%d')
    )
    
    if data.empty:
        print(f"❌ No data found for {args.symbol}")
        return
    
    print(f"✅ Downloaded {len(data)} bars\n")
    
    # Initialize strategy
    print("🎯 Initializing strategy...")
    strategy_params = config.strategy.get('bollinger_squeeze', {})
    strategy = BollingerSqueezeStrategy(params=strategy_params)
    
    # Run backtest
    print("🔄 Running backtest...\n")
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=args.capital,
        commission=config.backtesting.get('commission', 0.001),
        slippage=config.backtesting.get('slippage', 0.0005)
    )
    
    results = engine.run(args.symbol, data)
    
    # Display results
    print("=" * 80)
    print(f"BACKTEST RESULTS: {args.symbol}")
    print("=" * 80)
    print(f"Initial Capital:       ${results['initial_capital']:>12,.2f}")
    print(f"Final Equity:          ${results['final_equity']:>12,.2f}")
    print(f"Total Return:          {results['total_return']:>12.2f}%")
    print(f"Buy & Hold Return:     {results['buy_hold_return']:>12.2f}%")
    print("-" * 80)
    print(f"Total Trades:          {results['total_trades']:>12}")
    print(f"Wins:                  {results['wins']:>12}")
    print(f"Losses:                {results['losses']:>12}")
    print(f"Win Rate:              {results['win_rate']:>12.1f}%")
    print("-" * 80)
    print(f"Profit Factor:         {results['profit_factor']:>12.2f}")
    print(f"Sharpe Ratio:          {results['sharpe_ratio']:>12.2f}")
    print(f"Max Drawdown:          {results['max_drawdown']:>12.2f}%")
    print(f"Avg Win:               {results['avg_win']:>12.2f}%")
    print(f"Avg Loss:              {results['avg_loss']:>12.2f}%")
    print("=" * 80)
    
    # Generate report if requested
    if args.report:
        print("\n📊 Generating HTML report...")
        report_path = generate_html_report(results)
        print(f"✅ Report saved: {report_path}")


if __name__ == '__main__':
    main()
