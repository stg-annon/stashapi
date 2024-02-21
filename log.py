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
from enum import Enum

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

class StashLogLevel(Enum):
	NOTSET      = 0
	TRACE       = 1
	DEBUG       = 2
	INFO        = 3
	WARNING     = 4
	ERROR       = 5
	PROGRESS    = 6
	DISABLED    = 500
	def __lt__(self, other):
		return self.value < other.value
# Regex to replace data blobs from logging
DATA_BLOB_REGEX = re.compile(r"[\'|\"]data:.+/.*;base64,(?P<content>.*?)[\'|\"]")
# Max size of golang buf - level bytes and newline
LOG_PAYLOAD_MAX_SZ = (64 * 1024) - 4  

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

class StashLogger:

	def __init__(self, log_level:StashLogLevel=StashLogLevel.INFO,disable_progress_bar:bool=False) -> None:
		""" creates instance of StashLogger

		Args:
			log_level (StashLogLevel, optional): log level setting. Defaults to StashLogLevel.INFO.
			disable_progress_bar (bool, optional): disables logging progress bar, indented for use when running in console to avoid spam. Defaults to False.
		"""		

		self.DISABLE_PROGRESS = disable_progress_bar
		self.LEVEL = log_level

	def __log(self, level_char: bytes, s):
		if not level_char:
			return
		level_char = f"\x01{level_char.decode()}\x02"

		# convert dicts to json string
		if isinstance(s, dict):
			s = json.dumps(s)
		# attempt to cast any non string value to a string
		if not isinstance(s, str):
			s = str(s)

		# truncate any base64 data before logging
		s = DATA_BLOB_REGEX.sub(truncate_base64_replacement, s)

		for line in s.split("\n"):
			print(level_char, line[:LOG_PAYLOAD_MAX_SZ], file=sys.stderr, flush=True)

	def trace(self, s):
		if StashLogLevel.TRACE < self.LEVEL:
			return
		self.__log(b't', s)

	def debug(self, s):
		if StashLogLevel.DEBUG < self.LEVEL:
			return
		self.__log(b'd', s)

	def info(self, s):
		if StashLogLevel.INFO < self.LEVEL:
			return
		self.__log(b'i', s)

	def warning(self, s):
		if StashLogLevel.WARNING < self.LEVEL:
			return
		self.__log(b'w', s)

	def error(self, s):
		if StashLogLevel.ERROR < self.LEVEL:
			return
		self.__log(b'e', s)

	def progress(self, p):
		if self.DISABLE_PROGRESS or self.LEVEL == StashLogLevel.DISABLED:
			return
		progress = min(max(0, p), 1)
		self.__log(b'p', str(progress))

	def exit(self, msg=None, err=None):
		if msg is None and err is None:
			msg = "ok"
		print(json.dumps({
			"output": msg,
			"error": err
		}))
		sys.exit()
		
	def result(self, data=None):
		"""used to return data to stash from a scraper"""
		if data:
			print(json.dumps(data))
		else:
			print("null")
		sys.exit()

# module import backwards compatibility i.e. (import stashapi.log as log) 
sl = StashLogger(log_level=StashLogLevel.NOTSET)
def trace(s):
	sl.trace(s)
def debug(s):
	sl.debug(s)
def info(s):
	sl.info(s)
def warning(s):
	sl.warning(s)
def error(s):
	sl.error(s)
def progress(p):
	sl.progress(p)
def exit(msg=None, err=None):
	sl.exit(msg,err)
def result(data=None):
	sl.result(data)