"""
Stock analysis module for calculating technical indicators and generating
buy/sell/hold recommendations.

Indicators:
- SMA (Simple Moving Average): Trend identification
- RSI (Relative Strength Index): Momentum and overbought/oversold conditions

Recommendation Logic:
- BUY: Strong uptrend signals (price > MA, oversold RSI)
- SELL: Strong downtrend signals (price < MA, overbought RSI)
- HOLD: Mixed or neutral signals
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from massive_client import MassiveClient

logger = logging.getLogger(__name__)


def calculate_sma(prices: list[float], period: int) -> float | None:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of closing prices (oldest to newest)
        period: Number of periods to average (e.g., 20 for SMA-20)

    Returns:
        The SMA value, or None if insufficient data

    Example:
        prices = [100, 102, 101, 103, 105]
        sma_3 = calculate_sma(prices, 3)  # Average of last 3: (101+103+105)/3 = 103
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calculate_rsi(prices: list[float], period: int = 14) -> float | None:
    """
    Calculate Relative Strength Index (RSI).

    RSI measures momentum on a 0-100 scale:
    - RSI < 30: Oversold (potential buy signal)
    - RSI > 70: Overbought (potential sell signal)
    - RSI 30-70: Neutral

    Args:
        prices: List of closing prices (oldest to newest)
        period: RSI period (default: 14)

    Returns:
        RSI value (0-100), or None if insufficient data

    Example:
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                  111, 110, 112, 114, 113]
        rsi = calculate_rsi(prices, 14)
    """
    if len(prices) < period + 1:
        return None

    # Calculate price changes
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Separate gains and losses
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    # Calculate average gain and loss over the period
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    # Avoid division by zero
    if avg_loss == 0:
        return 100.0  # All gains, no losses

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def generate_recommendation(
    current_price: float,
    sma_20: float | None,
    sma_50: float | None,
    rsi: float | None,
    current_volume: float | None = None,
    avg_volume: float | None = None,
) -> tuple[str, float, list[str]]:
    """
    Generate a buy/sell/hold recommendation based on technical indicators.

    Scoring system:
    - Trend signals (moving averages): 0-3 points
    - Momentum signals (RSI): -2 to +2 points
    - Volume confirmation: 0-1 point

    Total score:
    - >= 3: BUY
    - <= -1: SELL
    - Otherwise: HOLD

    Args:
        current_price: Current stock price
        sma_20: 20-day simple moving average (or None)
        sma_50: 50-day simple moving average (or None)
        rsi: RSI value (0-100, or None)
        current_volume: Current trading volume (optional)
        avg_volume: Average trading volume (optional)

    Returns:
        (recommendation, confidence, reasons) tuple:
        - recommendation: 'BUY', 'SELL', or 'HOLD'
        - confidence: 0.0 to 1.0
        - reasons: List of human-readable reason strings

    Example:
        rec, conf, reasons = generate_recommendation(
            current_price=152.5,
            sma_20=150.0,
            sma_50=148.0,
            rsi=45.0
        )
        # Returns: ('BUY', 0.5, ['Price above 20-day MA', 'Price above 50-day MA'])
    """
    score = 0
    reasons = []

    # Trend signals (moving averages)
    if sma_20 is not None and current_price > sma_20:
        score += 1
        reasons.append(f"Price above 20-day MA (${sma_20:.2f})")
    elif sma_20 is not None and current_price < sma_20:
        reasons.append(f"Price below 20-day MA (${sma_20:.2f})")

    if sma_50 is not None and current_price > sma_50:
        score += 1
        reasons.append(f"Price above 50-day MA (${sma_50:.2f})")
    elif sma_50 is not None and current_price < sma_50:
        reasons.append(f"Price below 50-day MA (${sma_50:.2f})")

    if sma_20 is not None and sma_50 is not None and sma_20 > sma_50:
        score += 1
        reasons.append("Golden cross pattern (bullish)")
    elif sma_20 is not None and sma_50 is not None and sma_20 < sma_50:
        reasons.append("Death cross pattern (bearish)")

    # Momentum signals (RSI)
    if rsi is not None:
        if rsi < 30:
            score += 2
            reasons.append(f"Oversold (RSI: {rsi:.1f})")
        elif rsi > 70:
            score -= 2
            reasons.append(f"Overbought (RSI: {rsi:.1f})")
        else:
            reasons.append(f"Neutral momentum (RSI: {rsi:.1f})")

    # Volume confirmation
    if current_volume is not None and avg_volume is not None and avg_volume > 0:
        if current_volume > avg_volume * 1.2:
            score += 1
            reasons.append("Above-average volume (strong signal)")
        elif current_volume < avg_volume * 0.8:
            reasons.append("Below-average volume (weak signal)")

    # Generate final recommendation
    if score >= 3:
        recommendation = "BUY"
        confidence = min(score / 6.0, 1.0)
    elif score <= -1:
        recommendation = "SELL"
        confidence = min(abs(score) / 6.0, 1.0)
    else:
        recommendation = "HOLD"
        confidence = 0.5

    return recommendation, confidence, reasons


def analyze_stock(symbol: str, days: int = 50) -> dict[str, Any]:
    """
    Perform complete technical analysis for a stock symbol.

    Fetches historical data from Massive API, calculates indicators,
    and generates a recommendation.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        days: Number of historical days to analyze (default: 50)

    Returns:
        Dictionary with analysis results:
        {
            'symbol': 'AAPL',
            'current_price': 152.50,
            'sma_20': 150.00,
            'sma_50': 148.00,
            'rsi_14': 45.5,
            'volume_avg': 50000000,
            'recommendation': 'BUY',
            'confidence': 0.67,
            'reasons': ['Price above 20-day MA', ...],
            'analyzed_at': '2024-01-15T10:30:00Z'
        }

    Raises:
        Exception: If API call fails or insufficient data
    """
    client = MassiveClient()

    # Calculate date range
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")

    logger.info(f"Analyzing {symbol}: fetching {days} days of data ({from_date} to {to_date})")

    # Fetch historical data
    try:
        agg_data = client.get_aggregates(symbol, from_date, to_date)
    except Exception as e:
        logger.error(f"Failed to fetch aggregates for {symbol}: {e}")
        raise Exception(f"Could not fetch historical data for {symbol}: {str(e)}")

    # Extract price and volume data
    results = agg_data.get("results", [])
    if len(results) < 20:
        raise Exception(f"Insufficient data for {symbol}: only {len(results)} days available (need 20+)")

    closes = [bar["c"] for bar in results]
    volumes = [bar["v"] for bar in results]

    current_price = closes[-1]
    current_volume = volumes[-1]

    # Calculate indicators
    sma_20 = calculate_sma(closes, 20)
    sma_50 = calculate_sma(closes, 50)
    rsi_14 = calculate_rsi(closes, 14)
    volume_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None

    # Generate recommendation
    recommendation, confidence, reasons = generate_recommendation(
        current_price=current_price,
        sma_20=sma_20,
        sma_50=sma_50,
        rsi=rsi_14,
        current_volume=current_volume,
        avg_volume=volume_avg,
    )

    logger.info(
        f"Analysis complete for {symbol}: {recommendation} "
        f"(confidence: {confidence:.2f}, reasons: {len(reasons)})"
    )

    # Return analysis results
    return {
        "symbol": symbol,
        "current_price": current_price,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "rsi_14": rsi_14,
        "volume_avg": volume_avg,
        "recommendation": recommendation,
        "confidence": confidence,
        "reasons": reasons,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }
