#!/usr/bin/env python3

"""
For reasons I haven't been able to work out yet, my Visual Studio Code seems to
lose its connection to ocamllsp pretty frequently. It always seems to coincide with
multiple `ocamllsp` instances being started up, and as a result it's pretty easy
to detect and mitigate by killing them all.

"""


import logging
import subprocess
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocamllsp_killer")

def count_ocamllsp() -> int:
    ps_aux_out = subprocess.check_output(["ps", "aux"], encoding="utf-8")
    count = 0
    for line in ps_aux_out.splitlines():
        if " ocamllsp" in line:  # the space prevents us from counting ourself!
            time.sleep(0.25)
            count += 1
    logger.info("Counted %d matching ps aux lines", count)
    return count


def kill_ocamllsp() -> None:
    subprocess.check_call(["pkill", "-9", "ocamllsp"])


def check_and_maybe_kill() -> bool:
    count = count_ocamllsp()
    if count > 1:
        logger.info("Saw %d ocamllsp processes, killing them now", count)
        kill_ocamllsp()
        return True
    return False


def run_check_and_kill_loop(
    sleep_interval_s: float = 0.5,
    sleep_interval_after_kill_s: float = 10.0, 
) -> None:
    while True:
        if check_and_maybe_kill():
            # potentially sleep longer after a kill (if we kill too many times too fast,
            # eventually Visual Studio Code will turn off the extension; backing off a bit
            # helps).
            logger.info("Sleeping %f seconds", sleep_interval_after_kill_s)
            time.sleep(sleep_interval_after_kill_s)
        else:
            logger.info("Sleeping %f seconds", sleep_interval_s)
            time.sleep(sleep_interval_s)


if __name__ == "__main__":
    run_check_and_kill_loop()
