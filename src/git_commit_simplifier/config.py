#!/usr/bin/env python3
"""
Module de configuration pour Git Commit Simplifier.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

# Nom du fichier de configuration
CONFIG_FILE_NAME = ".git-commit-simplifier.json"

# Configuration par défaut
DEFAULT_CONFIG = {
    "style": "detailed",
    "emoji": False,
    "auto_push": False,
    "categories": {
        "python": [r"\.py$", r"\.pyw$"],
        "javascript": [r"\.js$", r"\.jsx$", r"\.ts$", r"\.tsx$"],
        "frontend": [r"\.html$", r"\.htm$", r"\.css$", r"\.scss$", r"\.sass$"],
        "documentation": [r"\.md$", r"\.rst$", r"\.txt$", r"docs/"],
        "configuration": [r"\.yml$", r"\.yaml$", r"\.json$", r"\.toml$", r"\.ini$", r"\.cfg$", r"config/"],
        "database": [r"\.sql$", r"migrations/", r"models/", r"schema"],
        "script": [r"\.sh$", r"\.bash$", r"\.zsh$", r"\.fish$", r"scripts/"],
        "backend": [r"\.c$", r"\.cpp$", r"\.h$", r"\.hpp$", r"\.java$", r"\.go$", r"\.rs$"],
        "assets": [r"\.png$", r"\.jpg$", r"\.jpeg$", r"\.gif$", r"\.svg$", r"\.ico$", r"assets/", r"static/"]
    },
    "change_types": {
        "feat": [r"feat", r"feature", r"add", r"new"],
        "fix": [r"fix", r"bug", r"issue", r"error", r"problem"],
        "docs": [r"doc", r"documentation", r"comment"],
        "style": [r"style", r"format", r"indent", r"whitespace", r"space", r"tab"],
        "refactor": [r"refactor", r"clean", r"improve", r"optimize"],
        "test": [r"test", r"assert", r"spec"],
        "chore": [r"chore", r"build", r"ci", r"release"]
    }
}

def get_config_path() -> Path:
    """
    Obtient le chemin vers le fichier de configuration.
    Cherche d'abord dans le répertoire courant, puis dans le répertoire utilisateur.
    """
    # Chercher dans le répertoire courant
    local_config = Path.cwd() / CONFIG_FILE_NAME
    if local_config.exists():
        return local_config
    
    # Chercher dans le répertoire utilisateur
    user_config = Path.home() / CONFIG_FILE_NAME
    return user_config

def load_config() -> Dict[str, Any]:
    """
    Charge la configuration depuis le fichier de configuration.
    Si le fichier n'existe pas, retourne la configuration par défaut.
    """
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # Fusionner avec la configuration par défaut pour les valeurs manquantes
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config)
            return merged_config
        
        except (json.JSONDecodeError, IOError):
            # En cas d'erreur, retourner la configuration par défaut
            return DEFAULT_CONFIG
    
    return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> None:
    """
    Enregistre la configuration dans le fichier de configuration.
    """
    config_path = get_config_path()
    
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    
    except IOError as e:
        print(f"Erreur lors de l'enregistrement de la configuration: {e}")
