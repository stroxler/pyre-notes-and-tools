# Minimal typeshed


A copy of typeched circa Spring 2021, with everything but the
standard library removed. I made this by unpacking a zipped
typeshed from the `main` branch of `facebook/pyre-check`.

The advantage of a limited typeshed is that pyre can parse
sources much faster (a clean run of pyre even on a tiny project
pays a fixed cost due to parsing several thousand stubs from
typeshed - cutting it down to a few hundred is a huge help!).
