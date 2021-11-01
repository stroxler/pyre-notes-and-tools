# pyre-check-scratch-projects

Some scratch projects I can use for fast end-to-end tests
of pyre changes.

One of the key things about projects here is that they can make
use of small "typeshed" directories that help pyre run much
faster than it does on full-sized projects.

## Why aren't these in facebook/pyre-check?

We keep unit tests and a handful of integration tests in
`pyre-check`, but only things we're willing to hook up to
continuous integration. Having large numbers of end-to-end tests
isn't scalable for CI systems.

But certain types of work - particularly experimental work that
involves many components - is prone to bugs at the integration
layer. In my case, I've done a lot of work on `pyre infer` trying
to make sure that the pyre backend, the pyre python client, and
the LibCST code generation all work together to produce as clean
an output as possible. Many of the bugs I've encountered are hard
to catch with just unit tests.

Hence this project, where I'm intending to create some example
python projects that I can use to see the results of end-to-end
`pyre infer` runs.
