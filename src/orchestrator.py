from customtkinter import *
import threading
import json
import traceback
from agents.planner_agent import handle_csv_upload, select_tools, generate_answer
from agents.context_memory import get_context_text

def log_status(stage: str, message: str):
    print(f"[DEBUG] [{stage}] {message}")

def process_csv_and_question(file_path: str, question: str):
    try:
        log_status("0% COMPLETED", f"Starting process for question: '{question}'")
        log_status("0% COMPLETED", f"Loading CSV from {file_path}")
        csv_data = handle_csv_upload(file_path)
        log_status("10% COMPLETED", "CSV successfully loaded")

        log_status("10% COMPLETED", "Selecting tools based on question and CSV data")
        tools_used = select_tools(question, csv_data)
        log_status("30% COMPLETED", f"Tools selected: {[t.tool for t in tools_used.tools]}")

        log_status("30% COMPLETED", "Generating final answer using selected tools")
        final_answer = generate_answer(question, tools_used, csv_data)

        log_status("90% COMPLETED", "Final answer generated successfully")
        context_text = get_context_text()

        result = {
            "tools_used": tools_used.dict(),
            "final_answer": final_answer.dict(),
            "context_memory": context_text
        }

        log_status("100% COMPLETED", "Process completed successfully")

        print("\n=== FINAL OUTPUT ===")
        print(json.dumps(result["tools_used"], indent=4, ensure_ascii=False))
        print(json.dumps(result["final_answer"], indent=4, ensure_ascii=False))
        print("\n=== CONTEXT MEMORY IS SAVED ===")

        return result

    except Exception as e:
        log_status("ERROR", f"An error occurred: {e}")
        traceback.print_exc()
        return {"error": str(e)}

def run_process_threaded(file_path, question):
    """Run process in a background thread so the UI stays responsive."""
    thread = threading.Thread(target=process_csv_and_question, args=(file_path, question))
    thread.start()

if __name__ == "__main__":
    file_path = "data/sales_data.csv"
    question = (
        "Based on the sales data, benchmark this against our competitors "
        "in the United Kingdom financial sector, HSBC, researching recent "
        "financial news, and getting real-time stock data from Yahoo Finance API "
        "to provide a comprehensive summary."
    )

    # Appearance mode should be set before creating widgets
    set_appearance_mode("Light")

    app = CTk()
    app.geometry("700x500")
    app.title("Multi-AI Agent Prototype")

    # --- Title ---
    label = CTkLabel(
        master=app,
        text="Multi-AI Agent Prototype",
        font=("Segoe UI", 20),
        text_color="black"
    )
    label.place(relx=0.5, rely=0.1, anchor=CENTER)

    # --- Question ---
    label2 = CTkLabel(
        master=app,
        text=f"Input: {question}",
        font=("Segoe UI", 15),
        text_color="black",
        wraplength=600,
        justify="center"
    )
    label2.place(relx=0.5, rely=0.3, anchor=CENTER)

    # --- Available Agents ---
    label3 = CTkLabel(
        master=app,
        text="Available Agents:\n- Data Analyst Agent \n- Planner Agent \n- Research Agent\n - Stock Analysis Agent",
        font=("Segoe UI", 15),
        text_color="black",
        wraplength=600,
        justify="center"
    )
    label3.place(relx=0.5, rely=0.52, anchor=CENTER)

    # --- Available LLMs ---
    label4 = CTkLabel(
        master=app,
        text="Available Large Language Models (LLMs):\n- Gemma-3 4B\n- Llama-3 8B",
        font=("Segoe UI", 15),
        text_color="black",
        wraplength=600,
        justify="center"
    )
    label4.place(relx=0.5, rely=0.75, anchor=CENTER)

    # --- Run Button ---
    btn = CTkButton(
        master=app,
        text="Run",
        font=("Segoe UI", 15),
        command=lambda: run_process_threaded(file_path, question)
    )
    btn.place(relx=0.5, rely=0.90, anchor=CENTER)

    app.mainloop()
