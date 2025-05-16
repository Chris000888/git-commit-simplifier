"""Interactive mode for git-commit-simplifier."""

import os
from typing import Dict, List, Optional, Set

import click
from colorama import Fore, Style
from git import Repo
from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style as PromptStyle


def select_files_interactively(repo: Repo, unstaged_changes: List, untracked_files: List) -> Set[str]:
    """Allow the user to select files to stage interactively using prompt_toolkit.
    
    Args:
        repo: Git repository object
        unstaged_changes: List of unstaged changes
        untracked_files: List of untracked files
        
    Returns:
        Set of selected file paths
    """
    if not unstaged_changes and not untracked_files:
        click.echo(f"{Fore.YELLOW}No unstaged changes or untracked files found.{Style.RESET_ALL}")
        return set()
    
    # Prepare the file list
    files = []
    for item in unstaged_changes:
        status = "M" if not (item.new_file or item.deleted_file or item.renamed) else \
                "A" if item.new_file else \
                "D" if item.deleted_file else \
                "R" if item.renamed else "?"
        files.append({
            'path': item.a_path,
            'status': status,
            'type': 'unstaged',
            'selected': False
        })
    
    for file_path in untracked_files:
        files.append({
            'path': file_path,
            'status': '?',
            'type': 'untracked',
            'selected': False
        })
    
    # Initialize the key bindings
    kb = KeyBindings()
    current_index = [0]  # Use list to allow modification in closures
    
    @kb.add('q')
    def _(event):
        "Quit without selecting files."
        event.app.exit()
    
    @kb.add('enter')
    def _(event):
        "Accept the current selection and exit."
        event.app.exit(result=[f for f in files if f['selected']])
    
    @kb.add('space')
    def _(event):
        "Toggle selection for the current file."
        files[current_index[0]]['selected'] = not files[current_index[0]]['selected']
        update_display()
    
    @kb.add('down')
    def _(event):
        "Move cursor down."
        current_index[0] = min(current_index[0] + 1, len(files) - 1)
        update_display()
    
    @kb.add('up')
    def _(event):
        "Move cursor up."
        current_index[0] = max(current_index[0] - 1, 0)
        update_display()
    
    @kb.add('a')
    def _(event):
        "Select all files."
        for file in files:
            file['selected'] = True
        update_display()
    
    @kb.add('n')
    def _(event):
        "Deselect all files."
        for file in files:
            file['selected'] = False
        update_display()
    
    # Style for the UI
    style = PromptStyle.from_dict({
        'unstaged': '#FFFF00',
        'untracked': '#00FF00',
        'selected': '#FFFFFF bold',
        'cursor': 'bg:#666666',
        'status': '#00FFFF',
        'help': '#888888',
        'title': '#FFFFFF bold',
    })
    
    # Create the display
    output = FormattedTextControl('')
    window = Window(content=output)
    help_text = FormattedTextControl([
        ('class:help', 'Use '),
        ('class:help', 'arrow keys'),
        ('class:help', ' to navigate, '),
        ('class:help', 'space'),
        ('class:help', ' to toggle selection, '),
        ('class:help', 'a'),
        ('class:help', ' to select all, '),
        ('class:help', 'n'),
        ('class:help', ' to deselect all, '),
        ('class:help', 'enter'),
        ('class:help', ' to confirm, '),
        ('class:help', 'q'),
        ('class:help', ' to quit')
    ])
    help_window = Window(content=help_text, height=1)
    title = FormattedTextControl([
        ('class:title', 'Select files to stage (use arrow keys to navigate):')
    ])
    title_window = Window(content=title, height=1)
    
    root_container = HSplit([
        title_window,
        window,
        help_window
    ])
    
    # Update the display
    def update_display():
        lines = []
        
        # Add unstaged changes section if there are any
        if any(f['type'] == 'unstaged' for f in files):
            lines.append([('', '\n')])
            lines.append([('class:title', 'Unstaged changes:')])
            lines.append([('', '\n')])
            
            for i, file in enumerate(files):
                if file['type'] == 'unstaged':
                    # Determine style based on selection and cursor position
                    style_class = 'cursor' if i == current_index[0] else 'unstaged'
                    selected_marker = '[X]' if file['selected'] else '[ ]'
                    
                    lines.append([
                        ('class:' + style_class, f"  {i+1}. {selected_marker} "),
                        ('class:status', f"{file['status']}"),
                        ('class:' + style_class, f" {file['path']}")
                    ])
        
        # Add untracked files section if there are any
        if any(f['type'] == 'untracked' for f in files):
            lines.append([('', '\n')])
            lines.append([('class:title', 'Untracked files:')])
            lines.append([('', '\n')])
            
            for i, file in enumerate(files):
                if file['type'] == 'untracked':
                    # Determine style based on selection and cursor position
                    style_class = 'cursor' if i == current_index[0] else 'untracked'
                    selected_marker = '[X]' if file['selected'] else '[ ]'
                    
                    lines.append([
                        ('class:' + style_class, f"  {i+1}. {selected_marker} "),
                        ('class:status', f"{file['status']}"),
                        ('class:' + style_class, f" {file['path']}")
                    ])
        
        output.text = lines
    
    # Initial display update
    update_display()
    
    # Create and run the application
    application = Application(
        layout=Layout(root_container),
        key_bindings=kb,
        style=style,
        full_screen=True
    )
    
    try:
        selected_files = application.run()
        if selected_files is None:
            return set()  # User quit without selecting
        return {f['path'] for f in selected_files}
    except Exception as e:
        click.echo(f"{Fore.RED}Error in interactive mode: {str(e)}{Style.RESET_ALL}")
        # Fallback to non-interactive selection
        if click.confirm(f"{Fore.YELLOW}Would you like to stage all changes instead?{Style.RESET_ALL}"):
            return {f['path'] for f in files}
        return set()


def stage_selected_files(repo: Repo, selected_files: Set[str]) -> None:
    """Stage the selected files.
    
    Args:
        repo: Git repository object
        selected_files: Set of selected file paths
    """
    if not selected_files:
        click.echo(f"{Fore.YELLOW}No files selected for staging.{Style.RESET_ALL}")
        return
    
    for file_path in selected_files:
        try:
            repo.git.add(file_path)
            click.echo(f"{Fore.GREEN}Staged: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            click.echo(f"{Fore.RED}Error staging {file_path}: {str(e)}{Style.RESET_ALL}")
