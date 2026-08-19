# Stock Analysis & Recommendations - Implementation Plan

## Overview
Enhance the stock watchlist app with technical analysis and buy/sell/hold recommendations using Massive.com API historical data.

## Architecture

### Data Flow
```
User adds stock to watchlist
  ↓
User clicks "Analyze" button
  ↓
Backend fetches 50 days of historical OHLCV data from Massive API
  ↓
Calculate technical indicators:
  - SMA(20): 20-day Simple Moving Average
  - SMA(50): 50-day Simple Moving Average  
  - RSI(14): 14-day Relative Strength Index
  ↓
Apply recommendation rules (scoring system)
  ↓
Store results in stock_analysis table (Lakebase)
  ↓
Return JSON to frontend with recommendation + confidence + reasons
  ↓
Display badge (BUY/SELL/HOLD) + confidence % + expandable reasons
```

## Database Schema

### New Table: `stock_analysis`
```sql
CREATE TABLE stock_analysis (
    symbol TEXT,
    email TEXT,
    current_price NUMERIC,
    price_change_1d NUMERIC,
    price_change_7d NUMERIC,
    sma_20 NUMERIC,
    sma_50 NUMERIC,
    rsi_14 NUMERIC,
    volume_avg NUMERIC,
    market_cap NUMERIC,
    sector TEXT,
    recommendation TEXT,  -- 'BUY', 'SELL', 'HOLD'
    confidence NUMERIC,   -- 0.0 to 1.0
    reasons JSONB,        -- Array of reasons
    analyzed_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (symbol, email)
);
```

## Technical Indicators

### 1. Simple Moving Average (SMA)
**Formula:** Average of closing prices over N days

**Implementation:**
```python
def calculate_sma(prices: list[float], period: int) -> float:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period
```

**Usage:**
- SMA(20): Short-term trend
- SMA(50): Medium-term trend
- Price > SMA(20) > SMA(50) = Strong uptrend

### 2. Relative Strength Index (RSI)
**Formula:** Measures momentum on 0-100 scale

**Implementation:**
```python
def calculate_rsi(prices: list[float], period: int = 14) -> float:
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

**Interpretation:**
- RSI < 30: Oversold (potential BUY)
- RSI > 70: Overbought (potential SELL)
- RSI 30-70: Neutral

## Recommendation Logic

### Scoring System
```python
score = 0
reasons = []

# Trend signals (3 points max)
if price > sma_20:
    score += 1
    reasons.append("Price above 20-day MA (bullish)")
if price > sma_50:
    score += 1
    reasons.append("Price above 50-day MA (bullish)")
if sma_20 > sma_50:
    score += 1
    reasons.append("Golden cross pattern detected")

# Momentum signals (±2 points)
if rsi < 30:
    score += 2
    reasons.append(f"Oversold (RSI: {rsi:.1f})")
elif rsi > 70:
    score -= 2
    reasons.append(f"Overbought (RSI: {rsi:.1f})")

# Volume confirmation (1 point)
if current_volume > volume_avg * 1.2:
    score += 1
    reasons.append("Above-average volume")

# Generate recommendation
if score >= 3:
    recommendation = "BUY"
    confidence = min(score / 6, 1.0)
elif score <= -1:
    recommendation = "SELL"
    confidence = min(abs(score) / 6, 1.0)
else:
    recommendation = "HOLD"
    confidence = 0.5
```

### Decision Matrix
| Score | Recommendation | Confidence |
|-------|---------------|------------|
| ≥ 5   | BUY          | 80-100%    |
| 3-4   | BUY          | 50-80%     |
| 0-2   | HOLD         | 30-70%     |
| -1 to -2 | SELL      | 50-70%     |
| ≤ -3  | SELL         | 70-100%    |

## API Integration

### Massive.com API Endpoints

**1. Historical Aggregates (OHLCV)**
```
GET /v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}
Response: {
  "results": [
    {"o": 150.0, "h": 152.5, "l": 149.0, "c": 151.2, "v": 1000000}
  ]
}
```

**2. Ticker Details**
```
GET /v3/reference/tickers/{symbol}
Response: {
  "results": {
    "market_cap": 2500000000,
    "sector": "Technology",
    "description": "..."
  }
}
```

## Backend Implementation

### File Structure
```
databricks-lakebase-app-day-1/
├── app.py                 # Main Flask app (add analysis routes)
├── massive_client.py      # Massive API client (add new methods)
├── analysis.py            # NEW: Analysis engine
├── lakebase.py           # Database utilities (add table creation)
├── templates/
│   └── index.html        # UI (add analysis features)
└── requirements.txt      # Dependencies (already complete)
```

### New Routes in app.py

**Analyze Single Stock:**
```python
@app.route("/watchlist/<symbol>/analyze", methods=["POST"])
def analyze_stock(symbol):
    # 1. Fetch 50 days of historical data from Massive
    # 2. Calculate indicators (SMA, RSI)
    # 3. Generate recommendation
    # 4. Store in stock_analysis table
    # 5. Return JSON
```

**Get Analysis Results:**
```python
@app.route("/watchlist/analysis", methods=["GET"])
def get_all_analysis():
    # Return analysis for all user's watchlist stocks
```

**Analyze All Stocks:**
```python
@app.route("/watchlist/analyze-all", methods=["POST"])
def analyze_all_stocks():
    # Batch analysis for entire watchlist
```

## Frontend Implementation

### UI Updates

**1. Add Columns to Table:**
- Recommendation badge (color-coded)
- Confidence indicator (progress bar or %)
- Analyze button per row

**2. Add Buttons:**
- "Analyze" button for each stock
- "Analyze All" button above table

**3. CSS Styling:**
```css
.badge-buy {
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
}

.badge-sell {
  background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
}

.badge-hold {
  background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
}

.confidence-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
}
```

**4. JavaScript Functions:**
```javascript
async function analyzeStock(symbol) {
  const resultEl = document.getElementById('result');
  resultEl.textContent = `Analyzing ${symbol}...`;
  
  try {
    const resp = await fetch(`/watchlist/${symbol}/analyze`, {
      method: 'POST'
    });
    const data = await resp.json();
    
    if (!resp.ok) {
      resultEl.textContent = 'Error: ' + (data.error || resp.statusText);
      return;
    }
    
    resultEl.textContent = `✓ Analysis complete for ${symbol}`;
    loadWatchlist();
  } catch (err) {
    resultEl.textContent = 'Request failed: ' + err;
  }
}
```

## Error Handling

### Edge Cases
1. **Insufficient data:** < 50 days of history
   - Display "Not enough data" message
   - Require minimum 20 days for analysis

2. **API rate limits:**
   - Add exponential backoff
   - Cache results (refresh once daily)

3. **Delisted stocks:**
   - Catch 404 errors from Massive API
   - Mark as "No data available"

4. **Database errors:**
   - Transaction rollback on failure
   - Log errors for debugging

## Performance Considerations

### Caching Strategy
- Store analysis results in database
- Refresh only if > 24 hours old
- Add `last_updated` timestamp check

### Rate Limiting
- Throttle bulk analysis (1 request per second)
- Show progress indicator for "Analyze All"

### Optimization
- Fetch only required fields from Massive API
- Use database indexes on (symbol, email)
- Paginate large watchlists

## Testing Plan

### Unit Tests
1. Test `calculate_sma()` with known values
2. Test `calculate_rsi()` with known values
3. Test `generate_recommendation()` logic

### Integration Tests
1. Add stock → Analyze → Verify database record
2. Test with various stock symbols (AAPL, TSLA, etc.)
3. Test error cases (invalid symbol, API failure)

### Manual Testing
1. Add 3-5 stocks to watchlist
2. Click "Analyze" on each
3. Verify recommendations make sense
4. Check confidence scores are reasonable
5. Expand reasons and verify logic

## Deployment Checklist

- [ ] Create `analysis.py` module
- [ ] Update `massive_client.py` with new methods
- [ ] Add `stock_analysis` table creation
- [ ] Implement analysis endpoints in `app.py`
- [ ] Update frontend with analysis UI
- [ ] Test locally (if possible) or via deployment
- [ ] Commit all changes to GitHub
- [ ] Deploy to Databricks Apps
- [ ] Verify app starts successfully
- [ ] Test end-to-end analysis flow
- [ ] Monitor logs for errors

## Future Enhancements

### Phase 2 Features
1. **Historical charts:** Line chart showing price vs moving averages
2. **Email alerts:** Notify on strong buy/sell signals
3. **Scheduled analysis:** Auto-analyze all stocks daily
4. **More indicators:** MACD, Bollinger Bands, volume trends
5. **Backtesting:** Show historical accuracy of recommendations
6. **News integration:** Factor in sentiment from recent news

### Phase 3 Features
1. **Portfolio tracking:** Track total value and gains/losses
2. **Trade simulation:** Paper trading to test strategies
3. **Risk metrics:** Volatility, beta, Sharpe ratio
4. **Comparison tools:** Compare multiple stocks side-by-side
5. **Mobile responsive:** Optimize for phone/tablet

## References

- Massive.com API: https://api.massive.com/docs
- Moving Averages: https://www.investopedia.com/terms/m/movingaverage.asp
- RSI Indicator: https://www.investopedia.com/terms/r/rsi.asp
- Technical Analysis: https://www.investopedia.com/terms/t/technicalanalysis.asp
