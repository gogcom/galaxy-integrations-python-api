"""Builds documentation locally. Use for preview only"""

import subprocess
import webbrowser


source = "docs/source"
build = "docs/build"
master_doc = 'index'

subprocess.run(['sphinx-build', '-M', 'clean', source, build])
subprocess.run(['sphinx-build', '-M', 'html', source, build])
webbrowser.open(f'{build}/html/{master_doc}')