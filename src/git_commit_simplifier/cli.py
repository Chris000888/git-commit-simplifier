#!/usr/bin/env python3
"""
Module principal pour l'interface en ligne de commande de Git Commit Simplifier.
"""

import os
import sys
import json
import click
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
    Obtient le dépôt Git à partir du chemin spécifié.
    """
    try:
        return Repo(path)
    except git.exc.InvalidGitRepositoryError:
        click.echo(f"{Fore.RED}Le chemin spécifié n'est pas un dépôt Git valide.{Style.RESET_ALL}")
        sys.exit(1)
    except git.exc.NoSuchPathError:
        click.echo(f"{Fore.RED}Le chemin spécifié n'existe pas.{Style.RESET_ALL}")
        sys.exit(1)

def get_staged_files(repo: Repo) -> List[Diff]:
    """
    Obtient la liste des fichiers en staging dans le dépôt.
    """
    try:
        staged_diffs = []
        
        # Vérifier si HEAD existe (si au moins un commit a été effectué)
        has_head = True
        try:
            repo.head.commit
        except (ValueError, TypeError, gitdb.exc.BadName):
            has_head = False
        
        if has_head:
            # Obtenir les différences entre l'index et HEAD
            diffs = repo.index.diff("HEAD")
            
            # Filtrer pour ne garder que les fichiers en staging
            staged_diffs = [d for d in diffs if d.a_path]
        
        # Si aucun fichier n'est en staging ou si HEAD n'existe pas, vérifier les nouveaux fichiers
        if not staged_diffs:
            # Obtenir les fichiers non suivis mais ajoutés à l'index
            staged_diffs = list(repo.index.diff(None))
            
            # Si c'est un nouveau dépôt, ajouter tous les fichiers en staging
            if not has_head and not staged_diffs:
                # Pour un nouveau dépôt, tous les fichiers dans l'index sont considérés comme "staged"
                for entry in repo.index.entries:
                    # Créer un diff simulé pour chaque fichier dans l'index
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
        click.echo(f"{Fore.RED}Erreur lors de la récupération des fichiers en staging: {e}{Style.RESET_ALL}")
        return []

def categorize_file(file_path: str, config: Dict[str, Any]) -> str:
    """
    Catégorise un fichier en fonction de son chemin et de son extension.
    """
    import re
    
    for category, patterns in config.get("categories", {}).items():
        for pattern in patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return category
    
    # Catégorie par défaut basée sur l'extension
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
    Analyse le contenu d'un diff pour déterminer la nature des changements.
    """
    try:
        diff_content = diff.diff.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        return 'update', []
    
    details = []
    
    # Compter les lignes ajoutées et supprimées
    added_lines = [line for line in diff_content.split('\n') if line.startswith('+') and not line.startswith('+++')]
    removed_lines = [line for line in diff_content.split('\n') if line.startswith('-') and not line.startswith('---')]
    
    # Détecter les changements de style (espaces, indentation, etc.)
    whitespace_only = True
    if added_lines or removed_lines:
        for line in added_lines + removed_lines:
            # Ignorer les lignes qui commencent par +++ ou ---
            if line.startswith('+++') or line.startswith('---'):
                continue
            # Enlever le + ou - au début
            code_line = line[1:] if line else ''
            # Vérifier si la ligne contient autre chose que des espaces
            stripped_line = code_line.strip()
            if stripped_line:
                # Si la différence entre la ligne avec et sans espaces est significative,
                # alors ce n'est pas seulement un changement d'espaces
                if len(code_line) - len(stripped_line) < len(code_line) * 0.9:
                    whitespace_only = False
                    break
    
    if whitespace_only and (added_lines or removed_lines):
        return 'style', ['whitespace changes']
    
    # Détecter les nouveaux fichiers
    if diff.new_file:
        details.append("new file")
        return 'feat', details
    
    # Détecter les fichiers supprimés
    if diff.deleted_file:
        details.append("file deletion")
        return 'chore', details
    
    # Détecter les changements de nom
    if diff.renamed:
        details.append("file rename")
        return 'refactor', details
    
    # Analyser le contenu pour déterminer le type de changement
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
    
    # Détecter les changements de dépendances
    if "import" in diff_content.lower() or "require" in diff_content.lower() or "dependency" in diff_content.lower():
        details.append("dependency changes")
        if "add" in diff_content.lower() or any(line.startswith('+') for line in diff_content.split('\n') if "import" in line.lower() or "require" in line.lower()):
            return 'feat', details
        else:
            return 'chore', details
    
    # Détecter les changements de fonction
    if "def " in diff_content.lower() or "function" in diff_content.lower() or "class" in diff_content.lower():
        details.append("function definition changes")
        if any(line.startswith('+') for line in diff_content.split('\n') if "def " in line.lower() or "function" in line.lower() or "class" in line.lower()):
            return 'feat', details
        else:
            return 'refactor', details
    
    # Par défaut, considérer comme une mise à jour
    details.append("code changes")
    return 'chore', details

def generate_commit_message(
    staged_files: List[Tuple[str, str, str, List[str]]],
    style: str = "detailed",
    use_emoji: bool = False
) -> str:
    """
    Génère un message de commit en fonction des fichiers en staging.
    """
    if not staged_files:
        return "No changes to commit"
    
    # Regrouper les fichiers par catégorie
    files_by_category: Dict[str, List[Tuple[str, str, List[str]]]] = {}
    for file_path, category, change_type, details in staged_files:
        if category not in files_by_category:
            files_by_category[category] = []
        files_by_category[category].append((file_path, change_type, details))
    
    # Déterminer le type de changement principal
    change_types = [change_type for _, _, change_type, _ in staged_files]
    primary_change_type = max(set(change_types), key=change_types.count)
    
    # Déterminer la catégorie principale
    categories = [category for _, category, _, _ in staged_files]
    primary_category = max(set(categories), key=categories.count)
    
    # Générer un résumé des changements
    summary = generate_summary(staged_files)
    
    # Ajouter un emoji si demandé
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
    
    # Générer le message selon le style demandé
    if style == "conventional":
        # Format: type(scope): description
        message = f"{primary_change_type}({primary_category}): {emoji_prefix}{summary}\n\n"
    elif style == "simple":
        # Format: Simple description
        message = f"{emoji_prefix}{summary}"
    else:  # detailed (default)
        # Format: Description with details
        message = f"{emoji_prefix}{summary}\n\n"
    
    # Ajouter les détails pour le style détaillé et conventionnel
    if style != "simple":
        for category, files in files_by_category.items():
            message += f"## {category}\n"
            for file_path, change_type, details in files:
                # Traduire le type de changement en anglais
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
    Génère un résumé des changements pour le message de commit.
    """
    # Extraire les types de changements et les catégories
    change_types = [change_type for _, _, change_type, _ in staged_files]
    categories = [category for _, category, _, _ in staged_files]
    
    # Déterminer le type de changement principal et la catégorie principale
    primary_change_type = max(set(change_types), key=change_types.count)
    primary_category = max(set(categories), key=categories.count)
    
    # Générer un résumé en fonction du type de changement principal (en anglais)
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
    
    # Générer un résumé en fonction de la catégorie principale (en anglais)
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
    
    # Si tous les fichiers sont dans le même répertoire, utiliser ce répertoire comme composant
    file_paths = [file_path for file_path, _, _, _ in staged_files]
    common_dir = os.path.commonpath(file_paths) if len(file_paths) > 1 else os.path.dirname(file_paths[0])
    if common_dir and common_dir != "." and common_dir != "":
        component = common_dir
    
    # Si c'est un changement de style pour des espaces, être plus spécifique (en anglais)
    if primary_change_type == 'style':
        details = [detail for _, _, _, file_details in staged_files for detail in file_details]
        if 'whitespace changes' in details:
            return f"Remove whitespace in {component}"
    
    return f"{action} {component}"

def preview_changes(repo: Repo) -> None:
    """
    Affiche un aperçu des changements en staging.
    """
    try:
        # Utiliser git diff --cached pour voir les changements en staging
        diff = repo.git.diff("--cached", color="always")
        if diff:
            click.echo(f"\n{Fore.CYAN}Aperçu des changements en staging:{Style.RESET_ALL}")
            click.echo(diff)
        else:
            click.echo(f"\n{Fore.YELLOW}Aucun changement en staging.{Style.RESET_ALL}")
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Erreur lors de l'aperçu des changements: {e}{Style.RESET_ALL}")

def interactive_staging(repo: Repo) -> None:
    """
    Mode interactif pour sélectionner les fichiers à mettre en staging.
    """
    try:
        # Obtenir la liste des fichiers modifiés mais pas encore en staging
        unstaged_files = [
            item.a_path
            for item in repo.index.diff(None)
        ]
        
        # Ajouter les fichiers non suivis
        untracked_files = repo.untracked_files
        all_files = unstaged_files + untracked_files
        
        if not all_files:
            click.echo(f"{Fore.YELLOW}Aucun fichier à mettre en staging.{Style.RESET_ALL}")
            return
        
        # Afficher un dialogue pour sélectionner les fichiers
        result = checkboxlist_dialog(
            title="Sélectionnez les fichiers à mettre en staging",
            text="Utilisez la barre d'espace pour sélectionner/désélectionner les fichiers",
            values=[(file, file) for file in all_files]
        ).run()
        
        if result:
            # Mettre en staging les fichiers sélectionnés
            repo.git.add(*result)
            click.echo(f"{Fore.GREEN}Fichiers ajoutés au staging: {', '.join(result)}{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}Aucun fichier sélectionné.{Style.RESET_ALL}")
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Erreur lors du staging interactif: {e}{Style.RESET_ALL}")

def commit_changes(repo: Repo, message: str, edit: bool = True) -> bool:
    """
    Commit les changements avec le message spécifié.
    """
    try:
        if edit:
            # Écrire le message dans un fichier temporaire
            temp_file = os.path.join(repo.git_dir, "COMMIT_EDITMSG")
            with open(temp_file, "w") as f:
                f.write(message)
            
            # Ouvrir l'éditeur pour modifier le message
            click.echo(f"{Fore.CYAN}Ouverture de l'éditeur pour modifier le message de commit...{Style.RESET_ALL}")
            editor = os.environ.get("EDITOR", "vim")
            os.system(f"{editor} {temp_file}")
            
            # Lire le message modifié
            with open(temp_file, "r") as f:
                edited_message = f.read()
            
            # Vérifier si le message a été modifié
            if edited_message.strip() == "":
                click.echo(f"{Fore.YELLOW}Commit annulé: message vide.{Style.RESET_ALL}")
                return False
            
            # Commit avec le message modifié
            repo.git.commit("-m", edited_message)
        else:
            # Commit directement avec le message généré
            repo.git.commit("-m", message)
        
        click.echo(f"{Fore.GREEN}Changements commités avec succès!{Style.RESET_ALL}")
        return True
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Erreur lors du commit: {e}{Style.RESET_ALL}")
        return False

def push_changes(repo: Repo) -> bool:
    """
    Pousse les changements vers le dépôt distant.
    """
    try:
        # Vérifier s'il y a un dépôt distant configuré
        if not repo.remotes:
            click.echo(f"{Fore.YELLOW}Aucun dépôt distant configuré.{Style.RESET_ALL}")
            return False
        
        # Pousser les changements
        remote = repo.remotes[0]
        remote.push()
        
        click.echo(f"{Fore.GREEN}Changements poussés avec succès vers {remote.name}!{Style.RESET_ALL}")
        return True
    
    except git.exc.GitCommandError as e:
        click.echo(f"{Fore.RED}Erreur lors du push: {e}{Style.RESET_ALL}")
        return False

@click.group(invoke_without_command=True)
@click.option("--path", default=".", help="Chemin vers le dépôt Git")
@click.option("--preview/--no-preview", default=True, help="Aperçu des changements avant de commiter")
@click.option("--edit/--no-edit", default=True, help="Éditer le message de commit avant de commiter")
@click.option("--push/--no-push", default=False, help="Pousser les changements après le commit")
@click.option("--style", type=click.Choice(["detailed", "conventional", "simple"]), default="detailed", help="Style du message de commit")
@click.option("--emoji/--no-emoji", default=False, help="Utiliser des emoji dans les messages de commit")
@click.option("--interactive/--no-interactive", default=False, help="Utiliser le mode interactif pour le staging")
@click.version_option()
@click.pass_context
def main(ctx, path, preview, edit, push, style, emoji, interactive):
    """
    Git Commit Simplifier - Un outil pour simplifier la création de messages de commit Git.
    """
    if ctx.invoked_subcommand is None:
        # Charger la configuration
        config = load_config()
        
        # Les options de ligne de commande ont priorité sur la configuration
        style = style or config.get("style", "detailed")
        emoji = emoji if emoji is not None else config.get("emoji", False)
        push = push if push is not None else config.get("auto_push", False)
        
        # Obtenir le dépôt Git
        repo = get_repo(path)
        
        # Mode interactif pour le staging si demandé
        if interactive:
            interactive_staging(repo)
        
        # Obtenir les fichiers en staging
        staged_diffs = get_staged_files(repo)
        
        if not staged_diffs:
            click.echo(f"{Fore.YELLOW}Aucun changement en staging. Utilisez 'git add' pour ajouter des fichiers.{Style.RESET_ALL}")
            return
        
        # Analyser les fichiers en staging
        staged_files = []
        for diff in staged_diffs:
            file_path = diff.a_path or diff.b_path
            category = categorize_file(file_path, config)
            change_type, details = analyze_diff_content(diff)
            staged_files.append((file_path, category, change_type, details))
        
        # Afficher un aperçu des changements si demandé
        if preview:
            preview_changes(repo)
        
        # Générer le message de commit
        commit_message = generate_commit_message(staged_files, style, emoji)
        
        # Afficher le message de commit généré
        click.echo(f"\n{Fore.CYAN}Message de commit généré:{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{commit_message}{Style.RESET_ALL}")
        
        # Demander confirmation
        if click.confirm(f"\n{Fore.CYAN}Voulez-vous commiter ces changements?{Style.RESET_ALL}", default=True):
            # Commiter les changements
            if commit_changes(repo, commit_message, edit):
                # Pousser les changements si demandé
                if push:
                    push_changes(repo)

@main.command()
@click.option("--style", type=click.Choice(["detailed", "conventional", "simple"]), help="Style du message de commit")
@click.option("--emoji/--no-emoji", help="Utiliser des emoji dans les messages de commit")
@click.option("--auto-push/--no-auto-push", help="Pousser automatiquement les changements après le commit")
def config(style, emoji, auto_push):
    """
    Configurer Git Commit Simplifier.
    """
    # Charger la configuration existante
    config = load_config()
    
    # Mettre à jour la configuration avec les nouvelles valeurs
    if style is not None:
        config["style"] = style
    if emoji is not None:
        config["emoji"] = emoji
    if auto_push is not None:
        config["auto_push"] = auto_push
    
    # Enregistrer la configuration
    save_config(config)
    
    # Afficher la configuration actuelle
    click.echo(f"{Fore.GREEN}Configuration enregistrée:{Style.RESET_ALL}")
    click.echo(json.dumps(config, indent=2))

if __name__ == "__main__":
    main()
