# Debugging Rust

The Meta rust toolchain seems to be pretty comparable to open-source vscode: we
can use lldb with some of the rust helpers that make structs printable; this
mainly works in the pop-up view at left, the actual lldb console seems to not
pick up the pretty-printers.

References aren't viewable (they print as raw pointer addresses), but you can
dereference them and get some pretty printing.

This is enough to help a bit, but I wasn't satisfied: you very quickly, when defining
custom datatypes, start to exceed the ability of the pretty-printer to traverse chained
pointers.

## Manual simulated-print debugging

The lldb + pretty-printing setup does seem to be smart enough to print `String` values
really nicely.

Consider this helper function:
```
pub fn string_of_debug(x: &dyn std::fmt::Debug) -> String {
    format!("{x:?}")
}
```

You can use this to view complex data semi-manually by defining lots of string variables
before a debug run, e.g.
```
let ty_str = crate::util::string_of_debug(ty)
```

This could get annoying since it's still print debugging, but it has several advantages:
- it avoids log spam; if you set a conditional breakpoint and look at the vars in the
  left-hand debug pane, you'll only see what's relevant
- you can visually see the control flow at the same time as viewing the dumped
  variables.
- assuming you make these vars up and down the callstack (again, annoying!), you can
  navigate up and down the callstack in the debugger to dynamically view the state,
  which is hard to reconstruct from just print debug output

In addition, as annoying as defining these vars is, it's at least probably doable in
a snippet or macro - at any rate, very easy to script in neovim or emacs.

Unfortunately there's probably no way to actually make this work with lldb, at least
without deep expertise :/
 - I can actually make the function findable pretty easily, all I need is `#[no_mangle]`
 - But the rust compiler is creating these trait objects (fat pointers with the reference
   plus a vtable reference) automagically, and lldb cannot replicate it
 - If I really knew lldb well, I *might* be able to script this (if there's a way to
   predictably find the trait objects and make the fat pointer manually). It's something
   I could look into in the future I guess.


## Interactive debugging with `Debug` traits in O(types) up-front effort

Even more exciting is this: if (anywhere in the crate!) you define a function like
these:
```
#[no_mangle]
pub extern "C" fn string_of_type(ty: &crate::types::types::Type) -> String {
    crate::util::string_of_debug(ty)
}

#[no_mangle]
pub extern "C" fn string_of_vec_type(tys: &Vec<crate::types::types::Type>) -> String {
    crate::util::string_of_debug(tys)
}
```
they become visible to lldb. And the magical trait object stuff that prevents me from directly
using `string_of_debug` goes away - now the compiler is trivially handling that, and I'm exposing
a completely static interface!

As a result, these helper functions are now callable directly in lldb (and with no namespacing!),
I can use them in `watch` expressions at will.

This is actually super exciting because I could:
- probably make a snippet to auto-generate these as needed
- save them all as I go, and make a script to add them into some crate module on the
  fly (I'd never get them past code review, but I could put them in my own
  github repo or something)

If I did that, I'd gradually build up a library of these static pretty-printers that could
probably handle most of the key types in a codebase, which means I can get something pretty
close to true interactive debugging!!
