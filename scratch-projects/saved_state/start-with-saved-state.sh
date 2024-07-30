set -x

# As of end of July, the open-source client has all the hooks for saved
# state but actually drops it silently. Grrr, I really wish we didn't
# delete code in such an unprincipled (in terms of UX) way.
echo "NOTE: THIS WILL NOT WORK IF YOU ARE USING AN OSS CLIENT AS OF 2024-07-30"

# make sure we start from a clean slate
pyre stop
rm -rf /tmp/scratch-saved-state

# Make a saved state
pyre -n --save-initial-state-to /tmp/scratch-saved-state || true

# Shut down
pyre stop

# Boot off of the saved state
pyre -n --load-initial-state-from /tmp/scratch-saved-state start --terminal
