"""Stock data retrieval, formatting, and LLM summaries."""

import json
import random
import re
from pydantic import BaseModel
from typing import Any
import yfinance as yf
import ollama
from helpers.stock_plot import visualize

# ----------------------------
# Schemas
# ----------------------------
class DirectAnswer(BaseModel):
    answer: Any
    reasoning: str
    confidence: float

# ----------------------------
# Ticker extraction
# ----------------------------
FALLBACK_FIN_TICKERS = ["HSBC", "UBS"]

def extract_tickers(text: str) -> list[str]:
    tickers = re.findall(r'\b[A-Z]{1,5}\b', text)
    valid_tickers = [t for t in tickers if t not in ["API"]]
    if not valid_tickers:
        valid_tickers = random.sample(FALLBACK_FIN_TICKERS, k=min(2, len(FALLBACK_FIN_TICKERS)))
    return list(set(valid_tickers))

# ----------------------------
# Fetch stock data safely
# ----------------------------

def fetch_stock_data(ticker: str) -> DirectAnswer:
    """
    Fetch stock data from Yahoo Finance for the given ticker using fast_info.
    Returns a summary with all key metrics.
    """
    try:
        stock = yf.Ticker(ticker)
        fast = stock.fast_info

        if not fast or fast.get("lastPrice") is None:
            print("No financial data found for ticker:", ticker)
            return DirectAnswer(
                answer={},
                reasoning=f"No financial data found for ticker '{ticker}' (possibly invalid or delisted)",
                confidence=0.0
            )

        key_data = {
            "symbol": ticker.upper(),
            "lastPrice": fast.get("lastPrice"),
            "marketCap": fast.get("marketCap"),
            "yearHigh": fast.get("yearHigh"),
            "yearLow": fast.get("yearLow"),
            "sharesOutstanding": fast.get("sharesOutstanding"),
        }

        visualize([ticker])

        return DirectAnswer(
            answer=key_data,
            reasoning=f"Fetched Yahoo Finance fast_info data for ticker '{ticker}'.",
            confidence=0.95
        )

    except Exception as e:
        print("Error fetching data for ticker:", ticker)
        return DirectAnswer(
            answer={},
            reasoning=f"Error fetching data for ticker '{ticker}': {e}",
            confidence=0.0
        )

# ----------------------------
# Format stock data for LLM
# ----------------------------
def format_stock_data(key_data: dict) -> str:
    """
    Returns a nicely formatted string of all key stock metrics for LLM consumption.
    """
    return (
        f"Symbol: {key_data.get('symbol')}\n"
        f"Last Price: {key_data.get('lastPrice')}\n"
        f"Market Cap: {key_data.get('marketCap')}\n"
        f"52-Week High: {key_data.get('yearHigh')}\n"
        f"52-Week Low: {key_data.get('yearLow')}\n"
        f"Shares Outstanding: {key_data.get('sharesOutstanding')}"
    )

# ----------------------------
# Summarize stock data using LLM
# ----------------------------
def summarize_stock(ticker: str) -> str:
    """
    Summarize the stock data using LLM (gemma3:4b), including all key metrics.
    """
    result = fetch_stock_data(ticker)
    if not result.answer:
        return f"Cannot summarize: {result.reasoning}"

    formatted_data = format_stock_data(result.answer)

    prompt = f"""
You are a financial analyst. Analyse this stock data in detail, include all key metrics, trends, and observations in 3-4 concise sentences:

{formatted_data}

Return strictly plain text.
"""
    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return f"Unable to summarise stock data: {e}"

# ----------------------------
# Command-line interface
# ----------------------------
if __name__ == "__main__":
    while True:
        ticker = input("Enter a stock ticker (or 'exit' to quit): ").strip()
        if ticker.lower() == "exit":
            break

        stock_info = fetch_stock_data(ticker)
        print("\nRaw Data:")
        print(json.dumps(stock_info.dict(), indent=2))

        summary = summarize_stock(ticker)
        print("\nSummary:")
        print(summary)
        print("\n" + "-"*50 + "\n")
