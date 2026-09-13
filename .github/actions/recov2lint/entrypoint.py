"""Compatibility entrypoint; run from a repository checkout."""

import os
from pathlib import Path
import subprocess
import sys


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'v2'
    workspace = Path(os.environ.get('GITHUB_WORKSPACE', Path.cwd()))
    sys.exit(subprocess.call(
        [sys.executable, '-m', 'scripts.validate_corpus', '--root', root],
        cwd=workspace,
    ))
