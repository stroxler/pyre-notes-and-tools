# An ultra-basic nvim config

Using the `xx-basic-lsp` branch of `nvim-starter` from
https://github.com/VonHeikemen/nvim-starter/tree/xx-basic-lsp, I was
able to make pyrefly work against our own `conformance/third-party` directory
with this call to the native vim LSP client:
```
lsp_setup({
  name = 'pyrefly',
  cmd = {'pyrefly-dev', 'lsp'},
  filetypes = {
    'python',
  },
  root_dir = function()
   -- hack to make pyrefly treat conformance tests as a valid dir
   return find_first({'_qualifiers_final_decorator.pyi'})
  end,
})
```

Note that Pyrefly doesn't need any config at all to run against (at least most
of?) the conformance tests because it bundles the stdlib typeshed, which leads to the
weird hack where I'm using one of the importable modules as a marker for the project
root.

# Vanilla Python + Rust development

I'd really like to sandbox things with nix rather than installers someday, but I just don't
have the time, so using uv and rustup at the moment.

Install:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

I don't allow installers to muck with my environment. The install locations are
- `~/.local/bin/uv` for uv
- `~/.cargo/bin` for rustup stuff

I can add these to a local environment by putting
```
export PATH=~/.local/bin/:~/.cargo/bin:$PATH
```
in an `.envrc`.

To bootstrap a project with uv, just run `uv sync`, which will auto-create a virtualenv
at `<project_root>/.venv`. You can get this in the `.envrc` by adding
```
. .venv/bin/activate
```

This setup isn't as sandboxed as nix, but for my current needs it's still pretty sandboxed:
- neither rustup nor uv are in my default profile, they are explicitly added
- cargo builds and uv venvs are both reasonably sandboxed, except from system packages
