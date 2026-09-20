"""CustomTkinter interface, background worker, and live progress display."""

import io
import json
import os
import re
import threading
from queue import Queue, Empty
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tkinter import END, filedialog
from PIL import Image, ImageTk

from customtkinter import (
    CTk,
    CTkButton,
    CTkCheckBox,
    CTkLabel,
    CTkTextbox,
    CTkFrame,
    CTkRadioButton,
    CTkTabview,
    StringVar,
    set_appearance_mode,
    set_default_color_theme,
)

font = "Segoe UI"

DEFAULT_QUESTION = (
    "Based on the sales data, benchmark this against our competitors "
    "in the United Kingdom financial sector, HSBC, researching recent "
    "financial news, and getting real-time stock data from Yahoo Finance API "
    "to provide a comprehensive summary."
)

AVAILABLE_TOOLS = [
    "Data Analyst Agent",
    "Planner Agent",
    "Research Agent",
    "Stock Analysis Agent",
]

AVAILABLE_LLMS = [
    "Gemma-3 4B",
    "Llama-3 8B",
]


def run_process_threaded(
    selected_csv_path,
    question,
    tools,
    selected_llm,
    on_complete,
    on_log,
    on_trace=None,
    *,
    process,
):
    def worker():
        output = LiveLogStream(on_log)

        with redirect_stdout(output), redirect_stderr(output):
            result = process(
                selected_csv_path,
                question,
                tools,
                selected_llm,
                on_trace=on_trace,
            )
        output.flush()
        on_complete(result)

    threading.Thread(target=worker, daemon=True).start()


class LiveLogStream(io.TextIOBase):
    def __init__(self, callback):
        self.callback = callback
        self.pending = ""

    def write(self, text):
        self.pending += text
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            if line.strip():
                self.callback(line)
        return len(text)

    def flush(self):
        if self.pending:
            self.callback(self.pending)
            self.pending = ""


def launch_app(process):
    """Launch the desktop UI with the supplied analysis callable."""
    file_path = "data/sales_data.csv"

    set_appearance_mode("Light")
    set_default_color_theme("blue")

    app = CTk()
    app.geometry("1100x820")
    app.minsize(900, 700)
    app.title("Local LLM Agentic System")
    app.configure(fg_color="#F5F7FA")

    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=0)
    app.grid_rowconfigure(1, weight=2, minsize=240)
    app.grid_rowconfigure(2, weight=0)

    inputs_panel = CTkFrame(app, fg_color="transparent")
    inputs_panel.grid(row=0, column=0, sticky="nsew")
    inputs_panel.grid_columnconfigure(0, weight=1)

    COLORS = {
        "background": "#F5F7FA",
        "card": "#FFFFFF",
        "border": "#E5E7EB",
        "text": "#172033",
        "muted": "#667085",
        "accent": "#3288D8",
        "accent_hover": "#2674BD",
        "input": "#FCFDFE",
    }

    title = CTkLabel(
        inputs_panel,
        text="Local LLM Agentic System",
        font=(font, 20, "bold"),
        text_color=COLORS["text"],
    )
    title.grid(row=0, column=0, pady=(25, 25))

    question_frame = CTkFrame(
        inputs_panel,
        fg_color=COLORS["card"],
        border_width=1,
        border_color=COLORS["border"],
        corner_radius=12,
    )
    question_frame.grid(
        row=1,
        column=0,
        padx=250,
        pady=(0, 14),
        sticky="ew",
    )
    question_frame.grid_columnconfigure(0, weight=1)

    CTkLabel(
        question_frame,
        text="What would you like the agents to investigate?",
        font=(font, 15, "bold"),
        text_color=COLORS["text"],
    ).grid(row=0, column=0, padx=18, pady=(15, 3), sticky="w")

    CTkLabel(
        question_frame,
        text="Edit the pre-filled question or enter your own.",
        font=(font, 12),
        text_color=COLORS["muted"],
    ).grid(row=1, column=0, padx=18, pady=(0, 8), sticky="w")

    question_box = CTkTextbox(
        question_frame,
        height=70,
        wrap="word",
        fg_color=COLORS["input"],
        border_width=1,
        border_color=COLORS["border"],
        corner_radius=8,
        text_color=COLORS["text"],
    )
    question_box.grid(
        row=2,
        column=0,
        padx=18,
        pady=(0, 18),
        sticky="ew",
    )
    question_box.insert("1.0", DEFAULT_QUESTION)

    options_frame = CTkFrame(
        inputs_panel,
        fg_color="transparent",
    )
    options_frame.grid(
        row=3,
        column=0,
        padx=250,
        pady=(0, 14),
        sticky="ew",
    )
    options_frame.grid_columnconfigure(0, weight=1)
    options_frame.grid_columnconfigure(1, weight=1)

    tools_frame = CTkFrame(
        options_frame,
        fg_color=COLORS["card"],
        border_width=1,
        border_color=COLORS["border"],
        corner_radius=12,
    )
    tools_frame.grid(
        row=0,
        column=0,
        padx=(0, 8),
        pady=0,
        sticky="nsew",
    )

    CTkLabel(
        tools_frame,
        text="Agents",
        font=(font, 15, "bold"),
        text_color=COLORS["text"],
    ).pack(anchor="w", padx=20, pady=(16, 2))

    CTkLabel(
        tools_frame,
        text="Choose which capabilities are available to the planner.",
        font=(font, 12),
        text_color=COLORS["muted"],
    ).pack(anchor="w", padx=20, pady=(0, 10))

    tool_vars = {}

    for tool in AVAILABLE_TOOLS:
        var = StringVar(value="on")
        tool_vars[tool] = var

        CTkCheckBox(
            tools_frame,
            text=tool,
            variable=var,
            onvalue="on",
            offvalue="off",
            font=(font, 13),
            text_color=COLORS["text"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=5,
        ).pack(anchor="w", padx=20, pady=7)

    CTkLabel(
        tools_frame,
        text="",
    ).pack(pady=2)

    llm_frame = CTkFrame(
        options_frame,
        fg_color=COLORS["card"],
        border_width=1,
        border_color=COLORS["border"],
        corner_radius=12,
    )
    llm_frame.grid(
        row=0,
        column=1,
        padx=(8, 0),
        pady=0,
        sticky="nsew",
    )

    CTkLabel(
        llm_frame,
        text="Language model",
        font=(font, 15, "bold"),
        text_color=COLORS["text"],
    ).pack(anchor="w", padx=20, pady=(16, 2))

    CTkLabel(
        llm_frame,
        text="Select the model used to coordinate the analysis.",
        font=(font, 12),
        text_color=COLORS["muted"],
    ).pack(anchor="w", padx=20, pady=(0, 10))

    selected_llm = StringVar(value=AVAILABLE_LLMS[0])

    for llm in AVAILABLE_LLMS:
        CTkRadioButton(
            llm_frame,
            text=llm,
            variable=selected_llm,
            value=llm,
            font=(font, 13),
            text_color=COLORS["text"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
        ).pack(anchor="w", padx=20, pady=8)

    results_tabs = CTkTabview(
        app,
        fg_color=COLORS["card"],
        segmented_button_fg_color="#EEF2F6",
        segmented_button_selected_color=COLORS["accent"],
        segmented_button_selected_hover_color=COLORS["accent_hover"],
        segmented_button_unselected_color="#EEF2F6",
        segmented_button_unselected_hover_color="#E3EAF2",
        text_color=COLORS["text"],
        corner_radius=12,
    )
    results_tabs.grid(
        row=1,
        column=0,
        padx=250,
        pady=(0, 26),
        sticky="nsew",
    )

    results_tabs.add("Summary")
    results_tabs.add("Agent Trace")
    results_tabs.add("Live Logs")
    results_tabs.add("Raw JSON")
    results_tabs.add("Visualisations")

    expanded = False
    expand_buttons = []

    def toggle_results():
        nonlocal expanded
        expanded = not expanded
        inputs_panel.grid_remove() if expanded else inputs_panel.grid()
        for button in expand_buttons:
            button.configure(text="Restore panels" if expanded else "Expand panel")

    for tab_name in ("Summary", "Agent Trace", "Live Logs", "Raw JSON", "Visualisations"):
        toolbar = CTkFrame(results_tabs.tab(tab_name), fg_color="transparent")
        toolbar.pack(fill="x", padx=12, pady=(6, 0))
        button = CTkButton(toolbar, text="Expand panel", width=130, height=28,
                           command=toggle_results)
        button.pack(side="right")
        expand_buttons.append(button)

    app.bind("<Escape>", lambda event: toggle_results() if expanded else None)

    summary_box = CTkTextbox(
        results_tabs.tab("Summary"),
        wrap="word",
        fg_color=COLORS["input"],
        text_color=COLORS["text"],
    )
    summary_box.pack(fill="both", expand=True, padx=12, pady=12)

    trace_container = results_tabs.tab("Agent Trace")

    trace_flow_frame = CTkFrame(
        trace_container,
        fg_color=COLORS["card"],
    )
    trace_flow_frame.pack(fill="x", padx=12, pady=(12, 4))
    trace_status = CTkLabel(trace_flow_frame, text="Ready — run an analysis to see the live flow.",
                            anchor="w", text_color=COLORS["muted"])
    trace_status.pack(fill="x")

    trace_box = CTkTextbox(
        trace_container,
        font=("Consolas", 13),
        wrap="word",
        fg_color=COLORS["input"],
        text_color=COLORS["text"],
        border_width=1,
        border_color=COLORS["border"],
    )
    trace_box.pack(fill="both", expand=True, padx=12, pady=8)

    logs_box = CTkTextbox(
        results_tabs.tab("Live Logs"),
        font=("Consolas", 13),
        wrap="word",
        fg_color=COLORS["input"],
        text_color=COLORS["text"],
        border_width=1,
        border_color=COLORS["border"],
    )
    logs_box.pack(fill="both", expand=True, padx=12, pady=12)

    raw_json_box = CTkTextbox(
        results_tabs.tab("Raw JSON"),
        font=("Consolas", 13),
        wrap="word",
        fg_color=COLORS["input"],
        text_color=COLORS["text"],
        border_width=1,
        border_color=COLORS["border"],
    )
    raw_json_box.pack(fill="both", expand=True, padx=12, pady=12)

    visualisation_content = CTkFrame(
        results_tabs.tab("Visualisations"), fg_color="transparent",
    )
    visualisation_content.pack(fill="both", expand=True, padx=12, pady=12)

    visualisation_label = CTkLabel(
        visualisation_content,
        text="Visualisations will appear here.",
        text_color=COLORS["muted"],
    )
    visualisation_label.pack(expand=True, padx=12, pady=12)

    visualisation_button = CTkButton(
        visualisation_content,
        text="No visualisation available",
        width=220,
        height=44,
        corner_radius=10,
        state="disabled",
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
    )
    visualisation_button.pack(pady=(0, 12))

    visualisation_path = Path("data/stock_plot.png")

    def open_visualisation():
        if visualisation_path.exists():
            os.startfile(str(visualisation_path.resolve()))

    def set_box_text(box, text):
        box.configure(state="normal")
        box.delete("1.0", END)
        box.markdown_images = []
        box.insert("1.0", text)
        box.configure(state="disabled")

    ui_events = Queue()

    def append_text(box, text):
        box.configure(state="normal")
        box.insert(END, text + "\n")
        box.see(END)
        box.configure(state="disabled")

    def display_trace(event):
        flow = "  →  ".join(event["nodes"])
        status = event["status"].upper()
        trace_status.configure(text=f"{status}: {event['nodes'][-1]}")
        detail = f"\n    {event['detail']}" if event.get("detail") else ""
        append_text(trace_box, f"{event['time']}  [{status}]  {flow}{detail}\n")

    def poll_events():
        try:
            for _ in range(100):
                kind, payload = ui_events.get_nowait()
                if kind == "log":
                    append_text(logs_box, payload)
                elif kind == "trace":
                    display_trace(payload)
                elif kind == "result":
                    display_result(payload)
        except Empty:
            pass
        finally:
            app.after(50, poll_events)

    def display_result(result):
        if "error" in result:
            set_box_text(summary_box, f"Error: {result['error']}")
            set_box_text(
                raw_json_box,
                json.dumps(result, indent=2, ensure_ascii=False),
            )

            visualisation_button.configure(
                text="No visualisation available",
                state="disabled",
                command=lambda: None,
            )

            run_button.configure(state="normal", text="Run Analysis")
            return

        final_answer = result.get("final_answer", {})
        answer = final_answer.get("answer", "No answer returned.")

        summary_markdown = answer if isinstance(answer, str) else json.dumps(answer, indent=2, ensure_ascii=False)
        if visualisation_path.exists():
            summary_markdown += f"\n\n![Stock analysis chart]({visualisation_path.as_posix()})\n"
        render_markdown(summary_box, summary_markdown)
        set_box_text(raw_json_box, json.dumps(result, indent=2, ensure_ascii=False))

        if visualisation_path.exists():
            visualisation_label.configure(text="The chart is displayed after the text in Summary.")
            visualisation_button.configure(
                text="View visualisation",
                state="normal",
                command=open_visualisation,
            )
        else:
            visualisation_label.configure(text="No visualisation available for this analysis.")
            visualisation_button.configure(
                text="No visualisation available",
                state="disabled",
                command=lambda: None,
            )

        run_button.configure(state="normal", text="Run Analysis")

    def start_process():

        visualisation_button.configure(
            text="Generating visualisation...",
            state="disabled",
            command=lambda: None,
        )
        question = question_box.get("1.0", END).strip()

        tools = [
            tool
            for tool, var in tool_vars.items()
            if var.get() == "on"
        ]

        if not question:
            return

        for box in (summary_box, trace_box, raw_json_box):
            set_box_text(box, "")
        trace_status.configure(text="Starting analysis...")
        results_tabs.set("Agent Trace")

        logs_box.configure(state="normal")
        logs_box.delete("1.0", END)
        logs_box.configure(state="disabled")

        run_button.configure(state="disabled", text="Running...")

        run_process_threaded(
            selected_csv_path.get(),
            question,
            tools,
            selected_llm.get(),
            lambda result: ui_events.put(("result", result)),
            lambda message: ui_events.put(("log", message)),
            lambda event: ui_events.put(("trace", event)),
            process=process,
        )

    run_button = CTkButton(
        app,
        text="Run Analysis",
        width=180,
        height=42,
        corner_radius=9,
        font=(font, 14, "bold"),
        fg_color="#3288D8",
        hover_color="#2674BD",
        command=start_process,
    )
    run_button.grid(row=2, column=0, pady=(0, 22))

    def resize_markdown_images(box):
        text_widget = box._textbox
        width = max(1, text_widget.winfo_width() - 24)
        for entry in getattr(box, "markdown_images", []):
            original = entry["original"]
            target_width = min(width, original.width)
            if entry.get("width") == target_width:
                continue
            resized = original.resize(
                (target_width, max(1, round(original.height * target_width / original.width))),
                Image.Resampling.LANCZOS,
            )
            entry["photo"] = ImageTk.PhotoImage(resized, master=text_widget)
            entry["width"] = target_width
            text_widget.image_configure(entry["name"], image=entry["photo"])

    summary_box._textbox.bind("<Configure>", lambda event: resize_markdown_images(summary_box), add="+")

    def render_markdown(box, markdown_text):
        box.configure(state="normal")
        box.delete("1.0", END)
        box.markdown_images = []

        text_widget = box._textbox

        text_widget.tag_configure(
            "heading",
            font=(font, 15, "bold"),
            foreground=COLORS["text"],
            spacing1=8,
            spacing3=4,
        )
        text_widget.tag_configure(
            "bold",
            font=(font, 12, "bold"),
            foreground=COLORS["text"],
        )
        text_widget.tag_configure(
            "bullet",
            lmargin1=18,
            lmargin2=32,
        )
        text_widget.tag_configure("image_center", justify="center")

        for line in markdown_text.splitlines():
            stripped = line.strip()

            image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if image_match and Path(image_match[2]) == visualisation_path:
                try:
                    with Image.open(visualisation_path) as source:
                        original = source.copy()
                    photo = ImageTk.PhotoImage(original, master=text_widget)
                    image_start = text_widget.index("end-1c")
                    name = text_widget.image_create(END, image=photo)
                    box.markdown_images.append({"original": original, "photo": photo, "name": name})
                    box.insert(END, "\n")
                    text_widget.tag_add("image_center", image_start, f"{image_start} lineend+1c")
                except (OSError, ValueError):
                    box.insert(END, f"{image_match[1]} (image unavailable)\n")
                continue

            if stripped.startswith("### "):
                box.insert(END, stripped[4:] + "\n", "heading")
                continue

            if stripped.startswith("## "):
                box.insert(END, stripped[3:] + "\n", "heading")
                continue

            if stripped.startswith("# "):
                box.insert(END, stripped[2:] + "\n", "heading")
                continue

            if stripped.startswith(("* ", "- ")):
                box.insert(END, "• ", "bullet")
                line = stripped[2:]
                tag = "bullet"
            else:
                tag = None

            parts = re.split(r"(\*\*.*?\*\*|__.*?__)", line)

            for part in parts:
                if not part:
                    continue

                if (
                    part.startswith("**")
                    and part.endswith("**")
                ) or (
                    part.startswith("__")
                    and part.endswith("__")
                ):
                    box.insert(END, part[2:-2], "bold")
                else:
                    box.insert(END, part, tag)

            box.insert(END, "\n")

        box.configure(state="disabled")
        resize_markdown_images(box)
        text_widget.yview_moveto(0)

    selected_csv_path = StringVar(value=file_path)

    def choose_csv():
        selected = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*"),
            ],
        )

        if selected:
            selected_csv_path.set(selected)
            csv_path_label.configure(text=Path(selected).name)

    csv_frame = CTkFrame(
        inputs_panel,
        fg_color=COLORS["card"],
        border_width=1,
        border_color=COLORS["border"],
        corner_radius=12,
    )
    csv_frame.grid(
        row=2,
        column=0,
        padx=250,
        pady=(0, 14),
        sticky="ew",
    )
    csv_frame.grid_columnconfigure(1, weight=1)

    CTkLabel(
        csv_frame,
        text="Sales data",
        font=(font, 15, "bold"),
        text_color=COLORS["text"],
    ).grid(row=0, column=0, padx=18, pady=14)

    csv_path_label = CTkLabel(
        csv_frame,
        text=Path(file_path).name,
        text_color=COLORS["muted"],
        anchor="w",
    )
    csv_path_label.grid(row=0, column=1, padx=8, sticky="ew")

    CTkButton(
        csv_frame,
        text="Choose CSV",
        width=125,
        command=choose_csv,
    ).grid(row=0, column=2, padx=18, pady=10)

    app.after(50, poll_events)
    app.mainloop()
