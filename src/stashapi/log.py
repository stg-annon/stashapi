# Log messages are transmitted via stderr and are
# encoded with a prefix consisting of special character SOH, then the log
# level (one of t, d, i, w, e - corresponding to trace, debug, info,
# warning and error levels respectively), then special character
# STX.
#
# The trace, debug, info, warning, and error methods, and their equivalent
# formatted methods are intended for use by script scraper instances to transmit log
# messages.

import re, sys, json

import logging
from functools import partial, partialmethod

logging.TRACE = 5  # low order python logging level
logging.addLevelName(logging.TRACE, "TRACE")
logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)
logging.trace = partial(logging.log, logging.TRACE)

logging.PROGRESS = 50 # high order python logging level
logging.addLevelName(logging.PROGRESS, "PROGRESS")
logging.Logger.progress = partialmethod(logging.Logger.log, logging.PROGRESS)
logging.progress = partial(logging.log, logging.PROGRESS)

STASH_LOG_LEVEL_MAP = {
	logging.TRACE:   "t",
	logging.DEBUG:   "d",
	logging.INFO:    "i",
	logging.WARNING: "w",
	logging.ERROR:   "e",
	logging.PROGRESS:"p",
}

# Regex to replace data blobs from logging
DATA_BLOB_REGEX = re.compile(r"[\'|\"]data:.+/.*;base64,(?P<content>.*?)[\'|\"]")
# Max size of golang buf - level bytes and newline, theoretical max (64 * 1024) - 4  
LOG_PAYLOAD_MAX_SZ = 64000

def truncate_base64_replacement(match_group):
	return match_group.group(0).replace(
		match_group.group(1), f"<BASE64_DATA({len(match_group.group(1))})>"
	)

class StashLogHandler(logging.Handler):
	"""Python std logging handler that outputs to stash log over stderr
	LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
	logging.basicConfig(format="%(name)s| %(message)s", handlers=[StashLogHandler()], level=LOG_LEVEL)
	"""

	def __init__(self, stream=sys.stderr) -> None:
		self.stream = stream
		super().__init__()

	def emit(self, record) -> None:
		if self.stream != sys.stderr and record.levelno == logging.PROGRESS:
			return
		msg = self.format(record)
		msg = DATA_BLOB_REGEX.sub(truncate_base64_replacement, msg)
		for line in msg.split("\n"):
			self.stream.write(f"\x01{STASH_LOG_LEVEL_MAP.get(record.levelno, 0)}\x02{line[:LOG_PAYLOAD_MAX_SZ]}\n")
			self.stream.flush()

def serialize(s):
	if isinstance(s, dict):
		s = json.dumps(s)
	# attempt to cast any non string value to a string
	if not isinstance(s, str):
		s = str(s)
	return s

# module import backwards compatibility i.e. (import stashapi.log as log)
DISABLE_PROGRESS = False
sl = logging.getLogger('StashLogger')
sl.setLevel(logging.DEBUG)
sl.addHandler(StashLogHandler())

def trace(s):
	sl.trace(serialize(s))
def debug(s):
	sl.debug(serialize(s))
def info(s):
	sl.info(serialize(s))
def warning(s):
	sl.warning(serialize(s))
def error(s):
	sl.error(serialize(s))
def progress(p):
	if DISABLE_PROGRESS:
		return
	progress = min(max(0, p), 1)
	sl.progress(progress)
def exit(msg=None, err=None):
	if msg is None and err is None:
		msg = "ok"
	print(json.dumps({
		"output": msg,
		"error": err
	}))
	sys.exit()
def result(data=None):
	"""used to return data to stash from a scraper"""
	if data:
		print(json.dumps(data))
	else:
		print("null")
	sys.exit()