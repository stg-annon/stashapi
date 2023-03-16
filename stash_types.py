from enum import Enum, IntEnum

class StashEnum(Enum):
	def __repr__(self) -> str:
		return f"{self.__class__.__name__}.{self.name}"
	def __str__(self) -> str:
		return self.value

class BulkUpdateIdMode(StashEnum):
	SET = "SET"
	ADD = "ADD"
	REMOVE = "REMOVE"

class ScrapeType(StashEnum):
	NAME = "NAME"
	FRAGMENT = "FRAGMENT"
	URL = "URL"

class ScrapeContentType(StashEnum):
	GALLERY = "GALLERY"
	MOVIE = "MOVIE"
	PERFORMER = "PERFORMER"
	SCENE = "SCENE"


class StashItem(StashEnum):
	SCENE = "SCENE"
	GALLERY = "GALLERY"
	PERFORMER = "PERFORMER"
	MOVIE = "MOVIE"

class Gender(StashEnum):
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
