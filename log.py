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
class StashLogLevel(Enum):
	DEFAULT     = 0
	TRACE       = 1
	DEBUG       = 2
	INFO        = 3
	WARNING     = 4
	ERROR       = 5
	DISABLED    = 6
	def __lt__(self, other):
		return self.value < other.value
# level can be set to disable lower level logs
LEVEL = StashLogLevel.DEFAULT
# disables logging progress bar, indented for use when running in console to avoid spam
DISABLE_PROGRESS = False

class StashLogger:

	def __init__(self, log_level:StashLogLevel=StashLogLevel.DEFAULT, disable_progress_bar:bool=False) -> None:

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
		s = re.sub(r'data:image.+?;base64(.+?")','<b64img>"',str(s))

		for line in s.split("\n"):
			print(level_char, line, file=sys.stderr, flush=True)

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
		if self.DISABLE_PROGRESS:
			return
		if self.LEVEL == StashLogLevel.DISABLED:
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
		
	def result(self, data):
		"""used to return data to stash from a scraper"""
		if data:
			print(json.dumps(data))
		else:
			print("null")
		sys.exit()


def __log(level_char: bytes, s):
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
	s = re.sub(r'data:image.+?;base64(.+?")','<b64img>"',str(s))

	for line in s.split("\n"):
		print(level_char, line, file=sys.stderr, flush=True)

def trace(s):
	if StashLogLevel.TRACE < LEVEL:
		return
	__log(b't', s)

def debug(s):
	if StashLogLevel.DEBUG < LEVEL:
		return
	__log(b'd', s)

def info(s):
	if StashLogLevel.INFO < LEVEL:
		return
	__log(b'i', s)

def warning(s):
	if StashLogLevel.WARNING < LEVEL:
		return
	__log(b'w', s)

def error(s):
	if StashLogLevel.ERROR < LEVEL:
		return
	__log(b'e', s)

def progress(p):
	if DISABLE_PROGRESS:
		return
	if StashLogLevel.DISABLED == LEVEL:
		return
	progress = min(max(0, p), 1)
	__log(b'p', str(progress))

def exit(msg=None, err=None):
	if msg is None and err is None:
		msg = "ok"
	print(json.dumps({
		"output": msg,
		"error": err
	}))
	sys.exit()
	
def result(data):
	"""used to return data to stash from a scraper"""
	if data:
		print(json.dumps(data))
	else:
		print("null")
	sys.exit()