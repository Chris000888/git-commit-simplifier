"""Tests for the CLI module."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner
from git import Repo
from git_commit_simplifier.cli import (analyze_changes, display_changes,
                                      generate_commit_message,
                                      get_file_category, main)


def test_version():
    """Test the version option."""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()


def test_get_file_category():
    """Test the file categorization function."""
    assert get_file_category('README.md') == 'documentation'
    assert get_file_category('setup.py') == 'build'
    assert get_file_category('config.yaml') == 'configuration'
    assert get_file_category('tests/test_app.py') == 'test'
    assert get_file_category('src/app.py') == 'python'
    assert get_file_category('styles.css') == 'style'
    assert get_file_category('index.html') == 'ui'
    assert get_file_category('migrations/001_init.sql') == 'database'
    assert get_file_category('unknown.xyz') == 'other'


@pytest.fixture
def git_repo():
    """Create a temporary Git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize git repo
        repo = Repo.init(temp_dir)
        
        # Create a test file
        test_file = os.path.join(temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('print("Hello, World!")')
        
        # Add and commit the file
        repo.git.add(test_file)
        repo.git.commit('-m', 'Initial commit')
        
        yield temp_dir, repo


def test_analyze_changes_no_changes(git_repo):
    """Test analyzing changes when there are no changes."""
    temp_dir, _ = git_repo
    
    # No changes since last commit
    with patch('git_commit_simplifier.cli.get_config_value', return_value=False):
        changes = analyze_changes(temp_dir)
    assert changes is None


def test_analyze_changes_with_changes(git_repo):
    """Test analyzing changes when there are changes."""
    temp_dir, repo = git_repo
    
    # Modify the test file
    test_file = os.path.join(temp_dir, 'test.py')
    with open(test_file, 'w') as f:
        f.write('print("Hello, Modified World!")')
    
    # Add a new file
    new_file = os.path.join(temp_dir, 'new.py')
    with open(new_file, 'w') as f:
        f.write('print("New file")')
    
    # Stage the modified file but not the new file
    repo.git.add(test_file)
    
    # Analyze changes
    with patch('git_commit_simplifier.cli.get_config_value', return_value=False), \
         patch('click.confirm', return_value=False):
        changes = analyze_changes(temp_dir)
    
    assert changes is not None
    assert len(changes['modified']) == 1
    assert changes['modified'][0]['path'] == 'test.py'
    assert changes['modified'][0]['category'] == 'python'


def test_generate_commit_message():
    """Test generating a commit message from changes."""
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
    
    # Test detailed style
    with patch('git_commit_simplifier.cli.get_config_value', side_effect=lambda key, default=None: 
              "detailed" if key == "commit_style" else 
              False if key == "emoji" else 
              72 if key == "max_subject_length" else 
              default):
        message = generate_commit_message(changes)
        assert 'new.py' in message
        assert 'test.py' in message
        assert 'python' in message.lower()
    
    # Test simple style
    with patch('git_commit_simplifier.cli.get_config_value', side_effect=lambda key, default=None: 
              "simple" if key == "commit_style" else 
              False if key == "emoji" else 
              72 if key == "max_subject_length" else 
              default):
        message = generate_commit_message(changes)
        assert '\n' not in message  # Simple style has no newlines
    
    # Test conventional style
    with patch('git_commit_simplifier.cli.get_config_value', return_value="conventional"), \
         patch('git_commit_simplifier.cli.generate_conventional_commit_message', return_value="feat: test message"):
        message = generate_commit_message(changes)
        assert message == "feat: test message"


def test_display_changes():
    """Test displaying changes."""
    changes = {
        'added': [
            {'path': 'new.py', 'category': 'python', 'change_type': 'feature', 'details': ['new file']}
        ],
        'modified': [
            {'path': 'test.py', 'category': 'python', 'change_type': 'fix', 'details': ['bug fix']}
        ],
        'deleted': [
            {'path': 'old.py', 'category': 'python', 'change_type': 'chore', 'details': ['removed file']}
        ],
        'renamed': [
            {'path': 'old.js → new.js', 'category': 'javascript', 'change_type': 'refactor', 'details': ['renamed file']}
        ],
        'categories': {}
    }
    
    # Just test that it doesn't raise an exception
    display_changes(changes)


def test_main_command_no_repo():
    """Test the main command when not in a git repository."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('git_commit_simplifier.cli.init_config'):
            result = runner.invoke(main, ['--path', temp_dir])
            assert result.exit_code == 0
            assert 'Error: Not a valid git repository' in result.output


def test_main_command_with_changes():
    """Test the main command with changes."""
    runner = CliRunner()
    
    # Mock the necessary functions
    mock_changes = {
        'added': [{'path': 'new.py', 'category': 'python', 'change_type': 'feature', 'details': ['new file']}],
        'modified': [],
        'deleted': [],
        'renamed': [],
        'categories': {'python': [{'path': 'new.py', 'category': 'python', 'change_type': 'feature', 'details': ['new file']}]}
    }
    
    with patch('git_commit_simplifier.cli.init_config'), \
         patch('git_commit_simplifier.cli.analyze_changes', return_value=mock_changes), \
         patch('git_commit_simplifier.cli.display_changes'), \
         patch('git_commit_simplifier.cli.generate_commit_message', return_value='Add new.py'), \
         patch('click.confirm', return_value=False):
        
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert 'Suggested commit message' in result.output


def test_config_command():
    """Test the config command."""
    runner = CliRunner()
    
    with patch('git_commit_simplifier.cli.set_config_value', return_value=True):
        result = runner.invoke(main, ['config', '--style', 'conventional', '--emoji'])
        assert result.exit_code == 0
        assert 'Configuration updated successfully' in result.output
        assert 'Commit style: conventional' in result.output
        assert 'Use emoji: True' in result.output
