# planner_agent.py

import pandas as pd
import json
from pydantic import BaseModel
from typing import Any, Optional, List
import ollama
from agents.data_analyst_agent import analyze_csv
from agents.researcher_agent import web_scrape
from agents.context_memory import save_context, get_context_text
from agents.stock_analysis_agent import extract_tickers, fetch_stock_data, format_stock_data
from helpers.llm_utils import clean_llm_json
from helpers.agent_trace import emit_trace, traced_call

# ----------------------------
# Schemas
# ----------------------------
class DirectAnswer(BaseModel):
    answer: Any
    reasoning: str
    confidence: float

class ToolCall(BaseModel):
    tool: str
    details: str
    require_csv: Optional[bool] = False

class MultiToolCall(BaseModel):
    action: str
    tools: List[ToolCall]

class ToolSpec(BaseModel):
    name: str
    description: str
    requires_csv: bool = False

# ----------------------------
# Tools
# ----------------------------
available_tools: List[ToolSpec] = [
    ToolSpec(name="csv", description="Analyze uploaded CSV data for totals, averages, metrics.", requires_csv=True),
    ToolSpec(name="web_scrape", description="Research online news or updates about a topic.", requires_csv=False),
    ToolSpec(name="api_call", description="Fetch stock/market/company data from Yahoo Finance.", requires_csv=False)
]

# ----------------------------
# CSV loader
# ----------------------------
def handle_csv_upload(file_path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

# ----------------------------
# Select tools dynamically
# ----------------------------
def select_tools(question: str, data: Optional[pd.DataFrame] = None) -> MultiToolCall:
    data_summary = data.to_csv(index=False) if data is not None else ""
    csv_text = f"CSV data:\n{data_summary}" if data_summary else "No CSV provided."
    tools_json = json.dumps([tool.dict() for tool in available_tools], indent=2)

    prompt = f"""
You are an AI planner. Based on the CSV and the question below, decide which tools to use.
Do NOT answer the question, only return JSON with the format:

{{
  "action": "use_tool",
  "tools": [
    {{"tool": "<tool_name>", "details": "Explain what the tool should do", "require_csv": true|false}}
  ]
}}

CSV context:
{csv_text}

Question: {question}

Available tools:
{tools_json}

Rules:
- Include "csv" if CSV is provided.
- Include "api_call" if the question asks about companies, tickers, or stock/market data.
- Include "web_scrape" if the question asks about news or trends.
- Return valid JSON only.
"""
    response = ollama.chat(model="gemma3:4b", messages=[{"role": "user", "content": prompt}])
    raw_output = clean_llm_json(response["message"]["content"].strip())

    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, list):
            parsed = {"action": "use_tool", "tools": parsed}
    except json.JSONDecodeError:
        parsed = {"action": "use_tool", "tools": []}

    if "action" not in parsed:
        parsed["action"] = "use_tool"
    if "tools" not in parsed:
        parsed["tools"] = []

    return MultiToolCall(**parsed)

# ----------------------------
# Generate final answer
# ----------------------------
def generate_answer(question: str, tools_used: MultiToolCall, data: Optional[pd.DataFrame] = None) -> DirectAnswer:
    agent_outputs = {}

    for tool in tools_used.tools:
        if tool.tool == "csv":
            emit_trace("CSV data", "Data Analyst Agent", status="running")
            res = traced_call("Data Analyst Agent", "csv / LLM analysis", analyze_csv, df=data)
            agent_outputs["csv"] = res.dict()
            print("██████████░░░░░░░░░░░░░░░ 40% \nCSV analysis complete")

        elif tool.tool == "api_call":
            tickers = extract_tickers(tool.details or question)
            print("███████████░░░░░░░░░░░░░░ 45% \nticker(s) extracted", tickers)
            api_results = {}
            for ticker in tickers:
                count = 1
                res = traced_call("Stock Analysis Agent", f"api_call / Yahoo Finance / {ticker}", fetch_stock_data, ticker)
                print(f"█████████████░░░░░░░░░░░░ 50% \nAPI call complete for ticker {count}: ", ticker)
                if res.answer:
                    formatted = format_stock_data(res.answer)
                    api_results[ticker] = {"raw": res.dict(), "formatted": formatted}
                    print("stock data found for: ", ticker)
                else:
                    api_results[ticker] = res.dict()
                    print("stock data not found for:", ticker)
                count += 1

            agent_outputs["api_call"] = api_results

        elif tool.tool == "web_scrape":
            emit_trace("Question", "Research Agent", status="running")
            res = traced_call("Research Agent", "web_scrape", web_scrape, query=question)
            agent_outputs["web_scrape"] = res.dict()
            print("██████████████░░░░░░░░░░░ 55% \nweb scraping complete")

        else:
            agent_outputs[tool.tool] = {"answer": None, "reasoning": "tool not implemented", "confidence": 0.0}

        agent = {"csv": "Data Analyst Agent", "api_call": "Stock Analysis Agent",
                 "web_scrape": "Research Agent"}.get(tool.tool, tool.tool)
        emit_trace(agent, f"{tool.tool} result data", "Final Answer Agent",
                   status="completed" if tool.tool in {"csv", "api_call", "web_scrape"} else "warning")

    save_context(question, agent_outputs)
    context_text = get_context_text()

    print("██████████████████░░░░░░░ 70% \ntool outputs collected for final answer")

    planner_prompt = f"""
You are a reasoning agent.

Context:
{context_text}

Question: {question}

Tool outputs:
{json.dumps(agent_outputs, indent=2)}

Instructions:
- Include all stock metrics (symbol, lastPrice, marketCap, yearHigh, yearLow, sharesOutstanding) in your final answer.
- Include revenue data from CSV if available.
- Include insights from web scraping if available.
- Provide a combined summary that mentions trends, stock data, and research insights.
- Return JSON with keys: answer, reasoning, confidence
"""

    print("attempting to generate final answer")

    response = traced_call("Final Answer Agent", "LLM / gemma3:4b", ollama.chat, model="gemma3:4b", messages=[{"role": "user", "content": planner_prompt}])
    raw_output = clean_llm_json(response["message"]["content"].strip())

    print("successfully generated final answer")

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = {"answer": "unable to generate final answer", "reasoning": "parsing error", "confidence": 0.0}

    return DirectAnswer(**parsed)

# ----------------------------
# CLI Example
# ----------------------------
if __name__ == "__main__":
    while True:
        question = input("Enter a question (or 'exit' to quit): ").strip()
        if question.lower() == "exit":
            break

        df = None  # optionally load CSV here
        tools = select_tools(question, data=df)
        final_answer = generate_answer(question, tools_used=tools, data=df)

        print("\nFinal Answer JSON:")
        print(json.dumps(final_answer.dict(), indent=2))
        print("\n" + "-"*50 + "\n")
