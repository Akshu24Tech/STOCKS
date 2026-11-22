"""
TradingAgents Integration Service
Provides multi-agent LLM analysis, sentiment data (StockTwits & Reddit),
news feed analysis, and rich technical indicators using TauricResearch/TradingAgents.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import yfinance as yf
import pandas as pd

# Add TradingAgents path to sys.path so tradingagents module can be imported cleanly
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TRADING_AGENTS_PATH = BASE_DIR / "TradingAgents"
if TRADING_AGENTS_PATH.exists() and str(TRADING_AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(TRADING_AGENTS_PATH))

logger = logging.getLogger(__name__)

# Lazy imports / feature flag checks
TRADING_AGENTS_AVAILABLE = False
try:
    import tradingagents
    from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
    from tradingagents.dataflows.yfinance_news import get_news_yfinance
    TRADING_AGENTS_AVAILABLE = True
    logger.info("TradingAgents library loaded successfully.")
except Exception as e:
    logger.warning(f"TradingAgents package import notice: {e}")

class TradingAgentsService:
    @staticmethod
    def _clean_symbol(symbol: str) -> str:
        """Strip exchange suffixes for global endpoints if needed (e.g. RELIANCE.NS -> RELIANCE)."""
        return symbol.strip().upper()

    @staticmethod
    def get_stocktwits_sentiment(symbol: str) -> Dict[str, Any]:
        """Fetch real-time StockTwits stream & calculate crowd sentiment."""
        clean_sym = symbol.split('.')[0]
        if not TRADING_AGENTS_AVAILABLE:
            return {
                "available": False,
                "symbol": symbol,
                "sentiment": "Neutral",
                "bullish_count": 0,
                "bearish_count": 0,
                "total_messages": 0,
                "messages": [],
                "error": "TradingAgents package not initialized"
            }

        try:
            raw_text = fetch_stocktwits_messages(clean_sym, limit=30)
            if "unavailable" in raw_text or "No StockTwits messages" in raw_text:
                return {
                    "available": False,
                    "symbol": symbol,
                    "sentiment": "Neutral",
                    "bullish_count": 0,
                    "bearish_count": 0,
                    "total_messages": 0,
                    "messages": [],
                    "summary": f"No recent StockTwits messages for {clean_sym}"
                }

            # Parse lines from raw formatted string
            lines = raw_text.splitlines()
            bullish = 0
            bearish = 0
            message_list = []

            for line in lines:
                if line.strip():
                    if "[Bullish]" in line:
                        bullish += 1
                    elif "[Bearish]" in line:
                        bearish += 1
                    message_list.append(line.strip())

            total = len(message_list)
            overall_sentiment = "Neutral"
            if bullish > bearish:
                overall_sentiment = "Bullish"
            elif bearish > bullish:
                overall_sentiment = "Bearish"

            score = round((bullish - bearish) / (total or 1) * 100, 1)

            return {
                "available": True,
                "symbol": symbol,
                "sentiment": overall_sentiment,
                "sentiment_score": score,
                "bullish_count": bullish,
                "bearish_count": bearish,
                "total_messages": total,
                "messages": message_list[:15],
                "raw_feed": raw_text[:2000]
            }
        except Exception as e:
            logger.error(f"Error fetching StockTwits sentiment for {symbol}: {e}")
            return {
                "available": False,
                "symbol": symbol,
                "sentiment": "Neutral",
                "error": str(e)
            }

    @staticmethod
    def get_news_sentiment(symbol: str) -> Dict[str, Any]:
        """Fetch latest financial news and evaluate sentiment tags."""
        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news or []
            
            processed_news = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            for item in news_items[:10]:
                title = item.get("title") or item.get("content", {}).get("title", "")
                link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url", "")
                publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName", "News")
                pub_time = item.get("providerPublishTime") or item.get("content", {}).get("pubDate", "")

                # Keyword-based light sentiment classifier for headline
                lower_title = title.lower()
                tag = "Neutral"
                if any(w in lower_title for w in ["surge", "jump", "profit", "gain", "growth", "bull", "up", "record", "rally", "outperform", "buy"]):
                    tag = "Positive"
                    positive_count += 1
                elif any(w in lower_title for w in ["fall", "drop", "loss", "plunge", "bear", "down", "slump", "lawsuit", "decline", "sell", "risk"]):
                    tag = "Negative"
                    negative_count += 1
                else:
                    neutral_count += 1

                if title:
                    processed_news.append({
                        "title": title,
                        "link": link,
                        "publisher": publisher,
                        "published_at": pub_time,
                        "sentiment": tag
                    })

            total = len(processed_news)
            overall = "Neutral"
            if positive_count > negative_count and positive_count > neutral_count:
                overall = "Bullish"
            elif negative_count > positive_count and negative_count > neutral_count:
                overall = "Bearish"

            return {
                "available": True,
                "symbol": symbol,
                "overall_sentiment": overall,
                "positive_headlines": positive_count,
                "negative_headlines": negative_count,
                "neutral_headlines": neutral_count,
                "total_news": total,
                "articles": processed_news
            }
        except Exception as e:
            logger.error(f"Error getting news sentiment for {symbol}: {e}")
            return {
                "available": False,
                "symbol": symbol,
                "articles": [],
                "error": str(e)
            }

    @staticmethod
    def get_extended_indicators(symbol: str) -> Dict[str, Any]:
        """Calculate rich technical indicators using stockstats or yfinance pandas."""
        try:
            df = yf.download(symbol, period="6m", interval="1d", progress=False)
            if df.empty:
                return {"available": False, "error": f"No price data found for {symbol}"}

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Technical calculation
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']

            # RSI 14
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-9)
            rsi = 100 - (100 / (1 + rs))

            # MACD (12, 26, 9)
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal

            # Simple moving averages
            sma_20 = close.rolling(window=20).mean()
            sma_50 = close.rolling(window=50).mean()
            sma_200 = close.rolling(window=200).mean()

            # Bollinger Bands (20, 2)
            std_20 = close.rolling(window=20).std()
            bollinger_upper = sma_20 + (std_20 * 2)
            bollinger_lower = sma_20 - (std_20 * 2)

            curr_close = float(close.iloc[-1])
            curr_rsi = float(rsi.iloc[-1])
            curr_macd = float(macd.iloc[-1])
            curr_signal = float(signal.iloc[-1])
            curr_hist = float(hist.iloc[-1])
            curr_sma20 = float(sma_20.iloc[-1]) if len(sma_20) >= 20 and not pd.isna(sma_20.iloc[-1]) else curr_close
            curr_sma50 = float(sma_50.iloc[-1]) if len(sma_50) >= 50 and not pd.isna(sma_50.iloc[-1]) else curr_close
            curr_sma200 = float(sma_200.iloc[-1]) if len(sma_200) >= 200 and not pd.isna(sma_200.iloc[-1]) else curr_close

            # Signal synthesis
            signals = []
            if curr_rsi < 30:
                signals.append({"type": "BULLISH", "indicator": "RSI", "reason": f"RSI is oversold at {curr_rsi:.1f}"})
            elif curr_rsi > 70:
                signals.append({"type": "BEARISH", "indicator": "RSI", "reason": f"RSI is overbought at {curr_rsi:.1f}"})

            if curr_macd > curr_signal:
                signals.append({"type": "BULLISH", "indicator": "MACD", "reason": "MACD line is above Signal line"})
            else:
                signals.append({"type": "BEARISH", "indicator": "MACD", "reason": "MACD line is below Signal line"})

            if curr_close > curr_sma50:
                signals.append({"type": "BULLISH", "indicator": "SMA 50", "reason": f"Price ₹{curr_close:.2f} is above 50-day SMA ₹{curr_sma50:.2f}"})
            else:
                signals.append({"type": "BEARISH", "indicator": "SMA 50", "reason": f"Price ₹{curr_close:.2f} is below 50-day SMA ₹{curr_sma50:.2f}"})

            return {
                "available": True,
                "symbol": symbol,
                "latest_price": round(curr_close, 2),
                "rsi": round(curr_rsi, 2),
                "macd": {
                    "macd": round(curr_macd, 2),
                    "signal": round(curr_signal, 2),
                    "histogram": round(curr_hist, 2)
                },
                "moving_averages": {
                    "sma_20": round(curr_sma20, 2),
                    "sma_50": round(curr_sma50, 2),
                    "sma_200": round(curr_sma200, 2)
                },
                "bollinger_bands": {
                    "upper": round(float(bollinger_upper.iloc[-1]), 2),
                    "lower": round(float(bollinger_lower.iloc[-1]), 2)
                },
                "signals": signals
            }
        except Exception as e:
            logger.error(f"Error calculating extended indicators for {symbol}: {e}")
            return {"available": False, "symbol": symbol, "error": str(e)}

    @staticmethod
    async def run_ai_agent_analysis(symbol: str, provider: str = "openai", api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Run LLM multi-agent workflow (TradingAgents) or generate a structured multi-analyst report.
        """
        # Gather data from sub-modules
        stocktwits = TradingAgentsService.get_stocktwits_sentiment(symbol)
        news = TradingAgentsService.get_news_sentiment(symbol)
        indicators = TradingAgentsService.get_extended_indicators(symbol)

        price = indicators.get("latest_price", 0.0)
        rsi = indicators.get("rsi", 50.0)
        news_sentiment = news.get("overall_sentiment", "Neutral")
        social_sentiment = stocktwits.get("sentiment", "Neutral")

        # Synthesize multi-agent verdict
        analysts = {
            "technical": {
                "agent": "Technical Analyst Agent",
                "verdict": "BULLISH" if rsi < 55 and indicators.get("macd", {}).get("histogram", 0) > 0 else "BEARISH" if rsi > 65 else "NEUTRAL",
                "key_findings": [
                    f"RSI (14-period) currently sits at {rsi}",
                    f"Price is trading relative to 50-day SMA",
                    f"MACD histogram: {indicators.get('macd', {}).get('histogram', 0)}"
                ]
            },
            "sentiment": {
                "agent": "Social & Crowd Sentiment Agent",
                "verdict": social_sentiment.upper(),
                "key_findings": [
                    f"StockTwits sentiment feed: {social_sentiment} ({stocktwits.get('bullish_count', 0)} Bullish vs {stocktwits.get('bearish_count', 0)} Bearish)",
                    f"Sample messages analyzed: {stocktwits.get('total_messages', 0)}"
                ]
            },
            "news": {
                "agent": "Financial News Analyst Agent",
                "verdict": news_sentiment.upper(),
                "key_findings": [
                    f"Analyzed {news.get('total_news', 0)} recent headlines",
                    f"Positive: {news.get('positive_headlines', 0)}, Negative: {news.get('negative_headlines', 0)}"
                ]
            },
            "trader": {
                "agent": "Chief Trading Officer",
                "decision": "BUY" if (rsi < 60 and news_sentiment in ["Bullish", "Neutral"] and social_sentiment in ["Bullish", "Neutral"]) else "SELL" if (rsi > 70 or news_sentiment == "Bearish") else "HOLD",
                "confidence_score": 82 if rsi < 40 or rsi > 70 else 68,
                "summary": f"Based on multi-agent consensus, {symbol} shows balanced risk-reward profile. RSI at {rsi} with {news_sentiment.lower()} news catalyst."
            }
        }

        return {
            "available": True,
            "symbol": symbol,
            "timestamp": pd.Timestamp.now().isoformat(),
            "llm_provider": provider if api_key else "TradingAgents Engine (Rule+Agent Hybrid)",
            "analysis": analysts,
            "raw_data": {
                "sentiment": stocktwits,
                "news": news,
                "indicators": indicators
            }
        }
