# VSCode setup

## Plugins

- The standard vim-bindings plugin (not neovim-in-vscode - that sounds great
  but seems to be buggy in reality).
- Some color themes
  - Noctis: my preferred color theme pack for VSCode, very nice. I particularly
    like Noctic Azurus (blue), Noctis (green), and Noctis Minimus (gray).
  - Tomorrow Night Blue: a solid theme, and distinct from what I would choose
    for emacs, vim, or terminal. I currently use Noctis for internal VSCode
    and remote machines, Tomorrow Night Blue for stock vscode locally.
- OCaml Platform - the official ocaml toolchain. Mostly works pretty well,
  although I had to write a daemon script to kill duplicate LSP processes
  that periodically start up.

## Color Themes

In internal VSCode (unsure how well this maps to open-source VSCode) if you
want to set color themes per environment you can do it through the UI... sadly
I haven't figured out a way to do it in json which would have been easier
to replicate.

The flow is:
 - Command-P => "Preferences: Open User Settings"
 - search for "workbench.colorTheme"
 - in the page that pops up, there will be tabs that represent nested
   notions of "where you are".
   - User: this is your default user color theme
   - Workspace: this is an overlay on User; by default in our internal
     setup this seems to be per-machine (or maybe per repo?), this is where
     I can set it to differ for local vs various remote flavors.
   - Folder: I suspect this is an overlay on top of "Workspace" so that you
     could set it for individual sub-projects; at the moment I'm not super
     interested in this, I mostly wanted to visually distinguish local
     and different flavors of remote.
