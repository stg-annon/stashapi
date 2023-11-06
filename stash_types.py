from enum import Enum, IntEnum

class StashEnum(Enum):
	def __repr__(self) -> str:
		return f"{self.__class__.__name__}.{self.name}"
	def __str__(self) -> str:
		return self.value
	def serialize(self):
		return self.value

class StashItem(StashEnum):
	SCENE = "SCENE"
	GALLERY = "GALLERY"
	PERFORMER = "PERFORMER"
	MOVIE = "MOVIE"

class PhashDistance(StashEnum):
	EXACT = 0
	HIGH = 4
	MEDIUM = 8
	LOW = 10
