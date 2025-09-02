#!/usr/bin/env python3
"""
Script to fix relative imports in the server directory
Converts relative imports (from ..module) to absolute imports (from module)
"""

import os
import re
from pathlib import Path

def fix_relative_imports(file_path):
    """Fix relative imports in a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match relative imports
    patterns = [
        (r'from \.\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', r'from \1'),
        (r'from \.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', r'from \1'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function to process all Python files in server directory"""
    server_dir = Path("D:/Projects2.0/BTP_HumanAICoCreation/human-ai-co-create/server")
    
    if not server_dir.exists():
        print(f"Server directory not found: {server_dir}")
        return
    
    fixed_files = []
    
    # Process all Python files recursively
    for py_file in server_dir.rglob("*.py"):
        if py_file.is_file():
            try:
                if fix_relative_imports(py_file):
                    fixed_files.append(str(py_file.relative_to(server_dir)))
            except Exception as e:
                print(f"Error processing {py_file}: {e}")
    
    if fixed_files:
        print(f"Fixed relative imports in {len(fixed_files)} files:")
        for file in fixed_files:
            print(f"  - {file}")
    else:
        print("No files needed fixing")

if __name__ == "__main__":
    main()
