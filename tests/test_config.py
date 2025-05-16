"""Tests for the config module."""

import os
import json
import tempfile
from unittest.mock import patch

import pytest
from git_commit_simplifier.config import (DEFAULT_CONFIG, get_config_path,
                                         get_config_value, init_config,
                                         load_config, save_config,
                                         set_config_value)


def test_get_config_path():
    """Test getting the config path."""
    # Test with config in current directory
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        with open('.git-commit-simplifier.json', 'w') as f:
            json.dump({}, f)
        
        assert get_config_path() == '.git-commit-simplifier.json'
    
    # Test with no config file (should return path in home directory)
    with patch('os.path.exists', return_value=False):
        path = get_config_path()
        assert '~' in path or 'home' in path or 'Users' in path


def test_load_config():
    """Test loading the configuration."""
    # Test with no config file
    with patch('git_commit_simplifier.config.get_config_path', return_value='/nonexistent/path'):
        with patch('os.path.exists', return_value=False):
            config = load_config()
            assert config == DEFAULT_CONFIG
    
    # Test with existing config file
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        json.dump({"commit_style": "conventional"}, temp_file)
        temp_file.flush()
        
        with patch('git_commit_simplifier.config.get_config_path', return_value=temp_file.name):
            config = load_config()
            assert config["commit_style"] == "conventional"
            # Other values should be from default config
            assert "emoji" in config
    
    os.unlink(temp_file.name)


def test_save_config():
    """Test saving the configuration."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        with patch('git_commit_simplifier.config.get_config_path', return_value=temp_file.name):
            result = save_config({"test": "value"})
            assert result is True
            
            # Verify the file was written correctly
            temp_file.seek(0)
            saved_config = json.load(temp_file)
            assert saved_config == {"test": "value"}
    
    os.unlink(temp_file.name)


def test_init_config():
    """Test initializing the configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, 'config.json')
        
        with patch('git_commit_simplifier.config.get_config_path', return_value=config_path):
            # Config file doesn't exist yet
            assert not os.path.exists(config_path)
            
            # Initialize config
            config = init_config()
            
            # Config file should now exist with default values
            assert os.path.exists(config_path)
            assert config == DEFAULT_CONFIG


def test_get_config_value():
    """Test getting a configuration value."""
    with patch('git_commit_simplifier.config.load_config', return_value={"test": "value"}):
        # Existing key
        assert get_config_value("test") == "value"
        
        # Non-existing key with default
        assert get_config_value("nonexistent", "default") == "default"
        
        # Non-existing key without default
        assert get_config_value("nonexistent") is None


def test_set_config_value():
    """Test setting a configuration value."""
    mock_config = {"existing": "value"}
    
    with patch('git_commit_simplifier.config.load_config', return_value=mock_config), \
         patch('git_commit_simplifier.config.save_config', return_value=True):
        
        # Set existing key
        result = set_config_value("existing", "new_value")
        assert result is True
        assert mock_config["existing"] == "new_value"
        
        # Set new key
        result = set_config_value("new_key", "new_value")
        assert result is True
        assert mock_config["new_key"] == "new_value"
