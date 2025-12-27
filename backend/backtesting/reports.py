"""HTML report generation for backtesting results."""
from typing import Dict
import pandas as pd
from pathlib import Path
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


def generate_html_report(results: Dict, output_path: str = None) -> str:
    """Generate HTML backtest report.
    
    Args:
        results: Backtest results dictionary
        output_path: Path to save report (optional)
        
    Returns:
        HTML string
    """
    symbol = results['symbol']
    
    if output_path is None:
        output_path = f"reports/backtest_{symbol}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    # Create reports directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Backtest Report - {symbol}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #555;
                margin-top: 30px;
                border-bottom: 2px solid #ddd;
                padding-bottom: 5px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .metric-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .metric-card.positive {{
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            }}
            .metric-card.negative {{
                background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            }}
            .metric-label {{
                font-size: 14px;
                opacity: 0.9;
                margin-bottom: 5px;
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: bold;
            }}
            .metric-subtitle {{
                font-size: 12px;
                opacity: 0.8;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .profit {{
                color: #4CAF50;
                font-weight: bold;
            }}
            .loss {{
                color: #f44336;
                font-weight: bold;
            }}
            .summary {{
                background-color: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .chart-placeholder {{
                background-color: #f0f0f0;
                padding: 40px;
                text-align: center;
                border-radius: 8px;
                margin: 20px 0;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Backtest Report: {symbol}</h1>
            
            <div class="summary">
                <strong>Period:</strong> {results['start_date'].strftime('%Y-%m-%d') if hasattr(results['start_date'], 'strftime') else results['start_date']} 
                to {results['end_date'].strftime('%Y-%m-%d') if hasattr(results['end_date'], 'strftime') else results['end_date']}<br>
                <strong>Initial Capital:</strong> ${results['initial_capital']:,.2f}<br>
                <strong>Final Equity:</strong> ${results['final_equity']:,.2f}
            </div>
            
            <h2>Performance Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-card {"positive" if results['total_return'] > 0 else "negative"}">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value">{results['total_return']:.2f}%</div>
                    <div class="metric-subtitle">vs Buy & Hold: {results['buy_hold_return']:.2f}%</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{results['total_trades']}</div>
                    <div class="metric-subtitle">Wins: {results['wins']} | Losses: {results['losses']}</div>
                </div>
                
                <div class="metric-card {"positive" if results['win_rate'] >= 70 else ""}">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{results['win_rate']:.1f}%</div>
                    <div class="metric-subtitle">Target: 70%+</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Profit Factor</div>
                    <div class="metric-value">{results['profit_factor']:.2f}</div>
                    <div class="metric-subtitle">Gross Profit / Gross Loss</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{results['sharpe_ratio']:.2f}</div>
                    <div class="metric-subtitle">Risk-adjusted return</div>
                </div>
                
                <div class="metric-card {"positive" if results['max_drawdown'] < 15 else "negative"}">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value">{results['max_drawdown']:.2f}%</div>
                    <div class="metric-subtitle">Peak to trough decline</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Avg Win</div>
                    <div class="metric-value">{results['avg_win']:.2f}%</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Avg Loss</div>
                    <div class="metric-value">{results['avg_loss']:.2f}%</div>
                </div>
            </div>
            
            <h2>Equity Curve</h2>
            <div class="chart-placeholder">
                📈 Equity Curve Chart<br>
                <small>Equity progression over time</small>
            </div>
            
            <h2>Trade History</h2>
            <table>
                <thead>
                    <tr>
                        <th>Entry Date</th>
                        <th>Exit Date</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>Shares</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                        <th>Exit Reason</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add trades
    for trade in results['trades'][-50:]:  # Last 50 trades
        pnl_class = "profit" if trade['pnl'] > 0 else "loss"
        html += f"""
                    <tr>
                        <td>{trade['entry_date'].strftime('%Y-%m-%d') if hasattr(trade['entry_date'], 'strftime') else trade['entry_date']}</td>
                        <td>{trade['exit_date'].strftime('%Y-%m-%d') if hasattr(trade['exit_date'], 'strftime') else trade['exit_date']}</td>
                        <td>${trade['entry_price']:.2f}</td>
                        <td>${trade['exit_price']:.2f}</td>
                        <td>{trade['shares']}</td>
                        <td class="{pnl_class}">${trade['pnl']:.2f}</td>
                        <td class="{pnl_class}">{trade['pnl_percent']:.2f}%</td>
                        <td>{trade['exit_reason']}</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                <p>Generated by Bollinger Squeeze Trading Bot</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save to file
    try:
        with open(output_path, 'w') as f:
            f.write(html)
        logger.info(f"Report saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {e}")
    
    return html
