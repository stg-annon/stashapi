from enum import Enum, IntEnum

class BulkUpdateIdMode(Enum):
	SET = "SET"
	ADD = "ADD"
	REMOVE = "REMOVE"

class ScrapeType(Enum):
	NAME = "NAME"
	FRAGMENT = "FRAGMENT"
	URL = "URL"

class StashItem(Enum):
	SCENE = "SCENE"
	GALLERY = "GALLERY"
	PERFORMER = "PERFORMER"
	MOVIE = "MOVIE"

class Gender(Enum):
	MALE="MALE"
	FEMALE="FEMALE"
	TRANSGENDER_MALE="TRANSGENDER_MALE"
	TRANSGENDER_FEMALE="TRANSGENDER_FEMALE"
	INTERSEX="INTERSEX"
	NON_BINARY="NON_BINARY"

class PhashDistance(IntEnum):
	EXACT = 0
	HIGH = 4
	MEDIUM = 8
	LOW = 10
