"""Conventional commits format support for git-commit-simplifier."""

from typing import Dict, List, Optional, Tuple

from .config import get_config_value


def format_conventional_commit(
    change_type: str, 
    scope: Optional[str] = None, 
    breaking: bool = False, 
    description: str = "", 
    body: Optional[str] = None, 
    footer: Optional[str] = None
) -> str:
    """Format a commit message according to the Conventional Commits specification.
    
    Args:
        change_type: Type of change (feat, fix, etc.)
        scope: Scope of the change (optional)
        breaking: Whether this is a breaking change
        description: Short description of the change
        body: Detailed description of the change (optional)
        footer: Footer with additional information (optional)
        
    Returns:
        Formatted commit message
    """
    # Ensure the change type is valid
    valid_types = get_config_value("conventional_types")
    if change_type not in valid_types:
        change_type = "chore"  # Default to chore if invalid
    
    # Format the header
    header = f"{change_type}"
    if scope:
        header += f"({scope})"
    if breaking:
        header += "!"
    header += f": {description}"
    
    # Build the message
    message_parts = [header]
    
    if body:
        message_parts.append("")  # Empty line after header
        message_parts.append(body)
    
    if breaking and not footer:
        message_parts.append("")  # Empty line before footer
        message_parts.append("BREAKING CHANGE: This commit introduces breaking changes.")
    
    if footer:
        message_parts.append("")  # Empty line before footer
        message_parts.append(footer)
    
    return "\n".join(message_parts)


def convert_to_conventional(
    primary_change_type: str, 
    categories: Dict[str, List[Dict]], 
    is_breaking: bool = False
) -> Tuple[str, Optional[str], str]:
    """Convert a change type to a conventional commit type.
    
    Args:
        primary_change_type: Primary type of change
        categories: Categories of changes
        is_breaking: Whether this is a breaking change
        
    Returns:
        Tuple of (conventional_type, scope, description)
    """
    # Map our change types to conventional commit types
    type_mapping = {
        "feature": "feat",
        "fix": "fix",
        "docs": "docs",
        "style": "style",
        "refactor": "refactor",
        "performance": "perf",
        "test": "test",
        "chore": "chore",
        "update": "chore"
    }
    
    conventional_type = type_mapping.get(primary_change_type, "chore")
    
    # Determine scope
    scope = None
    if len(categories) == 1:
        scope = next(iter(categories))
    
    # Generate description
    if len(categories) == 1:
        category = next(iter(categories))
        category_files = categories[category]
        
        if len(category_files) <= 3:
            # If few files changed, list them in the description
            files = [item['path'].split(' → ')[-1] for item in category_files]
            description = f"update {', '.join(files)}"
        else:
            # Otherwise, use a general description
            description = f"update multiple {category} files"
    else:
        description = "update multiple files across different categories"
    
    return conventional_type, scope, description


def generate_conventional_commit_message(changes: Dict[str, List[Dict]]) -> str:
    """Generate a commit message in the Conventional Commits format.
    
    Args:
        changes: Dictionary containing detailed information about changes
        
    Returns:
        Formatted commit message
    """
    # Determine the primary change type
    change_types = {}
    for change_list in [changes.get('added', []), changes.get('modified', []), 
                        changes.get('deleted', []), changes.get('renamed', [])]:
        for item in change_list:
            change_type = item.get('change_type', 'update')
            change_types[change_type] = change_types.get(change_type, 0) + 1
    
    primary_change_type = max(change_types.items(), key=lambda x: x[1])[0] if change_types else 'update'
    
    # Check if this is a breaking change
    is_breaking = False
    for change_list in [changes.get('modified', []), changes.get('deleted', [])]:
        for item in change_list:
            if 'breaking' in item.get('details', []):
                is_breaking = True
                break
    
    # Convert to conventional commit format
    conv_type, scope, description = convert_to_conventional(
        primary_change_type, changes['categories'], is_breaking
    )
    
    # Generate the body
    body_parts = []
    for category, items in changes['categories'].items():
        if items:
            body_parts.append(f"## {category.capitalize()}")
            for item in items:
                path = item['path']
                change_type = item['change_type']
                details = item.get('details', [])
                
                if change_type == 'feature':
                    prefix = "Add"
                elif change_type == 'fix':
                    prefix = "Fix"
                elif change_type == 'refactor':
                    prefix = "Refactor"
                elif change_type == 'docs':
                    prefix = "Document"
                elif change_type == 'test':
                    prefix = "Test"
                elif change_type == 'style':
                    prefix = "Style"
                elif change_type == 'performance':
                    prefix = "Optimize"
                elif change_type == 'chore':
                    prefix = "Update"
                else:
                    prefix = "Update"
                
                detail_text = f" ({', '.join(details)})" if details else ""
                body_parts.append(f"- {prefix} {path}{detail_text}")
            
            body_parts.append("")  # Empty line after each category
    
    body = "\n".join(body_parts).strip() if body_parts else None
    
    # Generate the footer
    footer = None
    if is_breaking:
        footer = "BREAKING CHANGE: This commit introduces breaking changes."
    
    # Format the commit message
    return format_conventional_commit(
        change_type=conv_type,
        scope=scope,
        breaking=is_breaking,
        description=description,
        body=body,
        footer=footer
    )
