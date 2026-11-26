#!/usr/bin/env python3
"""Read-only local/CI syntax checks and pure tests; never import VM setup scripts."""
import ast
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
for path in sorted(root.glob('*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
for path in sorted(root.glob('*.sh')):
    subprocess.run(['bash', '-n', str(path)], check=True)
subprocess.run([sys.executable, str(root / 'test-folder-redirection.py')], check=True)
print('LAB_STATIC_CHECKS_OK')
