# 🔑 Alpaca Setup Guide

## Overview

Alpaca provides more reliable market data than Yahoo Finance with significant advantages:

| Feature | Yahoo Finance | Alpaca |
|---------|--------------|--------|
| Rate Limits | ~2,000 requests/hour | 200 requests/minute (12,000/hour) |
| Data Quality | Delayed 15-20 minutes | Real-time |
| Reliability | Frequent errors and blocks | Professional-grade uptime |
| Authentication | None required | API keys required |
| Cost | Free | Free for paper trading |

## Step 1: Create Alpaca Account

1. **Go to** [https://alpaca.markets/](https://alpaca.markets/)
2. **Click** "Sign Up" button in the top right
3. **Choose** "Paper Trading" (free simulation account - no real money)
4. **Complete** registration with your email and basic information
5. **Verify** your email address

**Note**: Paper trading is completely free and provides the same data quality as live trading.

## Step 2: Generate API Keys

1. **Login** to [https://app.alpaca.markets/](https://app.alpaca.markets/)
2. **Navigate** to Paper Trading dashboard
3. **Go to** API Keys section:
   - Direct link: [https://app.alpaca.markets/paper/dashboard/api-keys](https://app.alpaca.markets/paper/dashboard/api-keys)
4. **Click** "Generate New Key"
5. **Name your key**: "Bollinger Bot" (or any name you prefer)
6. **Set permissions**: 
   - ✅ Account (Read-only)
   - ✅ Market Data (Read-only)
   - ❌ Trading (Not needed for data only)
7. **Click** "Generate"
8. **⚠️ IMPORTANT**: Copy both keys immediately
   - `API Key ID` (starts with "PK...")
   - `Secret Key` (long alphanumeric string)
   - ⚠️ **The Secret Key will only be shown once!**

## Step 3: Configure Bot

### 3.1 Add Keys to Environment File

Edit your `.env` file (create it from `.env.example` if it doesn't exist):

```bash
# Copy the example file if needed
cp .env.example .env

# Edit the file
nano .env
```

Add your Alpaca credentials:

```env
# Alpaca API
ALPACA_API_KEY=PKxxxxxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALPACA_PAPER=true
```

**Notes**:
- Replace `PKxxxxxxxxxx` with your actual API Key ID
- Replace the secret with your actual Secret Key
- Keep `ALPACA_PAPER=true` for paper trading
- Set `ALPACA_PAPER=false` only if you have a funded live trading account

### 3.2 Update Configuration File

Edit `config.yaml`:

```yaml
# Market Data
data:
  provider: "alpaca"  # Changed from "yahoo"
  timeframe: "1d"
  update_interval: 60
  cache_enabled: true
  cache_duration: 60
```

### 3.3 Restart Bot

If using Docker:
```bash
docker-compose restart backend
```

If running manually:
```bash
# Stop the current process (Ctrl+C)
# Then restart
python -m backend.main
```

## Step 4: Verify Setup

### 4.1 Check Logs

View the logs to confirm Alpaca is working:

```bash
# Docker
docker-compose logs backend | grep -i alpaca

# Manual
tail -f logs/trading.log | grep -i alpaca
```

You should see:
```
Alpaca provider initialized (Paper: True)
```

### 4.2 Run Test Script

Use the provided test script to validate your setup:

```bash
python scripts/test_alpaca.py
```

Expected output:
```
🔍 Testing Alpaca Integration
==================================================
✅ API Key found: PKxxxxxxxx...
✅ Secret Key found: xxxxxxxxxx...

📡 Initializing Alpaca provider...
✅ Provider initialized

🔍 Test 1: Checking market status...
Market is 🟢 OPEN

🔍 Test 2: Fetching AAPL historical data (5 days)...
✅ Success! Retrieved 5 bars

🔍 Test 3: Getting latest AAPL price...
✅ Latest price: $175.43

==================================================
✅ All tests completed successfully!
```

### 4.3 Test API Endpoint

If the bot is running, test via API:

```bash
curl http://localhost:8000/api/symbols/AAPL
```

## Troubleshooting

### Error: "Alpaca API credentials not found"

**Problem**: Environment variables are not loaded.

**Solution**:
1. Ensure `.env` file exists in the project root
2. Check that variable names are spelled correctly
3. Restart the application after editing `.env`
4. For Docker, rebuild: `docker-compose up -d --build`

### Error: "Forbidden" or "Unauthorized"

**Problem**: Invalid API keys.

**Solution**:
1. Verify keys are copied correctly (no extra spaces)
2. Ensure you're using Paper Trading keys for paper account
3. Check that keys haven't been revoked in Alpaca dashboard
4. Generate new keys if needed

### Error: "No data returned for symbol"

**Problem**: Symbol might not exist or market is closed.

**Solutions**:
1. Verify symbol is correct (use uppercase, e.g., "AAPL" not "aapl")
2. Check if it's a valid US stock
3. Try during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
4. Alpaca only provides data for US equities

### Data Quality Issues

**Problem**: Missing or incomplete data.

**Solutions**:
1. Alpaca provides data from IEX (Investors Exchange)
2. Some thinly traded stocks may have gaps
3. Pre-market and after-hours data require special subscription
4. Use Yahoo Finance as fallback if needed

## Rate Limits

### Paper Trading
- **Market Data**: 200 requests per minute
- **Account Info**: 200 requests per minute
- **No monthly limits**

### Live Trading
- Same limits as paper trading
- Market data is free for Alpaca trading customers

### Best Practices
1. Use caching to reduce API calls (enabled by default)
2. Batch requests when possible
3. Don't poll faster than necessary (60-120 second intervals recommended)
4. The bot handles rate limiting automatically

## Advanced Configuration

### Switch Back to Yahoo Finance

To temporarily use Yahoo Finance (no API keys needed):

```yaml
# config.yaml
data:
  provider: "yahoo"
```

### Use Both Providers (Fallback)

You can implement fallback logic in your code:

```python
from backend.data.market_data import get_data_provider

try:
    provider = get_data_provider("alpaca")
except:
    provider = get_data_provider("yahoo")
```

### Custom Timeframes

Alpaca supports various timeframes:

| Timeframe | Config Value | Use Case |
|-----------|--------------|----------|
| 1 Minute | `1m` | Scalping, day trading |
| 5 Minutes | `5m` | Intraday analysis |
| 15 Minutes | `15m` | Short-term trading |
| 1 Hour | `1h` | Swing trading |
| 1 Day | `1d` | Position trading (default) |
| 1 Week | `1wk` | Long-term analysis |

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use read-only API keys** (never enable trading permissions for this bot)
3. **Rotate keys periodically** (every 90 days recommended)
4. **Use paper trading** for testing and development
5. **Keep keys secure** - treat them like passwords

## API Key Management

### Regenerating Keys

If you need to regenerate your API keys:

1. Go to [Alpaca API Keys](https://app.alpaca.markets/paper/dashboard/api-keys)
2. Click "Revoke" on the old key
3. Click "Generate New Key"
4. Update your `.env` file with new keys
5. Restart the bot

### Multiple Environments

For running multiple instances (dev, staging, prod):

1. Create separate API keys for each environment
2. Use different `.env` files:
   - `.env.dev`
   - `.env.staging`
   - `.env.prod`
3. Load appropriate environment file

## Additional Resources

- **Alpaca Documentation**: [https://alpaca.markets/docs/](https://alpaca.markets/docs/)
- **API Reference**: [https://alpaca.markets/docs/api-references/market-data-api/](https://alpaca.markets/docs/api-references/market-data-api/)
- **Status Page**: [https://status.alpaca.markets/](https://status.alpaca.markets/)
- **Support**: [https://alpaca.markets/support](https://alpaca.markets/support)

## Getting Help

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Review bot logs for error messages
3. Test with `scripts/test_alpaca.py`
4. Check Alpaca's status page for outages
5. Open an issue on GitHub with:
   - Error message (remove sensitive info)
   - Steps to reproduce
   - Your environment (Docker/manual, OS, Python version)

---

**Next Steps**: After successful setup, configure your [watchlist](configuration.md) and start [scanning the market](../README.md#-usage)!
