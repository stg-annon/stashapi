from enum import IntEnum, StrEnum


class CriterionModifier(StrEnum):
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


class BulkUpdateIdMode(StrEnum):
    SET = "SET"
    ADD = "ADD"
    REMOVE = "REMOVE"


class ScrapeType(StrEnum):
    NAME = "NAME"
    FRAGMENT = "FRAGMENT"
    URL = "URL"


class ScrapeContentType(StrEnum):
    GALLERY = "GALLERY"
    MOVIE = "MOVIE"
    PERFORMER = "PERFORMER"
    SCENE = "SCENE"
    IMAGE = "IMAGE"


class StashItem(StrEnum):
    SCENE = "SCENE"
    GALLERY = "GALLERY"
    PERFORMER = "PERFORMER"
    MOVIE = "MOVIE"
    IMAGE = "IMAGE"


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    TRANSGENDER_MALE = "TRANSGENDER_MALE"
    TRANSGENDER_FEMALE = "TRANSGENDER_FEMALE"
    INTERSEX = "INTERSEX"
    NON_BINARY = "NON_BINARY"


class PhashDistance(IntEnum):
    EXACT = 0
    HIGH = 4
    MEDIUM = 8
    LOW = 10


class OnMultipleMatch(IntEnum):
    RETURN_NONE = 0
    RETURN_LIST = 1
    RETURN_FIRST = 2


class CallbackReturns(IntEnum):
    STOP_ITERATION = 0
