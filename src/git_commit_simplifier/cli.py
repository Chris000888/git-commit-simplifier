#!/usr/bin/env python3
"""
Main module for Git Commit Simplifier command line interface.
"""

import os
import sys
import json
import click
import gitdb
from typing import Dict, List, Tuple, Optional, Set, Any
from pathlib import Path
import git
from git import Repo, Diff
from colorama import Fore, Style, init
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import checkboxlist_dialog
from prompt_toolkit.formatted_text import HTML

from git_commit_simplifier.config import (
    load_config,
    save_config,
    DEFAULT_CONFIG,
    CONFIG_FILE_NAME,
)

# Initialiser colorama
init(autoreset=True)

def get_repo(path: str = ".") -> Repo:
    """
    Get the Git repository from the specified path.
    """
    try:
        return Repo(path)
    except git.exc.InvalidGitRepositoryError:
        click.echo(f"{Fore.RED}The specified path is not a valid Git repository.{Style.RESET_ALL}")
        sys.exit(1)
    except git.exc.NoSuchPathError:
        click.echo(f"{Fore.RED}The specified path does not exist.{Style.RESET_ALL}")
        sys.exit(1)

def get_staged_files(repo: Repo) -> List[Diff]:
    """
    Get the list of staged files in the repository.
    """
    try:
        staged_diffs = []
        
        # Check if HEAD exists (if at least one commit has been made)
        has_head = True
        try:
            repo.head.commit
        except (ValueError, TypeError, gitdb.exc.BadName):
            has_head = False
        
        if has_head:
            # Get differences between index and HEAD
            diffs = repo.index.diff("HEAD")
            
            # Filter to keep only staged files
            staged_diffs = [d for d in diffs if d.a_path]
        
        # If no files are staged or if HEAD doesn't exist, check new files
        if not staged_diffs:
            # Get untracked files but added to index
            staged_diffs = list(repo.index.diff(None))
            
            # If it's a new repository, add all staged files
            if not has_head and not staged_diffs:
                # For a new repository, all files in the index are considered "staged"
                for entry in repo.index.entries:
                    # Create a simulated diff for each file in the index
                    path = entry[0][0].decode('utf-8') if isinstance(entry[0][0], bytes) else entry[0][0]
                    diff = Diff(repo, 
                                a_path=path,
                                b_path=path,
                                a_blob=None,
                                b_blob=repo.index.entries[entry].to_blob(),
                                new_file=True)
                    staged_diffs.append(diff)
        
        return staged_diffs
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Error while retrieving staged files: {e}{Style.RESET_ALL}")
        return []

def categorize_file(file_path: str, config: Dict[str, Any]) -> str:
    """
    Categorize a file based on its path and extension.
    """
    import re
    
    for category, patterns in config.get("categories", {}).items():
        for pattern in patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return category
    
    # Default category based on extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".py", ".pyw"]:
        return "python"
    elif ext in [".js", ".jsx", ".ts", ".tsx"]:
        return "javascript"
    elif ext in [".html", ".htm", ".css", ".scss", ".sass"]:
        return "frontend"
    elif ext in [".md", ".rst", ".txt"]:
        return "documentation"
    elif ext in [".yml", ".yaml", ".json", ".toml", ".ini", ".cfg"]:
        return "configuration"
    elif ext in [".sql"]:
        return "database"
    elif ext in [".sh", ".bash", ".zsh", ".fish"]:
        return "script"
    elif ext in [".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs"]:
        return "backend"
    elif ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"]:
        return "assets"
    else:
        return "other"

def analyze_diff_content(diff: Diff) -> Tuple[str, List[str]]:
    """
    Analyze the content of a diff to determine the nature of changes.
    """
    try:
        diff_content = diff.diff.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        return 'update', []
    
    details = []
    
    # Count added and removed lines
    added_lines = [line for line in diff_content.split('\n') if line.startswith('+') and not line.startswith('+++')]
    removed_lines = [line for line in diff_content.split('\n') if line.startswith('-') and not line.startswith('---')]
    
    # Detect style changes (spaces, indentation, etc.)
    whitespace_only = True
    if added_lines or removed_lines:
        for line in added_lines + removed_lines:
            # Ignore lines that start with +++ or ---
            if line.startswith('+++') or line.startswith('---'):
                continue
            # Remove + or - at the beginning
            code_line = line[1:] if line else ''
            # Check if the line contains anything other than spaces
            stripped_line = code_line.strip()
            if stripped_line:
                # If the difference between the line with and without spaces is significant,
                # then it's not just a space change
                if len(code_line) - len(stripped_line) < len(code_line) * 0.9:
                    whitespace_only = False
                    break
    
    if whitespace_only and (added_lines or removed_lines):
        return 'style', ['whitespace changes']
    
    # Detect new files
    if diff.new_file:
        details.append("new file")
        return 'feat', details
    
    # Detect deleted files
    if diff.deleted_file:
        details.append("file deletion")
        return 'chore', details
    
    # Detect renamed files
    if diff.renamed:
        details.append("file rename")
        return 'refactor', details
    
    # Analyze content to determine change type
    if "fix" in diff_content.lower() or "bug" in diff_content.lower() or "issue" in diff_content.lower():
        details.append("bug fix")
        return 'fix', details
    
    if "test" in diff_content.lower() or "assert" in diff_content.lower():
        details.append("test changes")
        return 'test', details
    
    if "refactor" in diff_content.lower() or "clean" in diff_content.lower():
        details.append("code refactoring")
        return 'refactor', details
    
    if "doc" in diff_content.lower() or "comment" in diff_content.lower():
        details.append("documentation changes")
        return 'docs', details
    
    # Detect dependency changes
    if "import" in diff_content.lower() or "require" in diff_content.lower() or "dependency" in diff_content.lower():
        details.append("dependency changes")
        if "add" in diff_content.lower() or any(line.startswith('+') for line in diff_content.split('\n') if "import" in line.lower() or "require" in line.lower()):
            return 'feat', details
        else:
            return 'chore', details
    
    # Detect function changes
    if "def " in diff_content.lower() or "function" in diff_content.lower() or "class" in diff_content.lower():
        details.append("function definition changes")
        if any(line.startswith('+') for line in diff_content.split('\n') if "def " in line.lower() or "function" in line.lower() or "class" in line.lower()):
            return 'feat', details
        else:
            return 'refactor', details
    
    # Default, consider as an update
    details.append("code changes")
    return 'chore', details

def generate_commit_message(
    staged_files: List[Tuple[str, str, str, List[str]]],
    style: str = "detailed",
    use_emoji: bool = False
) -> str:
    """
    Generate a commit message based on staged files.
    """
    if not staged_files:
        return "No changes to commit"
    
    # Group files by category
    files_by_category: Dict[str, List[Tuple[str, str, List[str]]]] = {}
    for file_path, category, change_type, details in staged_files:
        if category not in files_by_category:
            files_by_category[category] = []
        files_by_category[category].append((file_path, change_type, details))
    
    # Determine primary change type
    change_types = [change_type for _, _, change_type, _ in staged_files]
    primary_change_type = max(set(change_types), key=change_types.count)
    
    # Determine primary category
    categories = [category for _, category, _, _ in staged_files]
    primary_category = max(set(categories), key=categories.count)
    
    # Generate summary of changes
    summary = generate_summary(staged_files)
    
    # Add emoji if requested
    emoji_prefix = ""
    if use_emoji:
        emoji_map = {
            'feat': '✨',
            'fix': '🐛',
            'docs': '📚',
            'style': '💄',
            'refactor': '♻️',
            'test': '✅',
            'chore': '🔧',
        }
        emoji_prefix = f"{emoji_map.get(primary_change_type, '🔧')} "
    
    # Generate message based on requested style
    if style == "conventional":
        # Format: type(scope): description
        message = f"{primary_change_type}({primary_category}): {emoji_prefix}{summary}\n\n"
    elif style == "simple":
        # Format: Simple description
        message = f"{emoji_prefix}{summary}"
    else:  # detailed (default)
        # Format: Description with details
        message = f"{emoji_prefix}{summary}\n\n"
    
    # Add details for detailed and conventional styles
    if style != "simple":
        for category, files in files_by_category.items():
            message += f"## {category}\n"
            for file_path, change_type, details in files:
                # Translate change type to English
                change_type_map = {
                    'feat': 'Add',
                    'fix': 'Fix',
                    'docs': 'Update',
                    'style': 'Improve',
                    'refactor': 'Refactor',
                    'test': 'Test',
                    'chore': 'Update'
                }
                change_verb = change_type_map.get(change_type, 'Update')
                
                detail_str = f"({', '.join(details)})" if details else ""
                message += f"- {change_verb} {file_path} {detail_str}\n"
            message += "\n"
    
    return message.strip()

def generate_summary(staged_files: List[Tuple[str, str, str, List[str]]]) -> str:
    """
    Generate a summary of changes for the commit message.
    """
    # Extract change types and categories
    change_types = [change_type for _, _, change_type, _ in staged_files]
    categories = [category for _, category, _, _ in staged_files]
    
    # Determine primary change type and primary category
    primary_change_type = max(set(change_types), key=change_types.count)
    primary_category = max(set(categories), key=categories.count)
    
    # Generate summary based on primary change type (in English)
    if primary_change_type == 'feat':
        action = "Add"
    elif primary_change_type == 'fix':
        action = "Fix"
    elif primary_change_type == 'docs':
        action = "Update documentation for"
    elif primary_change_type == 'style':
        action = "Improve style in"
    elif primary_change_type == 'refactor':
        action = "Refactor"
    elif primary_change_type == 'test':
        action = "Add tests for"
    else:  # chore or other
        action = "Update"
    
    # Generate summary based on primary category (in English)
    if primary_category == 'python':
        component = "Python code"
    elif primary_category == 'javascript':
        component = "JavaScript code"
    elif primary_category == 'frontend':
        component = "frontend components"
    elif primary_category == 'documentation':
        component = "documentation"
    elif primary_category == 'configuration':
        component = "configuration"
    elif primary_category == 'database':
        component = "database"
    elif primary_category == 'script':
        component = "scripts"
    elif primary_category == 'backend':
        component = "backend code"
    elif primary_category == 'assets':
        component = "assets"
    else:
        component = "files"
    
    # If all files are in the same directory, use that directory as component
    file_paths = [file_path for file_path, _, _, _ in staged_files]
    common_dir = os.path.commonpath(file_paths) if len(file_paths) > 1 else os.path.dirname(file_paths[0])
    if common_dir and common_dir != "." and common_dir != "":
        component = common_dir
    
    # If it's a style change for spaces, be more specific (in English)
    if primary_change_type == 'style':
        details = [detail for _, _, _, file_details in staged_files for detail in file_details]
        if 'whitespace changes' in details:
            return f"Remove whitespace in {component}"
    
    return f"{action} {component}"

def preview_changes(repo: Repo) -> None:
    """
    Display a preview of staged changes.
    """
    try:
        # Use git diff --cached to see staged changes
        diff = repo.git.diff("--cached", color="always")
        if diff:
            click.echo(f"\n{Fore.CYAN}Preview of staged changes:{Style.RESET_ALL}")
            click.echo(diff)
        else:
            click.echo(f"\n{Fore.YELLOW}No staged changes.{Style.RESET_ALL}")
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Error while previewing changes: {e}{Style.RESET_ALL}")

def interactive_staging(repo: Repo) -> None:
    """
    Interactive mode for selecting files to stage.
    """
    try:
        # Get list of modified but not yet staged files
        unstaged_files = [
            item.a_path
            for item in repo.index.diff(None)
        ]
        
        # Add untracked files
        untracked_files = repo.untracked_files
        all_files = unstaged_files + untracked_files
        
        if not all_files:
            click.echo(f"{Fore.YELLOW}No files to stage.{Style.RESET_ALL}")
            return
        
        # Display a dialog to select files
        result = checkboxlist_dialog(
            title="Select files to stage",
            text="Use spacebar to select/deselect files",
            values=[(file, file) for file in all_files]
        ).run()
        
        if result:
            # Stage selected files
            repo.git.add(*result)
            click.echo(f"{Fore.GREEN}Files added to staging: {', '.join(result)}{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}No files selected.{Style.RESET_ALL}")
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Error during interactive staging: {e}{Style.RESET_ALL}")

def commit_changes(repo: Repo, message: str, edit: bool = True) -> bool:
    """
    Commit changes with the specified message.
    """
    try:
        if edit:
            # Write message to temporary file
            temp_file = os.path.join(repo.git_dir, "COMMIT_EDITMSG")
            with open(temp_file, "w") as f:
                f.write(message)
            
            # Open editor to modify message
            click.echo(f"{Fore.CYAN}Opening editor to modify commit message...{Style.RESET_ALL}")
            editor = os.environ.get("EDITOR", "vim")
            os.system(f"{editor} {temp_file}")
            
            # Read modified message
            with open(temp_file, "r") as f:
                edited_message = f.read()
            
            # Check if message was modified
            if edited_message.strip() == "":
                click.echo(f"{Fore.YELLOW}Commit cancelled: empty message.{Style.RESET_ALL}")
                return False
            
            # Commit with modified message
            repo.git.commit("-m", edited_message)
        else:
            # Commit directly with generated message
            repo.git.commit("-m", message)
        
        click.echo(f"{Fore.GREEN}Changes committed successfully!{Style.RESET_ALL}")
        return True
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Error during commit: {e}{Style.RESET_ALL}")
        return False

def push_changes(repo: Repo) -> bool:
    """
    Push changes to remote repository.
    """
    try:
        # Check if remote repository is configured
        if not repo.remotes:
            click.echo(f"{Fore.YELLOW}No remote repository configured.{Style.RESET_ALL}")
            return False
        
        # Push changes
        remote = repo.remotes[0]
        remote.push()
        
        click.echo(f"{Fore.GREEN}Changes pushed successfully to {remote.name}!{Style.RESET_ALL}")
        return True
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Error during push: {e}{Style.RESET_ALL}")
        return False

@click.group(invoke_without_command=True)
@click.option("--path", default=".", help="Path to Git repository")
@click.option("--preview/--no-preview", default=True, help="Preview changes before committing")
@click.option("--edit/--no-edit", default=True, help="Edit commit message before committing")
@click.option("--push/--no-push", default=False, help="Push changes after commit")
@click.option("--style", type=click.Choice(["detailed", "conventional", "simple"]), default="detailed", help="Commit message style")
@click.option("--emoji/--no-emoji", default=False, help="Use emoji in commit messages")
@click.option("--interactive/--no-interactive", default=False, help="Use interactive mode for staging")
@click.version_option()
@click.pass_context
def main(ctx, path, preview, edit, push, style, emoji, interactive):
    """
    Git Commit Simplifier - A tool to simplify Git commit message creation.
    """
    if ctx.invoked_subcommand is None:
        # Load configuration
        config = load_config()
        
        # Command line options take precedence over configuration
        style = style or config.get("style", "detailed")
        emoji = emoji if emoji is not None else config.get("emoji", False)
        push = push if push is not None else config.get("auto_push", False)
        
        # Get Git repository
        repo = get_repo(path)
        
        # Interactive staging mode if requested
        if interactive:
            interactive_staging(repo)
        
        # Get staged files
        staged_diffs = get_staged_files(repo)
        
        if not staged_diffs:
            click.echo(f"{Fore.YELLOW}No staged changes. Use 'git add' to add files.{Style.RESET_ALL}")
            return
        
        # Analyze staged files
        staged_files = []
        for diff in staged_diffs:
            file_path = diff.a_path or diff.b_path
            category = categorize_file(file_path, config)
            change_type, details = analyze_diff_content(diff)
            staged_files.append((file_path, category, change_type, details))
        
        # Preview changes if requested
        if preview:
            preview_changes(repo)
        
        # Generate commit message
        commit_message = generate_commit_message(staged_files, style, emoji)
        
        # Display generated commit message
        click.echo(f"\n{Fore.CYAN}Generated commit message:{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{commit_message}{Style.RESET_ALL}")
        
        # Ask for confirmation
        if click.confirm(f"\n{Fore.CYAN}Do you want to commit these changes?{Style.RESET_ALL}", default=True):
            # Commit changes
            if commit_changes(repo, commit_message, edit):
                # Push changes if requested
                if push:
                    push_changes(repo)

@main.command()
@click.option("--style", type=click.Choice(["detailed", "conventional", "simple"]), help="Commit message style")
@click.option("--emoji/--no-emoji", help="Use emoji in commit messages")
@click.option("--auto-push/--no-auto-push", help="Automatically push changes after commit")
def config(style, emoji, auto_push):
    """
    Configure Git Commit Simplifier.
    """
    # Load existing configuration
    config = load_config()
    
    # Update configuration with new values
    if style is not None:
        config["style"] = style
    if emoji is not None:
        config["emoji"] = emoji
    if auto_push is not None:
        config["auto_push"] = auto_push
    
    # Save configuration
    save_config(config)
    
    # Display current configuration
    click.echo(f"{Fore.GREEN}Configuration saved:{Style.RESET_ALL}")
    click.echo(json.dumps(config, indent=2))

if __name__ == "__main__":
    main()
