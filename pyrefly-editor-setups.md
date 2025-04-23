# NVim:

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
