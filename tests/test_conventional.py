"""Tests for the conventional commits module."""

import pytest
from git_commit_simplifier.conventional import (convert_to_conventional,
                                              format_conventional_commit,
                                              generate_conventional_commit_message)


def test_format_conventional_commit():
    """Test formatting a conventional commit message."""
    # Basic commit
    message = format_conventional_commit(
        change_type="feat",
        description="add new feature"
    )
    assert message == "feat: add new feature"
    
    # Commit with scope
    message = format_conventional_commit(
        change_type="fix",
        scope="ui",
        description="resolve button alignment"
    )
    assert message == "fix(ui): resolve button alignment"
    
    # Breaking change
    message = format_conventional_commit(
        change_type="refactor",
        breaking=True,
        description="change API response format"
    )
    assert message == "refactor!: change API response format"
    
    # With body
    message = format_conventional_commit(
        change_type="docs",
        description="update README",
        body="Add installation instructions and examples."
    )
    assert message == "docs: update README\n\nAdd installation instructions and examples."
    
    # With footer
    message = format_conventional_commit(
        change_type="feat",
        description="add user authentication",
        footer="Closes #123"
    )
    assert message == "feat: add user authentication\n\nCloses #123"
    
    # Complete message
    message = format_conventional_commit(
        change_type="feat",
        scope="auth",
        breaking=True,
        description="implement OAuth2",
        body="This adds OAuth2 authentication support.",
        footer="BREAKING CHANGE: Previous authentication methods are no longer supported.\nCloses #456"
    )
    assert "feat(auth)!: implement OAuth2" in message
    assert "This adds OAuth2 authentication support." in message
    assert "BREAKING CHANGE: Previous authentication methods are no longer supported." in message
    assert "Closes #456" in message


def test_convert_to_conventional():
    """Test converting change types to conventional commit format."""
    # Feature change
    conv_type, scope, description = convert_to_conventional(
        primary_change_type="feature",
        categories={"python": [{"path": "app.py"}]}
    )
    assert conv_type == "feat"
    assert scope == "python"
    assert "python" in description
    
    # Fix change
    conv_type, scope, description = convert_to_conventional(
        primary_change_type="fix",
        categories={"ui": [{"path": "button.css"}, {"path": "form.css"}]}
    )
    assert conv_type == "fix"
    assert scope == "ui"
    assert "ui" in description
    
    # Multiple categories
    conv_type, scope, description = convert_to_conventional(
        primary_change_type="refactor",
        categories={
            "python": [{"path": "app.py"}],
            "ui": [{"path": "button.css"}]
        }
    )
    assert conv_type == "refactor"
    assert scope is None  # No scope for multiple categories
    assert "multiple" in description


def test_generate_conventional_commit_message():
    """Test generating a conventional commit message from changes."""
    changes = {
        'added': [
            {'path': 'new.py', 'category': 'python', 'change_type': 'feature', 'details': ['new file']}
        ],
        'modified': [
            {'path': 'test.py', 'category': 'python', 'change_type': 'fix', 'details': ['bug fix']}
        ],
        'deleted': [],
        'renamed': [],
        'categories': {
            'python': [
                {'path': 'new.py', 'category': 'python', 'change_type': 'feature', 'details': ['new file']},
                {'path': 'test.py', 'category': 'python', 'change_type': 'fix', 'details': ['bug fix']}
            ]
        }
    }
    
    message = generate_conventional_commit_message(changes)
    
    # Should be a conventional commit message
    assert message.startswith(("feat", "fix"))
    assert ":" in message
    
    # Should include the category as scope
    assert "(python)" in message
    
    # Should include details in the body
    assert "new.py" in message
    assert "test.py" in message
