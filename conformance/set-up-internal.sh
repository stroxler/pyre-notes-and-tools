set -ex

# clone upstream so we can copy code in
rm -rf /tmp/oss-python-typing
git clone git@github.com:python/typing.git /tmp/oss-python-typing

# set up the source tree for (internal) pyre
mkdir -p src
ln -s .pyre_configuration.internal .pyre_configuration

# copy over all the python files
cp /tmp/oss-python-typing/conformance/tests/* src/
# also copy the toml files so that it's easy to see notes side-by-side with code
cp /tmp/oss-python-typing/conformance/results/pyre/* src/

# clean up
rm -rf /tmp/oss-python-typing

