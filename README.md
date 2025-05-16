### Git Commit Simplifier

A command-line tool that analyzes your Git changes and suggests meaningful commit messages, saving you time and ensuring consistent commit practices.

## Features

- 📊 **Smart Analysis**: Automatically analyzes staged changes in your Git repository
- 🗂️ **File Categorization**: Groups files by type (Python, JavaScript, documentation, etc.)
- 🔍 **Change Detection**: Identifies the nature of changes (new feature, bug fix, refactor)
- ✨ **Multiple Styles**: Supports detailed, conventional, or simple commit message formats
- 😀 **Emoji Support**: Optional emoji prefixes for more expressive commits
- 🔄 **Interactive Mode**: Select files to stage through an interactive interface
- ✏️ **Edit Before Commit**: Review and modify the suggested message
- 🚀 **Auto-Push**: Option to push changes immediately after committing
- ⚙️ **Configurable**: Customize via command-line options or configuration file


## Installation

```shellscript
pip install git-commit-simplifier
```

## Quick Start

Navigate to your Git repository and run:

```shellscript
# Use the short alias 'gcs'
gcs

# Or the full command
git-commit-simplifier
```

That's it! The tool will analyze your staged changes and suggest an appropriate commit message.

## Available Commands

You can use any of these commands - they all do exactly the same thing:

```shellscript
gcs                     # Short alias (recommended)
git_commit_simplifier   # Underscore version
git-commit-simplifier   # Hyphenated version
```

## Usage Examples

```shellscript
# Basic usage
gcs

# Use conventional commit style with emoji
gcs --style conventional --emoji

# Skip preview and use interactive mode for staging
gcs --no-preview --interactive

# Commit and push in one command
gcs --push

# Configure default settings
gcs config --style conventional --emoji --auto-push
```

## Command Options

```plaintext
--path TEXT                     Path to the Git repository (default: current directory)
--preview / --no-preview        Preview changes before committing (default: enabled)
--edit / --no-edit              Edit the commit message before committing (default: enabled)
--push / --no-push              Push changes after committing (default: disabled)
--style [detailed|conventional|simple]
                                Commit message style
--emoji / --no-emoji            Use emoji in commit messages
--interactive / --no-interactive
                                Use interactive mode for staging
--version                       Show the version and exit
--help                          Show this message and exit
```

## Configuration

You can configure default options using the `config` command:

```shellscript
gcs config --style conventional --emoji --auto-push
```

Configuration is stored in `~/.git-commit-simplifier.json` or `.git-commit-simplifier.json` in your repository.

## Commit Message Styles

### Detailed (Default)

```plaintext
Add user authentication

## python
- Add src/auth.py (new file, authentication implementation)
- Update src/app.py (dependency changes, function definition changes)

## configuration
- Add config/auth.yaml (new file)
```

### Conventional

Follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```plaintext
feat(auth): implement user authentication

## python
- Add src/auth.py (new file, authentication implementation)
- Update src/app.py (dependency changes, function definition changes)

## configuration
- Add config/auth.yaml (new file)
```

### Simple

```plaintext
Add user authentication
```

## How It Works

1. Git Commit Simplifier analyzes your staged changes
2. It categorizes files and determines the type of changes
3. Based on this analysis, it generates an appropriate commit message
4. You can review, edit, and confirm the message before committing
5. The tool handles the commit (and optionally push) process


## License

MIT License