#!/usr/bin/env python3
# /sensor-monitor-ds/recover_and_fix.py

"""
Recover and fix file headers - preserves all original formatting except headers.
Run this from your project root directory.
"""

import os
import re
from pathlib import Path

def should_ignore(filepath):
    """Check if file should be ignored"""
    ignore_patterns = [
        "build/", "*.egg-info/", "dist/", "*.pyc", "__pycache__/",
        "*.log", "*.pid", "sm_config.yaml", ".venv/", "venv/",
        ".vscode/", ".idea/", ".git/", "fix_headers.py"
    ]
    
    for pattern in ignore_patterns:
        if pattern.endswith('/'):
            if pattern.rstrip('/') in str(filepath).split('/'):
                return True
        elif filepath.match(pattern):
            return True
    return False

def is_text_file(filepath):
    """Check if file is a text file"""
    try:
        import subprocess
        result = subprocess.run(['file', '--mime-type', '-b', str(filepath)], 
                              capture_output=True, text=True)
        return result.stdout.strip().startswith('text/')
    except:
        return False

def extract_original_content(content):
    """
    Extract the original content by removing header lines and
    restoring proper line breaks.
    """
    lines = content.split('\n')
    
    # Find where the actual content starts (skip header lines)
    content_start = 0
    for i, line in enumerate(lines):
        # Skip empty lines at the top
        if not line.strip():
            continue
        # Skip shebang lines
        if line.startswith('#!'):
            continue
        # Skip path comment lines
        if re.match(r'^# (?:/|[\w\-\.]+/)', line):
            continue
        # Found actual content
        content_start = i
        break
    
    # Take the rest of the lines
    remaining_lines = lines[content_start:]
    
    # Join with newlines
    return '\n'.join(remaining_lines)

def fix_file(filepath, project_root, project_name):
    """Fix a single file's header while preserving all formatting"""
    
    # Get relative path
    rel_path = filepath.relative_to(project_root)
    correct_comment = f"# /{project_name}/{rel_path}"
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Check if first non-empty line is shebang
    lines = content.split('\n')
    first_non_empty = next((l for l in lines if l.strip()), '')
    has_shebang = first_non_empty.startswith('#!')
    shebang_line = first_non_empty if has_shebang else None
    
    # Extract original content (removing any header cruft)
    original_content = extract_original_content(content)
    
    # Build new content with proper formatting
    new_lines = []
    if has_shebang:
        new_lines.append(shebang_line)
        new_lines.append(correct_comment)
        new_lines.append('')  # blank line for readability
        # Add the original content, preserving its exact formatting
        if original_content:
            new_lines.append(original_content)
    else:
        new_lines.append(correct_comment)
        new_lines.append('')  # blank line for readability
        if original_content:
            new_lines.append(original_content)
    
    # Join with newlines, ensure no extra blank lines at the end
    new_content = '\n'.join(new_lines)
    
    # Write back if changed
    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False

def main():
    project_root = Path.cwd()
    project_name = project_root.name
    
    print(f"Working directory: {project_root}")
    print(f"Project name: {project_name}")
    print("=" * 60)
    print("WARNING: This will modify your files!")
    print("Press Enter to continue or Ctrl+C to abort...")
    input()
    
    # Find all files
    all_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(Path(d))]
        
        for file in files:
            filepath = Path(root) / file
            if should_ignore(filepath):
                continue
            if not is_text_file(filepath):
                continue
            all_files.append(filepath)
    
    # Process files
    fixed_count = 0
    for filepath in all_files:
        if fix_file(filepath, project_root, project_name):
            print(f"✓ FIXED: {filepath.relative_to(project_root)}")
            fixed_count += 1
        else:
            print(f"  OK: {filepath.relative_to(project_root)}")
    
    print("=" * 60)
    print(f"Done! Fixed {fixed_count} files.")
    
    # Show a sample of the fixed file
    print("\nSample of fixed test_parsers.py:")
    print("-" * 60)
    sample_file = project_root / "tests" / "test_parsers.py"
    if sample_file.exists():
        with open(sample_file, 'r') as f:
            lines = f.readlines()[:20]  # First 20 lines
        for line in lines:
            print(line.rstrip())
    else:
        print("test_parsers.py not found")

if __name__ == "__main__":
    main()