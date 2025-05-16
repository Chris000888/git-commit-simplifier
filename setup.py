from setuptools import setup, find_packages
import os
import sys

# Définir une description par défaut
default_description = "A tool to simplify Git commit message creation by analyzing changes"

# Essayer de lire README.md, utiliser la description par défaut en cas d'échec
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except (FileNotFoundError, IOError):
    print("Warning: Could not read README.md, using default description")
    long_description = default_description

# Créer le répertoire scripts s'il n'existe pas
if not os.path.exists('scripts'):
    os.makedirs('scripts')

# Créer le script git_commit_simplifier
with open('scripts/git_commit_simplifier', 'w') as f:
    f.write('''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Assurer que le package est dans le path
package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, package_dir)

# Importer et exécuter la fonction principale
from git_commit_simplifier.cli import main

if __name__ == "__main__":
    main()
''')

# Rendre le script exécutable
os.chmod('scripts/git_commit_simplifier', 0o755)

# Créer le script git-commit-simplifier (avec tiret)
with open('scripts/git-commit-simplifier', 'w') as f:
    f.write('''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Assurer que le package est dans le path
package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, package_dir)

# Importer et exécuter la fonction principale
from git_commit_simplifier.cli import main

if __name__ == "__main__":
    main()
''')

# Rendre le script exécutable
os.chmod('scripts/git-commit-simplifier', 0o755)

setup(
    name="git-commit-simplifier",
    version="0.1.3",
    author="Christopher Dato",
    author_email="christopherdato08@gmail.com",
    description=default_description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Chris000888/git-commit-simplifier",
    project_urls={
        "Bug Tracker": "https://github.com/Chris000888/git-commit-simplifier/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
    install_requires=[
        "gitpython>=3.1.40",
        "click>=8.1.7",
        "colorama>=0.4.6",
        "prompt_toolkit>=3.0.36",
    ],
    # Utiliser à la fois scripts et entry_points pour une compatibilité maximale
    scripts=[
        'scripts/git_commit_simplifier',
        'scripts/git-commit-simplifier',
    ],
    entry_points={
        "console_scripts": [
            "git-commit-simplifier=git_commit_simplifier.cli:main",
            "git_commit_simplifier=git_commit_simplifier.cli:main",
            "gitcommitsimplifier=git_commit_simplifier.cli:main",  # Nom sans tiret ni underscore
            "gcs=git_commit_simplifier.cli:main",  # Alias court
        ],
    },
)
