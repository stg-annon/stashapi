"""
Log messages are transmitted via stderr and are
encoded with a prefix consisting of special character SOH, then the log
level (one of t, d, i, w, e - corresponding to trace, debug, info,
warning and error levels respectively), then special character
STX.

The trace, debug, info, warning, and error methods, and their equivalent
formatted methods are intended for use by script scraper instances to transmit log
messages.
"""

from functools import partial, partialmethod
import json
import logging
import os
import re
import sys
from typing import Callable, TextIO
from typing_extensions import override


TRACE = 5  # logging.TRACE will be available, but pyright doesn't like it
setattr(logging, "TRACE", TRACE)  # low order python logging level
logging.addLevelName(TRACE, "TRACE")
setattr(logging.Logger, "trace", partialmethod(logging.Logger.log, TRACE))
setattr(logging, "trace", partial(logging.log, TRACE))

#  PROGRESS used to be 50, but 50 is already used for CRITICAL. Switch to 60 (below), but keep
#  supporting 50 internally. It doesn't actually affect the contents of the output
_OLD_PROGRESS = 50

PROGRESS = 60  # logging.PROGRESS will be available, but pyright doesn't like it
setattr(logging, "PROGRESS", PROGRESS)  # high order python logging level
logging.addLevelName(PROGRESS, "PROGRESS")
setattr(logging.Logger, "progress", partialmethod(logging.Logger.log, PROGRESS))
setattr(logging, "progress", partial(logging.log, PROGRESS))

STASH_LOG_LEVEL_MAP = {
    TRACE: "t",
    logging.DEBUG: "d",
    logging.INFO: "i",
    logging.WARNING: "w",
    logging.ERROR: "e",
    PROGRESS: "p",
}

# Regex to replace data blobs from logging
DATA_BLOB_REGEX = re.compile(r"[\'|\"]data:.+/.*;base64,(?P<content>.*?)[\'|\"]")

# Max size of golang buf - level bytes and newline, theoretical max (64 * 1024) - 4
LOG_PAYLOAD_MAX_SZ = 64000


def truncate_base64_replacement(match_group: re.Match[str]):
    return match_group.group(0).replace(match_group.group(1), f"<BASE64_DATA({len(match_group.group(1))})>")


class StashLogHandler(logging.Handler):
    """Python std logging handler that outputs to stash log over stderr
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
    logging.basicConfig(format="%(name)s| %(message)s", handlers=[StashLogHandler()], level=LOG_LEVEL)
    """

    def __init__(self, stream: TextIO = sys.stderr) -> None:
        super().__init__()
        self.stream: TextIO = stream

    @override
    def emit(self, record: logging.LogRecord) -> None:
        if self.stream != sys.stderr and record.levelno >= _OLD_PROGRESS:
            return

        msg = self.format(record)
        msg = DATA_BLOB_REGEX.sub(truncate_base64_replacement, msg)
        for line in msg.split("\n"):
            _ = self.stream.write(f"\x01{STASH_LOG_LEVEL_MAP.get(record.levelno, 0)}\x02{line[:LOG_PAYLOAD_MAX_SZ]}\n")
            self.stream.flush()


def serialize(s: object) -> str:
    if isinstance(s, str):
        return s
    elif isinstance(s, dict):
        return json.dumps(s)
    else:
        # attempt to cast any non string value to a string
        return str(s)


# module import backwards compatibility i.e. (import stashapi.log as log)
DISABLE_PROGRESS = False
sl = logging.getLogger("StashLogger")
sl.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))
sl.addHandler(StashLogHandler())


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger with the given name, or "StashLogger" if the name is omitted

    This logger can be used identically to the more traditional `import stashapi.log as log`,
    but gives you a `logging.Logger` object to work with instead of a Module("stashapi.log") object

    Args:
        name (str, optional): The name to call `logging.getLogger` with
    """

    name = name or "StashLogger"
    sl = logging.getLogger(name)
    sl.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))
    sl.addHandler(StashLogHandler())
    return sl


def trace(s: object):
    func: Callable[[object], None] = getattr(sl, "trace")
    func(serialize(s))


def debug(s: object):
    sl.debug(serialize(s))


def info(s: object):
    sl.info(serialize(s))


def warning(s: object):
    sl.warning(serialize(s))


def error(s: object):
    sl.error(serialize(s))


def progress(p: float):
    """
    Inform stash of the program's progress.

    Params:
      p (float): current progress from 0.0 to 1.0 (will be saturated)
    """
    if DISABLE_PROGRESS:
        return
    progress = min(max(0.0, p), 1.0)
    func: Callable[[object], None] = getattr(sl, "progress")
    func(progress)


def exit(msg: object | None = None, err: object | None = None):
    """
    Write the given `msg` and `err` to stdout and terminate the program.
    """
    if msg is None and err is None:
        msg = "ok"
    print(json.dumps({"output": msg, "error": err}))
    sys.exit()


def result(data: object | None = None):
    """
    Write the given data to stdout and terminate the program.
    Example use: return data to stash from a scraper
    """
    if data:
        print(json.dumps(data))
    else:
        print("null")
    sys.exit()
