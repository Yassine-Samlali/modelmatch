#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║                      ModelMatch LLM v1.0                        ║
║         Local AI Model Recommender for Windows PCs              ║
╚══════════════════════════════════════════════════════════════════╝

Analyzes your PC's hardware (RAM, GPU VRAM) and recommends which
open-source LLMs you can realistically run locally using 4-bit
quantized GGUF models.

────────────────────────────────────────────────────────────────────
COMPILATION INSTRUCTIONS
────────────────────────────────────────────────────────────────────

1. Install dependencies:
      pip install psutil rich

2. (Optional) Test it first:
      python modelmatch_llm.py

3. Compile to a standalone .exe:
      pyinstaller --onefile --name ModelMatchLLM modelmatch_llm.py

   The final .exe will be in the  dist/  folder.
────────────────────────────────────────────────────────────────────
"""

import io
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime

# ── Force UTF-8 stdout so box-drawing characters render on Windows ──
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

import urllib.request
import urllib.error

import psutil
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, DownloadColumn, TransferSpeedColumn
from rich.table import Table
from rich.text import Text

# ─── Constants ────────────────────────────────────────────────────
APP_NAME = "ModelMatch LLM"
APP_VERSION = "1.0.0"

# ─── Rich Console ─────────────────────────────────────────────────
console = Console(force_terminal=True)

# ─── Model Database ──────────────────────────────────────────────
# Each entry represents a popular open-source LLM with realistic
# requirements for 4-bit quantized GGUF inference (e.g., llama.cpp,
# Ollama, LM Studio, GPT4All).
#
# Fields:
#   name            – Display name
#   parameters      – Parameter count string
#   min_ram_gb      – Minimum system RAM needed (GB)
#   min_vram_gb     – Minimum GPU VRAM for full offload (GB);
#                     0 means CPU-only is perfectly fine
#   use_case        – Short description of the model's strength
#   quant_size_gb   – Approximate download size of the Q4_K_M GGUF

MODEL_DATABASE = [
    {
        "name": "Phi-3.5 Mini (2026 Edition)",
        "parameters": "3.8B",
        "min_ram_gb": 4,
        "min_vram_gb": 0,
        "use_case": "Ultra-light reasoning, coding assistant",
        "quant_size_gb": 2.2,
        "download_url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
    },
    {
        "name": "Gemma 2 2B Instruct",
        "parameters": "2B",
        "min_ram_gb": 4,
        "min_vram_gb": 0,
        "use_case": "Edge-device chat, fast summarization",
        "quant_size_gb": 1.6,
        "download_url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
    },
    {
        "name": "Llama 3.1 8B Instruct",
        "parameters": "8B",
        "min_ram_gb": 8,
        "min_vram_gb": 6,
        "use_case": "Versatile assistant, creative writing",
        "quant_size_gb": 4.6,
        "download_url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    },
    {
        "name": "Mistral 7B v0.3",
        "parameters": "7B",
        "min_ram_gb": 8,
        "min_vram_gb": 4,
        "use_case": "General chat, balanced performance",
        "quant_size_gb": 4.1,
        "download_url": "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
    },
    {
        "name": "Qwen 2.5 14B",
        "parameters": "14B",
        "min_ram_gb": 12,
        "min_vram_gb": 8,
        "use_case": "Math, coding, and long-context tasks",
        "quant_size_gb": 8.4,
        "download_url": "https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct-Q4_K_M.gguf",
    },
    {
        "name": "DeepSeek-Coder-V2 Lite",
        "parameters": "16B (MoE)",
        "min_ram_gb": 12,
        "min_vram_gb": 6,
        "use_case": "Code generation & debugging",
        "quant_size_gb": 9.7,
        "download_url": "https://huggingface.co/bartowski/DeepSeek-Coder-V2-Lite-Base-GGUF/resolve/main/DeepSeek-Coder-V2-Lite-Base-Q4_K_M.gguf",
    },
    {
        "name": "Command-R (35B)",
        "parameters": "35B",
        "min_ram_gb": 24,
        "min_vram_gb": 16,
        "use_case": "RAG, enterprise search, tool use",
        "quant_size_gb": 20.0,
        "download_url": "https://huggingface.co/bartowski/c4ai-command-r-v01-GGUF/resolve/main/c4ai-command-r-v01-Q4_K_M.gguf",
    },
    {
        "name": "Llama 3.3 70B Instruct",
        "parameters": "70B",
        "min_ram_gb": 48,
        "min_vram_gb": 40,
        "use_case": "Near-GPT-4 quality, research-grade",
        "quant_size_gb": 39.6,
        "download_url": "https://huggingface.co/bartowski/Llama-3.3-70B-Instruct-GGUF/resolve/main/Llama-3.3-70B-Instruct-Q4_K_M.gguf",
    },
    {
        "name": "Mixtral 8x7B",
        "parameters": "46.7B (MoE)",
        "min_ram_gb": 32,
        "min_vram_gb": 24,
        "use_case": "MoE powerhouse, multitask expert",
        "quant_size_gb": 24.6,
        "download_url": "https://huggingface.co/TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF/resolve/main/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf",
    },
]


# ────────────────────────────────────────────────────────────────────
# Hardware Detection
# ────────────────────────────────────────────────────────────────────

def get_system_ram_gb() -> float:
    """Return total system RAM in GB using psutil."""
    total_bytes = psutil.virtual_memory().total
    return round(total_bytes / (1024 ** 3), 1)


def get_cpu_info() -> str:
    """Return a human-readable CPU identifier."""
    return platform.processor() or "Unknown CPU"


def get_nvidia_vram_gb() -> tuple[float | None, str | None]:
    """
    Attempt to query NVIDIA GPU VRAM via nvidia-smi.

    Returns:
        (vram_gb, gpu_name)  on success
        (None, None)         if no NVIDIA GPU / driver is found
    """
    try:
        # nvidia-smi ships with every NVIDIA driver install on Windows
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,name",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode != 0:
            return None, None

        # Parse the first GPU line (multi-GPU rigs use the primary)
        line = result.stdout.strip().splitlines()[0]
        vram_str, gpu_name = [s.strip() for s in line.split(",", 1)]
        vram_gb = round(float(vram_str) / 1024, 1)
        return vram_gb, gpu_name

    except FileNotFoundError:
        # nvidia-smi not on PATH → no NVIDIA driver installed
        return None, None
    except subprocess.TimeoutExpired:
        return None, None
    except (IndexError, ValueError, OSError):
        # Catch-all for unexpected parsing issues
        return None, None


# ────────────────────────────────────────────────────────────────────
# Recommendation Engine
# ────────────────────────────────────────────────────────────────────

def classify_models(
    ram_gb: float,
    vram_gb: float | None,
) -> tuple[list[dict], list[dict]]:
    """
    Split the model database into two lists:
      • recommended – models the hardware can handle
      • too_heavy   – models that exceed hardware limits

    Logic:
      - A model is recommended if system RAM ≥ model's min_ram_gb.
      - If the model needs VRAM and the user has enough, it gets a
        GPU-accelerated note; otherwise it still runs on CPU if RAM
        is sufficient.
    """
    recommended: list[dict] = []
    too_heavy: list[dict] = []

    for model in MODEL_DATABASE:
        # Basic RAM gate
        if ram_gb < model["min_ram_gb"]:
            too_heavy.append(model)
            continue

        # Determine acceleration tier
        if vram_gb is not None and model["min_vram_gb"] > 0:
            if vram_gb >= model["min_vram_gb"]:
                model = {**model, "_accel": "GPU -- full VRAM offload [>>]"}
            else:
                model = {**model, "_accel": "CPU + partial GPU offload"}
        elif model["min_vram_gb"] == 0:
            model = {**model, "_accel": "CPU -- lightweight [OK]"}
        else:
            model = {**model, "_accel": "CPU-only (slower, but works)"}

        recommended.append(model)

    return recommended, too_heavy


# ────────────────────────────────────────────────────────────────────
# Display / Rendering
# ────────────────────────────────────────────────────────────────────

def print_banner() -> None:
    """Print the stylized application banner."""
    title_line = "[bold bright_white on blue] ModelMatch LLM [/bold bright_white on blue]  v1.0"
    subtitle = "[italic bright_yellow]Find the best local AI for YOUR hardware[/italic bright_yellow]"
    content = f"{title_line}\n{subtitle}"
    console.print(
        Panel(
            content,
            border_style="bold cyan",
            padding=(1, 4),
        )
    )
    console.print()


def print_hardware_panel(
    cpu: str,
    ram_gb: float,
    vram_gb: float | None,
    gpu_name: str | None,
) -> None:
    """Render a rich Panel summarizing detected hardware."""
    lines: list[str] = []
    lines.append(f"[bold]CPU:[/bold]          {cpu}")
    lines.append(f"[bold]System RAM:[/bold]   {ram_gb} GB")

    if gpu_name and vram_gb is not None:
        lines.append(f"[bold]GPU:[/bold]          {gpu_name}")
        lines.append(f"[bold]GPU VRAM:[/bold]    {vram_gb} GB")
    else:
        lines.append("[bold]GPU:[/bold]          [yellow]No NVIDIA GPU detected[/yellow]")
        lines.append(
            "[dim]-> Recommendations will be based on CPU + System RAM only.[/dim]"
        )

    panel_text = "\n".join(lines)
    console.print(
        Panel(
            panel_text,
            title="[bold bright_white]Hardware Profile[/bold bright_white]",
            border_style="bright_blue",
            padding=(1, 3),
        )
    )
    console.print()


def print_recommended_table(models: list[dict]) -> None:
    """Render the 'Recommended Models' table in green."""
    if not models:
        console.print(
            Panel(
                "[bold yellow]No models in our database match your hardware.\n"
                "Consider upgrading your RAM to at least 4 GB.[/bold yellow]",
                title="Recommended Models",
                border_style="yellow",
            )
        )
        return

    table = Table(
        title="[bold bright_green][+] Recommended Models[/bold bright_green]",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold bright_green",
        show_lines=True,
        padding=(0, 1),
    )
    table.add_column("#", justify="center", width=3)
    table.add_column("Model", ratio=2)
    table.add_column("Params", justify="center", width=12)
    table.add_column("GGUF Size", justify="center", width=10)
    table.add_column("Min RAM", justify="center", width=9)
    table.add_column("Acceleration", ratio=3)
    table.add_column("Best For", ratio=3)

    for i, m in enumerate(models, 1):
        table.add_row(
            str(i),
            f"[bold]{m['name']}[/bold]",
            m["parameters"],
            f"~{m['quant_size_gb']} GB",
            f"{m['min_ram_gb']} GB",
            m.get("_accel", "--"),
            m["use_case"],
        )

    console.print(table)
    console.print()


def print_too_heavy_table(models: list[dict]) -> None:
    """Render the 'Too Heavy' table in red."""
    if not models:
        console.print(
            "[bold bright_green]Your hardware can handle every model "
            "in our database! You're all set.[/bold bright_green]\n"
        )
        return

    table = Table(
        title="[bold bright_red][X] Models Too Heavy for Your PC[/bold bright_red]",
        box=box.ROUNDED,
        border_style="red",
        header_style="bold bright_red",
        show_lines=True,
        padding=(0, 1),
    )
    table.add_column("#", justify="center", width=3)
    table.add_column("Model", ratio=2)
    table.add_column("Params", justify="center", width=12)
    table.add_column("GGUF Size", justify="center", width=10)
    table.add_column("Needs RAM", justify="center", width=10)
    table.add_column("Needs VRAM", justify="center", width=11)
    table.add_column("Best For", ratio=3)

    for i, m in enumerate(models, 1):
        vram_cell = f"{m['min_vram_gb']} GB" if m["min_vram_gb"] > 0 else "--"
        table.add_row(
            str(i),
            f"[dim]{m['name']}[/dim]",
            m["parameters"],
            f"~{m['quant_size_gb']} GB",
            f"[bold red]{m['min_ram_gb']} GB[/bold red]",
            vram_cell,
            m["use_case"],
        )

    console.print(table)
    console.print()


def print_tips(vram_gb: float | None) -> None:
    """Print helpful tips at the bottom of the report."""
    tips: list[str] = [
        "All size estimates assume [bold]Q4_K_M[/bold] quantization (best quality-to-size ratio).",
        "Use [bold cyan]Ollama[/bold cyan], [bold cyan]LM Studio[/bold cyan], or "
        "[bold cyan]GPT4All[/bold cyan] to download & run these models in one click.",
        "Models marked 'CPU-only' will be slower but still fully functional.",
    ]

    if vram_gb is None:
        tips.append(
            "[yellow]Adding an NVIDIA GPU (even a GTX 1660 with 6 GB VRAM) "
            "will dramatically speed up inference.[/yellow]"
        )

    tip_text = "\n".join(f"  * {t}" for t in tips)
    console.print(
        Panel(
            tip_text,
            title="[bold bright_white]Tips[/bold bright_white]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )
    console.print()


def print_footer() -> None:
    """Print timestamp and credits."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"[dim]Report generated on {now} by {APP_NAME} v{APP_VERSION}[/dim]"
    )
    console.print(
        "[dim]Models & requirements sourced from HuggingFace, Ollama, "
        "and community benchmarks.[/dim]"
    )
    console.print()
    console.print(
        Panel(
            "[bold bright_yellow]Want to download one of these models?[/bold bright_yellow]\n"
            "Press [bold bright_green] q [/bold bright_green] on your keyboard to exit this viewer and open the Installation/Download Menu!",
            border_style="bright_green",
            box=box.DOUBLE,
            padding=(1, 2)
        )
    )
    console.print()


# ────────────────────────────────────────────────────────────────────
# Downloader
# ────────────────────────────────────────────────────────────────────

def _get_app_dir() -> str:
    """Return the directory where the script or .exe lives."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle → sys.executable is the .exe path
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def download_model(url: str, dest_filename: str) -> None:
    """Download a model file with a rich progress bar."""
    models_dir = os.path.join(_get_app_dir(), "models")
    os.makedirs(models_dir, exist_ok=True)
    dest_path = os.path.join(models_dir, dest_filename)
    
    if os.path.exists(dest_path):
        console.print(f"\n[yellow]Model already exists at:[/yellow] {dest_path}")
        return

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            total_size_in_bytes = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024  # 1 MB chunk
            
            with Progress(
                TextColumn("[bold bright_cyan]{task.description}"),
                BarColumn(bar_width=40, complete_style="bright_green", finished_style="bold bright_green"),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
                "•",
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(f"Downloading [bold]{dest_filename}[/bold]...", total=total_size_in_bytes)
                with open(dest_path, 'wb') as file:
                    while True:
                        data = response.read(block_size)
                        if not data:
                            break
                        file.write(data)
                        progress.update(task, advance=len(data))
                        
        console.print(f"\n[bold bright_green]Successfully downloaded to:[/bold bright_green] {dest_path}")
    except urllib.error.URLError as e:
        console.print(f"\n[bold red]Network error occurred:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]Failed to download model:[/bold red] {e}")


def interactive_download_prompt(recommended_models: list[dict]) -> None:
    """Prompt the user to select and download a recommended model."""
    if not recommended_models:
        return
        
    console.print()
    console.print(Panel(
        "You can now download one of the recommended models directly.\n"
        "Models will be saved to the [bold cyan]models/[/bold cyan] folder.",
        title="[bold green]Download Manager[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    
    answer = console.input("[bold yellow]Would you like to download a model? (y/n): [/bold yellow]").strip().lower()
    if answer not in ("y", "yes"):
        return
        
    console.print("\n[bold bright_white]Available models to download:[/bold bright_white]")
    for i, m in enumerate(recommended_models, 1):
        console.print(f"  [bright_green][{i}][/bright_green] {m['name']} [dim](~{m['quant_size_gb']} GB)[/dim]")
        
    console.print("  [bright_green][0][/bright_green] Cancel")
    
    while True:
        choice_str = console.input(f"\n[bold yellow]Select a model to download [0-{len(recommended_models)}]: [/bold yellow]").strip()
        if not choice_str.isdigit():
            console.print("[red]Please enter a valid number.[/red]")
            continue
            
        choice = int(choice_str)
        if choice == 0:
            console.print("[yellow]Download aborted.[/yellow]")
            return
        if 1 <= choice <= len(recommended_models):
            selected = recommended_models[choice - 1]
            break
        console.print(f"[red]Please enter a number between 0 and {len(recommended_models)}.[/red]")
        
    # Extract filename from URL or make a safe one
    url = selected["download_url"]
    filename = url.split("/")[-1]
    if not filename.endswith(".gguf"):
        filename = f"{selected['name'].replace(' ', '_')}.gguf"
        
    console.print()
    download_model(url, filename)

# ────────────────────────────────────────────────────────────────────
# Interactive Pager (Windows-friendly, preserves Rich colors)
# ────────────────────────────────────────────────────────────────────

def interactive_pager(content: str) -> None:
    """
    A lightweight scrollable viewer for the Windows console.

    Features:
      • Preserves full ANSI / Rich color output
      • Uses the alternate screen buffer (clean exit)
      • Supports: Arrow Up/Down, Page Up/Down, Home/End, Space, q
      • Works inside Windows Terminal, conhost, and PyInstaller .exe
    """
    try:
        import msvcrt
    except ImportError:
        # Fallback if somehow not on Windows and interactive_pager was called
        sys.stdout.write(content)
        return

    lines = content.splitlines()
    total = len(lines)
    cols, rows = shutil.get_terminal_size()
    view_h = max(1, rows - 1)          # reserve 1 row for the status bar
    max_scroll = max(0, total - view_h)
    pos = 0                             # index of the top visible line

    def _draw() -> None:
        """Redraw the visible slice + status bar in one write."""
        buf: list[str] = ["\033[H"]    # cursor to home (top-left)
        visible = lines[pos : pos + view_h]
        for line in visible:
            buf.append(f"\033[2K{line}\n")      # clear line, print, newline
        # fill any remaining empty rows (e.g. near the end of content)
        for _ in range(view_h - len(visible)):
            buf.append("\033[2K\n")
        # ─ status bar (reverse-video) ─
        if max_scroll == 0:
            pct = "All"
        elif pos == 0:
            pct = "Top"
        elif pos >= max_scroll:
            pct = "End"
        else:
            pct = f"{int(pos / max_scroll * 100)}%"
        bar = f" \u2191\u2193 Scroll  PgUp/PgDn  Space  q=Exit View  [{pct}]"
        buf.append(f"\033[2K\033[7m{bar:<{cols}}\033[0m")
        sys.stdout.write("".join(buf))
        sys.stdout.flush()

    # ── enter alternate screen buffer & hide cursor ─────────────────
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()

    try:
        _draw()
        while True:
            key = msvcrt.getch()
            new_pos = pos

            if key in (b"q", b"Q", b"\x1b"):       # q / Esc
                break
            elif key == b" ":                        # Space  = page down
                new_pos = min(max_scroll, pos + view_h)
            elif key == b"\r":                       # Enter  = one line down
                new_pos = min(max_scroll, pos + 1)
            elif key in (b"\xe0", b"\x00"):          # extended-key prefix
                key2 = msvcrt.getch()
                if key2 == b"H":                     # Up arrow
                    new_pos = max(0, pos - 1)
                elif key2 == b"P":                   # Down arrow
                    new_pos = min(max_scroll, pos + 1)
                elif key2 == b"I":                   # Page Up
                    new_pos = max(0, pos - view_h)
                elif key2 == b"Q":                   # Page Down
                    new_pos = min(max_scroll, pos + view_h)
                elif key2 == b"G":                   # Home
                    new_pos = 0
                elif key2 == b"O":                   # End
                    new_pos = max_scroll

            if new_pos != pos:
                pos = new_pos
                _draw()
    finally:
        # ── restore cursor & exit alternate screen ─────────────────
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


# ────────────────────────────────────────────────────────────────────
# Main Entry Point
# ────────────────────────────────────────────────────────────────────

def run_loading_animation(duration: int = 10) -> None:
    """Display an animated progress bar that runs for `duration` seconds."""
    steps = [
        "Detecting CPU...",
        "Measuring system RAM...",
        "Searching for NVIDIA GPU...",
        "Querying GPU VRAM...",
        "Loading model database...",
        "Comparing hardware specs...",
        "Evaluating quantization requirements...",
        "Ranking compatible models...",
        "Checking acceleration options...",
        "Generating report...",
    ]

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold bright_cyan]{task.description}"),
        BarColumn(bar_width=40, complete_style="bright_green", finished_style="bold bright_green"),
        TextColumn("[bold]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(steps[0], total=100)
        step_duration = duration / len(steps)
        ticks_per_step = 20  # smooth updates within each step
        tick_sleep = step_duration / ticks_per_step
        increment = 100 / (len(steps) * ticks_per_step)

        for step_text in steps:
            progress.update(task, description=step_text)
            for _ in range(ticks_per_step):
                time.sleep(tick_sleep)
                progress.advance(task, increment)

        progress.update(task, description="[bold bright_green]Analysis complete!")

    console.print()


def render_report(
    cpu: str,
    ram_gb: float,
    vram_gb: float | None,
    gpu_name: str | None,
    recommended: list[dict],
    too_heavy: list[dict],
) -> None:
    """
    Capture the full Rich report into a buffer, then display it
    in the custom interactive pager.

    The global ``console`` is temporarily swapped to a buffer-backed
    Console so every existing ``print_*`` helper writes to a string
    instead of stdout.  The pager then renders the string with full
    ANSI color support.
    """
    global console

    # Fallback to Rich's built-in pager on non-Windows platforms
    if os.name != "nt":
        with console.pager(styles=True):
            print_banner()
            print_hardware_panel(cpu, ram_gb, vram_gb, gpu_name)
            print_recommended_table(recommended)
            print_too_heavy_table(too_heavy)
            print_tips(vram_gb)
            print_footer()
        return

    # ── Windows Custom Interactive Pager (preserves colors) ───────

    # Measure the real terminal so Rich wraps tables correctly
    # Subtract 1 from columns to prevent exact-width line auto-wrapping on Windows
    term_cols = shutil.get_terminal_size().columns
    term_width = max(80, term_cols - 1)

    buf = io.StringIO()
    report_console = Console(
        file=buf, force_terminal=True, width=term_width,
    )

    # Swap → capture → restore
    original_console = console
    console = report_console
    try:
        print_banner()
        print_hardware_panel(cpu, ram_gb, vram_gb, gpu_name)
        print_recommended_table(recommended)
        print_too_heavy_table(too_heavy)
        print_tips(vram_gb)
        print_footer()
    finally:
        console = original_console

    interactive_pager(buf.getvalue())


def main() -> None:
    """Run the full hardware scan → recommendation pipeline."""
    # ── Banner ────────────────────────────────────────────────────
    print_banner()

    # ── Ask for Permission ────────────────────────────────────────
    console.print(
        Panel(
            "[bold]ModelMatch LLM[/bold] will scan your hardware to find\n"
            "the best local AI models for your PC.\n\n"
            "Information collected:\n"
            "  [cyan]>[/cyan] CPU type\n"
            "  [cyan]>[/cyan] Total system RAM\n"
            "  [cyan]>[/cyan] NVIDIA GPU name and VRAM (if present)\n\n"
            "[dim]All data stays on your machine. Nothing is sent online.[/dim]",
            title="[bold bright_white]Permission Required[/bold bright_white]",
            border_style="bright_yellow",
            padding=(1, 3),
        )
    )

    answer = console.input(
        "[bold bright_yellow]Proceed with hardware scan? (y/n): [/bold bright_yellow]"
    ).strip().lower()

    if answer not in ("y", "yes", ""):
        console.print("\n[yellow]Scan cancelled. No data was collected.[/yellow]")
        return

    console.print()

    # ── Detect Hardware ─────────────────────────────────────────
    cpu = get_cpu_info()
    ram_gb = get_system_ram_gb()
    vram_gb, gpu_name = get_nvidia_vram_gb()

    print_hardware_panel(cpu, ram_gb, vram_gb, gpu_name)

    # ── Loading Animation (5 seconds) ─────────────────────────────
    run_loading_animation(duration=5)

    # ── Classify Models ───────────────────────────────────────────
    recommended, too_heavy = classify_models(ram_gb, vram_gb)

    # ── Display full report in the interactive pager ───────────────
    # Starts at the top (Hardware Profile), user scrolls down,
    # press 'q' to exit.
    render_report(cpu, ram_gb, vram_gb, gpu_name, recommended, too_heavy)

    # ── Prompt for Downloading ─────────────────────────────────────
    interactive_download_prompt(recommended)


# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Execution cancelled by user.[/yellow]")
    except Exception as exc:
        # Last-resort handler so the .exe never silently closes
        console.print(f"\n[bold red]Unexpected error:[/bold red] {exc}")
    finally:
        # Always wait for input before closing so the final messages are visible
        # especially helpful when compiled as a PyInstaller .exe
        input("\nPress Enter to exit...")
