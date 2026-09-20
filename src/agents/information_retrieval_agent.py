"""Compatibility imports; stock functionality lives in stock_analysis_agent."""

from agents.stock_analysis_agent import (
    DirectAnswer,
    fetch_stock_data,
    format_stock_data,
    summarize_stock,
)

__all__ = ["DirectAnswer", "fetch_stock_data", "format_stock_data", "summarize_stock"]
