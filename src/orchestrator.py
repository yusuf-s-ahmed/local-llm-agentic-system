"""Coordinate CSV analysis and launch the optional desktop interface."""

import traceback
from pathlib import Path

from agents.planner_agent import handle_csv_upload, select_tools, generate_answer
from agents.context_memory import get_context_text
from helpers.agent_trace import emit_trace, traced_call, trace_sink


def log_status(stage: str, message: str, on_log=None):
    line = f"{stage} {message}"
    print(line)

    if on_log:
        on_log(line)


def process_csv_and_question(
    file_path: str,
    question: str,
    selected_tools: list[str],
    selected_llm: str,
    on_log=None,
    on_trace=None,
):
    events = []

    def record(event):
        events.append(event)
        if on_trace:
            on_trace(event)

    token = trace_sink.set(record)
    try:
        def report(stage, message):
            log_status(stage, message, on_log)

        report("░░░░░░░░░░░░░░░░░░░░░░░░░ 0%", f"\nstarting process for question: \n'{question}'")
        report("█░░░░░░░░░░░░░░░░░░░░░░░░ 2%", f"loading CSV from '{file_path}'")

        csv_data = traced_call("CSV loader", Path(file_path).name, handle_csv_upload, file_path)
        emit_trace("CSV data + question", "Planner Agent", status="running",
                   detail=f"{len(csv_data)} rows, {len(csv_data.columns)} columns")
        report("███░░░░░░░░░░░░░░░░░░░░░░ 10%", "\nCSV successfully loaded")

        tool_preferences = ", ".join(selected_tools) or "let the planner choose"
        planner_question = (
            f"{question}\n\n"
            f"use these selected tools where applicable: {tool_preferences}.\n"
            f"use this selected LLM: {selected_llm}."
        )

        report("████░░░░░░░░░░░░░░░░░░░░░ 15%", "\nselecting tools")
        tools_used = traced_call("Planner agent", "LLM / tool selection", select_tools, planner_question, csv_data)
        emit_trace("planner agent", "tool plan", "execution agents",
                   detail=", ".join(tool.tool for tool in tools_used.tools))

        report(
            "█████░░░░░░░░░░░░░░░░░░░░ 20%",
            f"\ntools selected: {[tool.tool for tool in tools_used.tools]}",
        )

        report("████████░░░░░░░░░░░░░░░░░ 30%", "\ngenerating final answer")
        final_answer = generate_answer(planner_question, tools_used, csv_data)
        emit_trace("final answer agent", "summary", status="completed")

        result = {
            "tools_used": tools_used.dict(),
            "final_answer": final_answer.dict(),
            "context_memory": get_context_text(),
            "agent_trace": events,
        }

        report("█████████████████████████ 100%", "\nprocess completed successfully")
        return result

    except Exception as error:
        report("ERROR", str(error))
        traceback.print_exc()
        emit_trace("analysis", status="error", detail=str(error))
        return {"error": str(error), "agent_trace": events}
    finally:
        trace_sink.reset(token)


if __name__ == "__main__":
    from ui.desktop import launch_app

    launch_app(process_csv_and_question)
