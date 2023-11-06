from enum import Enum, IntEnum

class StashEnum(Enum):
	def __repr__(self) -> str:
		return f"{self.__class__.__name__}.{self.name}"
	def __str__(self) -> str:
		return self.value
	def serialize(self):
		return self.value

class CriterionModifier(StashEnum):
	EQUALS = "EQUALS"
	NOT_EQUALS = "NOT_EQUALS"
	GREATER_THAN = "GREATER_THAN"
	LESS_THAN = "LESS_THAN"
	IS_NULL = "IS_NULL"
	NOT_NULL = "NOT_NULL"
	INCLUDES_ALL = "INCLUDES_ALL"
	INCLUDES = "INCLUDES"
	EXCLUDES = "EXCLUDES"
	MATCHES_REGEX = "MATCHES_REGEX"
	NOT_MATCHES_REGEX = "NOT_MATCHES_REGEX"
	BETWEEN = "BETWEEN"
	NOT_BETWEEN = "NOT_BETWEEN"

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
	MALE = "MALE"
	FEMALE = "FEMALE"
	TRANSGENDER_MALE = "TRANSGENDER_MALE"
	TRANSGENDER_FEMALE = "TRANSGENDER_FEMALE"
	INTERSEX = "INTERSEX"
	NON_BINARY = "NON_BINARY"

class PhashDistance(StashEnum):
	EXACT = 0
	HIGH = 4
	MEDIUM = 8
	LOW = 10

class OnMultipleMatch(Enum):
	RETURN_NONE = 0
	RETURN_LIST = 1
	RETURN_FIRST = 2