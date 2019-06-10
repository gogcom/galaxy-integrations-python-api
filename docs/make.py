"""Builds documentation locally. Use for preview only"""

import pathlib
import subprocess
import webbrowser


source = pathlib.Path("docs", "source")
build = pathlib.Path("docs", "build")
master_doc = 'index.html'

subprocess.run(['sphinx-build', '-M', 'clean', str(source), str(build)])
subprocess.run(['sphinx-build', '-M', 'html', str(source), str(build)])

master_path = build / 'html' / master_doc
webbrowser.open(f'file://{master_path.resolve()}')