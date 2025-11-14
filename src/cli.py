#!/usr/bin/env python3
"""
Aesthetic CLI wrapper for the Intelligent Web Automation System.

Provides a beautiful, interactive command-line interface similar to Claude Code CLI.
"""

import sys
import re
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.align import Align
from rich import box
from rich.markdown import Markdown

from src.orchestrator import run_iterative

# Initialize console
console = Console()


def print_banner():
    """Print the welcome banner."""
    banner = Text()
    banner.append("🤖 ", style="bold cyan")
    banner.append("Intelligent Web Automation System", style="bold white")
    banner.append("\n", style="reset")
    banner.append("   Two-Agent Architecture for Smart Browser Automation", style="dim white")
    
    console.print("\n")
    console.print(Align.center(banner), style="bold")
    console.print("\n")


def get_task_input() -> str:
    """Get task input from user in a nice box."""
    console.print("\n")
    
    # Create a nice input box
    prompt_text = Text()
    prompt_text.append("📝 ", style="bold cyan")
    prompt_text.append("Enter your task:", style="bold white")
    
    console.print(Panel(
        prompt_text,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    
    console.print("\n")
    
    # Show examples
    examples = [
        "Create a new issue in Linear called 'Test Issue' and save it",
        "Navigate to https://linear.app and create a new project",
        "Fill out the contact form on example.com with your details",
    ]
    
    console.print("[bold cyan]💡 Examples:[/bold cyan]")
    for i, example in enumerate(examples, 1):
        console.print(f"  [dim]{i}. {example}[/dim]")
    
    console.print("\n")
    console.print("[dim]────────────────────────────────────────────────────────────[/dim]")
    console.print("[dim]Enter your task below (press Enter twice or Ctrl+D when done):[/dim]\n")
    
    # Get multi-line input
    task_lines = []
    try:
        while True:
            try:
                line = input()
                if not line.strip() and task_lines:
                    # Empty line after content means done
                    break
                if line.strip():
                    task_lines.append(line)
            except EOFError:
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Input cancelled[/yellow]\n")
        sys.exit(0)
    
    task = "\n".join(task_lines).strip()
    
    if not task:
        console.print("\n[red]❌ No task provided. Exiting.[/red]\n")
        sys.exit(1)
    
    return task


def display_task_summary(task: str):
    """Display the task in a nice summary box."""
    console.print("\n")
    
    summary = Panel(
        Text(task, style="white"),
        title="[bold cyan]📋 Task[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(summary)
    console.print("\n")


def create_progress_display() -> tuple[Live, Progress]:
    """Create a live progress display."""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )
    
    layout = Layout()
    layout.split_column(
        Layout(name="main", size=3),
        Layout(name="progress"),
    )
    
    live = Live(layout, console=console, refresh_per_second=10)
    return live, progress


def display_step_info(step_num: int, action_type: str, target: str, reasoning: Optional[str] = None):
    """Display step information in a nice format."""
    console.print("\n")
    
    # Create step header
    step_header = Text()
    step_header.append(f"Step {step_num}", style="bold yellow")
    step_header.append(" • ", style="dim")
    step_header.append(action_type.upper(), style="bold cyan")
    
    step_panel = Panel(
        step_header,
        border_style="yellow",
        box=box.ROUNDED,
    )
    console.print(step_panel)
    
    # Display target
    console.print(f"  [cyan]→[/cyan] [white]{target}[/white]")
    
    # Display reasoning if available
    if reasoning:
        console.print(f"  [dim]💭 {reasoning}[/dim]")
    
    console.print()


def display_agent_status(agent: str, status: str, message: str):
    """Display agent status updates."""
    icons = {
        "thinking": "🤔",
        "executing": "🚀",
        "success": "✅",
        "error": "❌",
        "analyzing": "🔍",
    }
    
    icon = icons.get(status, "⚙️")
    colors = {
        "thinking": "yellow",
        "executing": "cyan",
        "success": "green",
        "error": "red",
        "analyzing": "blue",
    }
    
    color = colors.get(status, "white")
    
    status_text = Text()
    status_text.append(f"{icon} ", style=f"bold {color}")
    status_text.append(f"Agent {agent}: ", style=f"bold {color}")
    status_text.append(message, style="white")
    
    console.print(f"  {status_text}")


def display_results_summary(results: list):
    """Display execution results summary."""
    console.print("\n")
    
    # Create results table
    table = Table(title="[bold cyan]📊 Execution Summary[/bold cyan]", box=box.ROUNDED, border_style="cyan")
    table.add_column("Step", style="yellow", justify="right")
    table.add_column("Action", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    
    success_count = 0
    error_count = 0
    
    for result in results:
        step = result.get("step_index", 0)
        action_type = result.get("action_type", "unknown").upper()
        status = result.get("result", {}).get("status", "unknown")
        error_msg = result.get("result", {}).get("error_message")
        
        if status == "success":
            status_display = "[green]✓[/green]"
            success_count += 1
        elif status == "error":
            status_display = "[red]✗[/red]"
            error_count += 1
        else:
            status_display = f"[yellow]{status}[/yellow]"
        
        details = error_msg[:50] + "..." if error_msg and len(error_msg) > 50 else (error_msg or "")
        
        table.add_row(
            str(step),
            action_type,
            status_display,
            details,
        )
    
    console.print(table)
    
    # Summary stats
    console.print("\n")
    stats_panel = Panel(
        f"[green]✓ Success: {success_count}[/green]  [red]✗ Errors: {error_count}[/red]  [white]Total: {len(results)}[/white]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(stats_panel)
    console.print("\n")


def format_orchestrator_output(text: str) -> Text:
    """Format orchestrator output with rich formatting."""
    lines = text.split('\n')
    formatted = Text()
    
    for line in lines:
        if not line.strip():
            formatted.append('\n')
            continue
            
        # Format step headers
        if re.match(r'^--- Step \d+ ---$', line):
            step_num = re.search(r'\d+', line).group()
            formatted.append(f"\n[bold yellow]━━━ Step {step_num} ━━━[/bold yellow]\n")
        
        # Format agent B messages
        elif 'Agent B:' in line:
            if '🤔' in line or 'Analyzing' in line:
                formatted.append("  [yellow]🤔 Agent B:[/yellow] ", style="")
                formatted.append(line.split('Agent B:')[1].strip(), style="dim white")
                formatted.append("\n")
            elif '✅' in line or 'decided' in line:
                action_match = re.search(r'decided: (\w+) - (.+)', line)
                if action_match:
                    action_type = action_match.group(1)
                    target = action_match.group(2)
                    formatted.append("  [green]✅ Agent B decided:[/green] ", style="")
                    formatted.append(f"[cyan]{action_type}[/cyan] - [white]{target}[/white]\n")
                else:
                    formatted.append(f"  [green]{line}[/green]\n")
            elif '🔍' in line or 'Evaluating' in line:
                formatted.append("  [blue]🔍 Agent B:[/blue] ", style="")
                formatted.append(line.split('Agent B:')[1].strip(), style="dim white")
                formatted.append("\n")
            else:
                formatted.append(f"  {line}\n")
        
        # Format agent A messages
        elif 'Agent A:' in line or '🚀' in line:
            if '🚀' in line:
                formatted.append("  [cyan]🚀 Agent A:[/cyan] ", style="")
                formatted.append(line.split('Agent A:')[1].strip() if 'Agent A:' in line else line.split('🚀')[1].strip(), style="white")
                formatted.append("\n")
            else:
                formatted.append(f"  {line}\n")
        
        # Format status messages
        elif 'Status:' in line:
            status = line.split('Status:')[1].strip()
            if status == 'success':
                formatted.append(f"  [green]✓ Status: {status}[/green]\n")
            elif status == 'error':
                formatted.append(f"  [red]✗ Status: {status}[/red]\n")
            else:
                formatted.append(f"  [yellow]Status: {status}[/yellow]\n")
        
        # Format reasoning
        elif line.strip().startswith('Reasoning:'):
            reasoning = line.split('Reasoning:')[1].strip()
            formatted.append(f"  [dim]💭 Reasoning: {reasoning}[/dim]\n")
        
        # Format screenshots
        elif '📸' in line or 'Screenshot' in line:
            formatted.append(f"  [blue]📸 {line.split('📸')[1].strip() if '📸' in line else line}[/blue]\n")
        
        # Format errors
        elif '❌' in line or 'Error:' in line:
            formatted.append(f"  [red]{line}[/red]\n")
        
        # Format section headers
        elif '=' * 70 in line:
            if 'Starting' in text or '🎯' in text:
                formatted.append("[bold cyan]" + "═" * 70 + "[/bold cyan]\n")
            elif 'completed' in line.lower() or '✅' in line:
                formatted.append("[bold green]" + "═" * 70 + "[/bold green]\n")
            else:
                formatted.append("[dim]" + "─" * 70 + "[/dim]\n")
        
        # Format task header
        elif '🎯 Starting iterative execution:' in line:
            task_name = line.split('🎯 Starting iterative execution:')[1].strip()
            formatted.append(f"\n[bold cyan]🎯 Starting execution:[/bold cyan] [white]{task_name}[/white]\n")
        
        # Format completion message
        elif 'Iterative execution completed' in line:
            step_match = re.search(r'after (\d+) steps', line)
            if step_match:
                steps = step_match.group(1)
                formatted.append(f"\n[bold green]✅ Execution completed after {steps} steps[/bold green]\n")
        
        # Default formatting
        else:
            formatted.append(f"  {line}\n")
    
    return formatted


def run_cli():
    """Main CLI entry point."""
    try:
        # Print banner
        print_banner()
        
        # Get task input
        task = get_task_input()
        
        # Display task summary
        display_task_summary(task)
        
        # Confirm execution
        console.print("[dim]Press Enter to start execution, or Ctrl+C to cancel...[/dim]")
        try:
            input()
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Cancelled by user[/yellow]\n")
            sys.exit(0)
        
        console.print("\n")
        console.print(Panel(
            "[bold cyan]🚀 Starting execution...[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        ))
        console.print("\n")
        
        # Run the orchestrator - output will be displayed in real-time
        # The orchestrator's print statements will show directly
        results = run_iterative(
            task=task,
            use_real_browser=True,
            browser_type="brave",
            max_steps=50,
        )
        
        # Display results summary in a nice format
        if results:
            console.print("\n")
            display_results_summary(results)
        
        # Final success message
        console.print("\n")
        console.print(Panel(
            "[bold green]✅ Task execution completed successfully![/bold green]",
            border_style="green",
            box=box.ROUNDED,
        ))
        console.print("\n")
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠️  Interrupted by user[/yellow]\n")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        import traceback
        console.print("[dim]")
        traceback.print_exc()
        console.print("[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    run_cli()

