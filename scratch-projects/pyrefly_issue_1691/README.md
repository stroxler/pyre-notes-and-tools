# Attempt to repro a Pyrefly package bug

This directory has a simple project trying to reproduce
https://github.com/facebook/pyrefly/issues/1691

Setup:
```
uv venv
uv pip install pyrefly
pyrefly check
```

------

The setup is actually wrong though, issue 1691 is actually
a configuration bug because the layout is more complex.

See the script at pyrefly_circular_imports.py which sets
up the project layout in a temp directory. To run that
script you'll need to install `rich` and `lsp_types` in
addition to `pyrefly`:
```
uv pip install lsp_types
uv pip install rich
```
