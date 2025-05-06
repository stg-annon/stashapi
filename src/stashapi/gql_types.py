from enum import StrEnum
from typing import Literal, NotRequired, Required, Self, TypeAlias, TypedDict

from stashapi.classes import JSON


class GQLSetFingerprintsInput(TypedDict):
    type: str
    value: NotRequired[str]


class GQLMoveFilesInput(TypedDict):
    ids: list[int]
    destination_folder: NotRequired[str]
    destination_folder_id: NotRequired[int]
    destination_basename: NotRequired[str]


class GQLTagCreateInput(TypedDict, total=False):
    name: Required[str]
    sort_name: str
    description: str
    aliases: list[str]
    ignore_auto_tag: bool
    favorite: bool
    image: str
    parent_ids: list[int]
    child_ids: list[int]


class GQLTagUpdateInput(TypedDict, total=False):
    id: Required[int]
    name: str
    sort_name: str
    description: str
    aliases: list[str]
    ignore_auto_tag: bool
    favorite: bool
    image: str
    parent_ids: list[int]
    child_ids: list[int]


class GQLCriterionModifier(StrEnum):
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


CriterionModifierType: TypeAlias = (
    GQLCriterionModifier
    | Literal[
        "EQUALS",
        "NOT_EQUALS",
        "GREATER_THAN",
        "LESS_THAN",
        "IS_NULL",
        "NOT_NULL",
        "INCLUDES_ALL",
        "INCLUDES",
        "EXCLUDES",
        "MATCHES_REGEX",
        "NOT_MATCHES_REGEX",
        "BETWEEN",
        "NOT_BETWEEN",
    ]
)


class GQLCircumisedEnum(StrEnum):
    CUT = "CUT"
    UNCUT = "UNCUT"


CircumsisedEnumType: TypeAlias = (
    GQLCircumisedEnum
    | Literal[
        "CUT",
        "UNCUT",
    ]
)


class GQLGenderEnum(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    TRANSGENDER_MALE = "TRANSGENDER_MALE"
    TRANSGENDER_FEMALE = "TRANSGENDER_FEMALE"
    INTERSEX = "INTERSEX"
    NON_BINARY = "NON_BINARY"


GenderEnumType: TypeAlias = (
    GQLGenderEnum
    | Literal[
        "MALE",
        "FEMALE",
        "TRANSGENDER_MALE",
        "TRANSGENDER_FEMALE",
        "INTERSEX",
        "NON_BINARY",
    ]
)


class GQLResolutionEnum(StrEnum):
    VERY_LOW = "VERY_LOW"  # 144p
    LOW = "LOW"  # 240p
    R360P = "R360P"  # 360p
    STANDARD = "STANDARD"  # 480p
    WEB_HD = "WEB_HD"  # 540p
    STANDARD_HD = "STANDARD_HD"  # 720p
    FULL_HD = "FULL_HD"  # 1080p
    QUAD_HD = "QUAD_HD"  # 1440p
    FOUR_K = "FOUR_K"  # 4K
    FIVE_K = "FIVE_K"  # 5K
    SIX_K = "SIX_K"  # 6K
    SEVEN_K = "SEVEN_K"  # 7K
    EIGHT_K = "EIGHT_K"  # 8K
    HUGE = "HUGE"  # 8K+


ResolutionEnumType: TypeAlias = (
    GQLResolutionEnum
    | Literal[
        "VERY_LOW",
        "LOW",
        "R360P",
        "STANDARD",
        "WEB_HD",
        "STANDARD_HD",
        "FULL_HD",
        "QUAD_HD",
        "FOUR_K",
        "FIVE_K",
        "SIX_K",
        "SEVEN_K",
        "EIGHT_K",
        "HUGE",
    ]
)


class GQLStringCriterionInput(TypedDict):
    value: str
    modifier: CriterionModifierType


class GQLMultiCriterionInput(TypedDict):
    value: NotRequired[list[int]]
    modifier: CriterionModifierType
    excludes: NotRequired[list[int]]


class GQLStashIDCriterionInput(TypedDict):
    # If present, this value is treated as a predicate.
    # That is, it will filter based on stash_ids with the matching endpoint
    endpoint: NotRequired[str]

    stash_id: str
    modifier: NotRequired[CriterionModifierType]


class GQLHierarchicalMultiCriterionInput(TypedDict):
    value: NotRequired[list[int]]
    modifier: CriterionModifierType
    depth: NotRequired[int]
    excludes: NotRequired[list[int]]


class GQLFloatCriterionInput(TypedDict):
    value: float
    value2: NotRequired[float]
    modifier: CriterionModifierType


class GQLIntCriterionInput(TypedDict):
    value: int
    value2: NotRequired[int]
    modifier: CriterionModifierType


class GQLTimestampCriterionInput(TypedDict):
    value: str
    value2: NotRequired[str]
    modifier: CriterionModifierType


class GQLDateCriterionInput(TypedDict):
    value: str
    value2: NotRequired[str]
    modifier: CriterionModifierType


class GQLCircumcisionCriterionInput(TypedDict):
    value: NotRequired[list[CircumsisedEnumType]]
    modifier: CriterionModifierType


class GQLGenderCriterionInput(TypedDict):
    value: GenderEnumType
    value_list: NotRequired[list[GenderEnumType]]
    modifier: CriterionModifierType


class GQLCustomFieldCriterionInput(TypedDict):
    field: str
    value: NotRequired[list[JSON]]
    modifier: CriterionModifierType


class GQLPhashDistanceCriterionInput(TypedDict):
    value: str
    modifier: CriterionModifierType
    distance: NotRequired[int]


class GQLPHashDuplicationCriterionInput(TypedDict, total=False):
    duplicated: bool
    distance: int


class GQLResolutionCriterionInput(TypedDict):
    value: ResolutionEnumType
    modifier: CriterionModifierType


class GQLOrientationEnum(StrEnum):
    LANDSCAPE = "LANDSCAPE"
    PORTRAIT = "PORTRAIT"
    SQUARE = "SQUARE"


class GQLOrientationCriterionInput(TypedDict):
    value: list[GQLOrientationEnum]


class GQLSortDirectionEnum(StrEnum):
    ASC = "ASC"
    DESC = "DESC"


class GQLBulkUpdateIdMode(StrEnum):
    SET = "SET"
    ADD = "ADD"
    REMOVE = "REMOVE"


BulkUpdateIdModeType: TypeAlias = (
    GQLBulkUpdateIdMode
    | Literal[
        "SET",
        "ADD",
        "REMOVE",
    ]
)


class GQLBulkUpdateStrings(TypedDict):
    values: list[str]
    mode: Required[BulkUpdateIdModeType]


class GQLBulkUpdateIds(TypedDict):
    ids: list[int]
    mode: Required[BulkUpdateIdModeType]


class GQLCustomFieldsInput(TypedDict, total=False):
    # If populated, the entire custom fields map will be replaced with this value
    full: dict[str, JSON]

    # If populated, only the keys in this map will be updated
    partial: dict[str, JSON]


class GQLFindFilterType(TypedDict, total=False):
    q: str
    page: int

    # use per_page = -1 to indicate all results. Defaults to 25.
    per_page: int

    sort: str
    direction: GQLSortDirectionEnum


class GQLMovieFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    name: GQLStringCriterionInput
    director: GQLStringCriterionInput
    synopsis: GQLStringCriterionInput
    duration: GQLIntCriterionInput
    rating100: GQLIntCriterionInput
    studios: GQLHierarchicalMultiCriterionInput
    is_missing: str
    url: GQLStringCriterionInput
    performers: GQLMultiCriterionInput
    tags: GQLHierarchicalMultiCriterionInput
    tag_count: GQLIntCriterionInput
    date: GQLDateCriterionInput
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    scenes_filter: "GQLSceneFilterType"
    studios_filter: "GQLStudioFilterType"


class GQLGroupFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    name: GQLStringCriterionInput
    director: GQLStringCriterionInput
    synopsis: GQLStringCriterionInput
    duration: GQLIntCriterionInput
    rating100: GQLIntCriterionInput
    studios: GQLHierarchicalMultiCriterionInput
    is_missing: str
    url: GQLStringCriterionInput
    performers: GQLMultiCriterionInput
    tags: GQLHierarchicalMultiCriterionInput
    tag_count: GQLIntCriterionInput
    date: GQLDateCriterionInput
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    containing_groups: GQLHierarchicalMultiCriterionInput
    sub_groups: GQLHierarchicalMultiCriterionInput
    containing_group_count: GQLIntCriterionInput
    sub_group_count: GQLIntCriterionInput
    scenes_filter: "GQLSceneFilterType"
    studios_filter: "GQLStudioFilterType"


class GQLTagFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    name: GQLStringCriterionInput
    sort_name: GQLStringCriterionInput
    aliases: GQLStringCriterionInput
    favorite: bool
    description: GQLStringCriterionInput
    is_missing: str
    scene_count: GQLIntCriterionInput
    image_count: GQLIntCriterionInput
    gallery_count: GQLIntCriterionInput
    performer_count: GQLIntCriterionInput
    studio_count: GQLIntCriterionInput
    movie_count: GQLIntCriterionInput
    group_count: GQLIntCriterionInput
    marker_count: GQLIntCriterionInput
    parents: GQLHierarchicalMultiCriterionInput
    children: GQLHierarchicalMultiCriterionInput
    parent_count: GQLIntCriterionInput
    child_count: GQLIntCriterionInput
    ignore_auto_tag: bool
    scenes_filter: "GQLSceneFilterType"
    images_filter: "GQLImageFilterType"
    galleries_filter: "GQLGalleryFilterType"
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput


class GQLPerformerFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    name: GQLStringCriterionInput
    disambiguation: GQLStringCriterionInput
    details: GQLStringCriterionInput
    filter_favorites: bool
    birth_year: GQLIntCriterionInput
    age: GQLIntCriterionInput
    ethnicity: GQLStringCriterionInput
    country: GQLStringCriterionInput
    eye_color: GQLStringCriterionInput
    height_cm: GQLIntCriterionInput
    measurements: GQLStringCriterionInput
    fake_tits: GQLStringCriterionInput
    penis_length: GQLFloatCriterionInput
    circumcised: GQLCircumcisionCriterionInput
    career_length: GQLStringCriterionInput
    tattoos: GQLStringCriterionInput
    piercings: GQLStringCriterionInput
    aliases: GQLStringCriterionInput
    gender: GQLGenderCriterionInput
    is_missing: str
    tags: GQLHierarchicalMultiCriterionInput
    tag_count: GQLIntCriterionInput
    scene_count: GQLIntCriterionInput
    image_count: GQLIntCriterionInput
    gallery_count: GQLIntCriterionInput
    play_count: GQLIntCriterionInput
    o_counter: GQLIntCriterionInput
    stash_id_endpoint: GQLStashIDCriterionInput
    rating100: GQLIntCriterionInput
    url: GQLStringCriterionInput
    hair_color: GQLStringCriterionInput
    weight: GQLIntCriterionInput
    death_year: GQLIntCriterionInput
    studios: GQLHierarchicalMultiCriterionInput
    performers: GQLMultiCriterionInput
    ignore_auto_tag: bool
    birthdate: GQLDateCriterionInput
    death_date: GQLDateCriterionInput
    scenes_filter: "GQLSceneFilterType"
    images_filter: "GQLImageFilterType"
    galleries_filter: "GQLGalleryFilterType"
    tags_filter: GQLTagFilterType
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    custom_fields: list[GQLCustomFieldCriterionInput]


class GQLSceneMarkerFilterType(TypedDict, total=False):
    tags: GQLHierarchicalMultiCriterionInput
    scene_tags: GQLHierarchicalMultiCriterionInput
    performers: GQLMultiCriterionInput
    scenes: GQLMultiCriterionInput
    duration: GQLFloatCriterionInput
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    scene_date: GQLDateCriterionInput
    scene_created_at: GQLTimestampCriterionInput
    scene_updated_at: GQLTimestampCriterionInput
    scene_filter: "GQLSceneFilterType"


class GQLSceneFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    id: GQLIntCriterionInput
    title: GQLStringCriterionInput
    code: GQLStringCriterionInput
    details: GQLStringCriterionInput
    director: GQLStringCriterionInput
    oshash: GQLStringCriterionInput
    checksum: GQLStringCriterionInput
    phash: GQLStringCriterionInput
    phash_distance: GQLPhashDistanceCriterionInput
    path: GQLStringCriterionInput
    file_count: GQLIntCriterionInput
    rating100: GQLIntCriterionInput
    organized: bool
    o_counter: GQLIntCriterionInput
    duplicated: GQLPHashDuplicationCriterionInput
    resolution: GQLResolutionCriterionInput
    orientation: GQLOrientationCriterionInput
    framerate: GQLIntCriterionInput
    bitrate: GQLIntCriterionInput
    video_codec: GQLStringCriterionInput
    audio_codec: GQLStringCriterionInput
    duration: GQLIntCriterionInput
    has_markers: str
    is_missing: str
    studios: GQLHierarchicalMultiCriterionInput
    movies: GQLMultiCriterionInput
    groups: GQLHierarchicalMultiCriterionInput
    galleries: GQLMultiCriterionInput
    tags: GQLHierarchicalMultiCriterionInput
    tag_count: GQLIntCriterionInput
    performer_tags: GQLHierarchicalMultiCriterionInput
    performer_favorite: bool
    performer_age: GQLIntCriterionInput
    performers: GQLMultiCriterionInput
    performer_count: GQLIntCriterionInput
    stash_id_endpoint: GQLStashIDCriterionInput
    url: GQLStringCriterionInput
    interactive: bool
    interactive_speed: GQLIntCriterionInput
    captions: GQLStringCriterionInput
    resume_time: GQLIntCriterionInput
    play_count: GQLIntCriterionInput
    play_duration: GQLIntCriterionInput
    last_played_at: GQLTimestampCriterionInput
    date: GQLDateCriterionInput
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    galleries_filter: "GQLGalleryFilterType"
    performers_filter: GQLPerformerFilterType
    studios_filter: "GQLStudioFilterType"
    tags_filter: GQLTagFilterType
    movies_filter: GQLMovieFilterType
    groups_filter: GQLGroupFilterType
    markers_filter: GQLSceneMarkerFilterType


class GQLImageFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    title: GQLStringCriterionInput
    details: GQLStringCriterionInput
    id: GQLIntCriterionInput
    checksum: GQLStringCriterionInput
    path: GQLStringCriterionInput
    file_count: GQLIntCriterionInput
    rating100: GQLIntCriterionInput
    date: GQLDateCriterionInput
    url: GQLStringCriterionInput
    organized: bool
    o_counter: GQLIntCriterionInput
    resolution: GQLResolutionCriterionInput
    orientation: GQLOrientationCriterionInput
    is_missing: str
    studios: GQLHierarchicalMultiCriterionInput
    tags: GQLHierarchicalMultiCriterionInput
    tag_count: GQLIntCriterionInput
    performer_tags: GQLHierarchicalMultiCriterionInput
    performers: GQLMultiCriterionInput
    performer_count: GQLIntCriterionInput
    performer_favorite: bool
    performer_age: GQLIntCriterionInput
    galleries: GQLMultiCriterionInput
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    code: GQLStringCriterionInput
    photographer: GQLStringCriterionInput
    galleries_filter: "GQLGalleryFilterType"
    performers_filter: GQLPerformerFilterType
    studios_filter: "GQLStudioFilterType"
    tags_filter: GQLTagFilterType


class GQLStudioFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    name: GQLStringCriterionInput
    details: GQLStringCriterionInput
    parents: GQLMultiCriterionInput
    stash_id_endpoint: GQLStashIDCriterionInput
    tags: GQLHierarchicalMultiCriterionInput
    is_missing: str
    rating100: GQLIntCriterionInput
    favorite: bool
    scene_count: GQLIntCriterionInput
    image_count: GQLIntCriterionInput
    gallery_count: GQLIntCriterionInput
    tag_count: GQLIntCriterionInput
    url: GQLStringCriterionInput
    aliases: GQLStringCriterionInput
    child_count: GQLIntCriterionInput
    ignore_auto_tag: bool
    scenes_filter: GQLSceneFilterType
    images_filter: GQLImageFilterType
    galleries_filter: "GQLGalleryFilterType"
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput


class GQLGalleryFilterType(TypedDict, total=False):
    AND: Self
    OR: Self
    NOT: Self
    id: GQLIntCriterionInput
    title: GQLStringCriterionInput
    details: GQLStringCriterionInput
    checksum: GQLStringCriterionInput
    path: GQLStringCriterionInput
    file_count: GQLIntCriterionInput
    is_missing: str
    is_zip: bool
    rating100: GQLIntCriterionInput
    organized: bool
    average_resolution: GQLResolutionCriterionInput
    has_chapters: str
    scenes: GQLMultiCriterionInput
    studios: GQLHierarchicalMultiCriterionInput
    tags: GQLHierarchicalMultiCriterionInput
    tag_count: GQLIntCriterionInput
    performer_tags: GQLHierarchicalMultiCriterionInput
    performers: GQLMultiCriterionInput
    performer_count: GQLIntCriterionInput
    performer_favorite: bool
    performer_age: GQLIntCriterionInput
    image_count: GQLIntCriterionInput
    url: GQLStringCriterionInput
    date: GQLDateCriterionInput
    created_at: GQLTimestampCriterionInput
    updated_at: GQLTimestampCriterionInput
    code: GQLStringCriterionInput
    photographer: GQLStringCriterionInput
    scenes_filter: GQLSceneFilterType
    images_filter: GQLImageFilterType
    performers_filter: GQLPerformerFilterType
    studios_filter: GQLStudioFilterType
    tags_filter: GQLTagFilterType


class GQLStashIDInput(TypedDict):
    endpoint: str
    stash_id: str
    updated_at: NotRequired[str]


class GQLStudioCreateInput(TypedDict):
    name: str
    url: NotRequired[str]
    parent_id: NotRequired[int]
    image: NotRequired[str]
    stash_ids: NotRequired[list[GQLStashIDInput]]
    rating100: NotRequired[int]
    favorite: NotRequired[bool]
    details: NotRequired[str]
    aliases: NotRequired[list[str]]
    tag_ids: NotRequired[list[int]]
    ignore_auto_tag: NotRequired[bool]


class GQLStudioUpdateInput(TypedDict, total=False):
    id: Required[int]
    name: str
    url: str
    parent_id: int
    image: str
    stash_ids: list[GQLStashIDInput]
    rating100: int
    favorite: bool
    details: str
    aliases: list[str]
    tag_ids: list[int]
    ignore_auto_tag: bool


class GQLPerformerCreateInput(TypedDict, total=False):
    name: Required[str]
    disambiguation: str
    url: str
    urls: list[str]
    gender: GenderEnumType
    birthdate: str
    ethnicity: str
    country: str
    eye_color: str
    height_cm: int
    measurements: str
    fake_tits: str
    penis_length: float
    circumcised: CircumsisedEnumType
    career_length: str
    tattoos: str
    piercings: str
    alias_list: list[str]
    twitter: str
    instagram: str
    favorite: bool
    tag_ids: list[int]
    image: str
    stash_ids: list[GQLStashIDInput]
    rating100: int
    details: str
    death_date: str
    hair_color: str
    weight: int
    ignore_auto_tag: bool
    custom_fields: dict[str, JSON]


class GQLPerformerUpdateInput(TypedDict, total=False):
    clientMutationId: str
    ids: list[int]
    disambiguation: str
    url: str
    urls: GQLBulkUpdateStrings
    gender: GenderEnumType
    birthdate: str
    ethnicity: str
    country: str
    eye_color: str
    height_cm: int
    measurements: str
    fake_tits: str
    penis_length: float
    circumcised: CircumsisedEnumType
    career_length: str
    tattoos: str
    piercings: str
    alias_list: GQLBulkUpdateStrings
    twitter: str
    instagram: str
    favorite: bool
    tag_ids: GQLBulkUpdateIds
    rating100: int
    details: str
    death_date: str
    hair_color: str
    weight: int
    ignore_auto_tag: bool
    custom_fields: GQLCustomFieldsInput


class GQLBulkPerformerUpdateInput(TypedDict, total=False):
    clientMutationId: str
    ids: list[int]
    disambiguation: str
    url: str
    urls: GQLBulkUpdateStrings
    gender: GenderEnumType
    birthdate: str
    ethnicity: str
    country: str
    eye_color: str
    height_cm: int
    measurements: str
    fake_tits: str
    penis_length: float
    circumcised: CircumsisedEnumType
    career_length: str
    tattoos: str
    piercings: str
    alias_list: GQLBulkUpdateStrings
    twitter: str
    instagram: str
    favorite: bool
    tag_ids: GQLBulkUpdateIds
    rating100: int
    details: str
    death_date: str
    hair_color: str
    weight: int
    ignore_auto_tag: bool
    custom_fields: GQLCustomFieldsInput


class GQLGroupDescriptionInput(TypedDict):
    group_id: int
    description: NotRequired[str]


class GQLGroupCreateInput(TypedDict, total=False):
    name: Required[str]
    aliases: str
    duration: int
    date: str
    rating100: int
    studio_id: int
    director: str
    synopsis: str
    urls: list[str]
    tag_ids: list[int]
    containing_groups: list[GQLGroupDescriptionInput]
    sub_groups: list[GQLGroupDescriptionInput]
    front_image: str
    back_image: str


class GQLGroupUpdateInput(TypedDict, total=False):
    id: Required[int]
    name: str
    aliases: str
    duration: int
    date: str
    rating100: int
    studio_id: int
    director: str
    synopsis: str
    urls: list[str]
    tag_ids: list[int]
    containing_groups: list[GQLGroupDescriptionInput]
    sub_groups: list[GQLGroupDescriptionInput]
    front_image: str
    back_image: str


class GQLGalleryCreateInput(TypedDict, total=False):
    title: Required[str]
    code: str
    url: str
    urls: list[str]
    date: str
    details: str
    photographer: str
    rating100: int
    organized: bool
    scene_ids: list[int]
    studio_id: int
    tag_ids: list[int]
    performer_ids: list[int]


class GQLGalleryUpdateInput(TypedDict, total=False):
    clientMutationId: str
    id: Required[int]
    title: str
    code: str
    url: str
    urls: list[str]
    date: str
    details: str
    photographer: str
    rating100: int
    organized: bool
    scene_ids: list[int]
    studio_id: int
    tag_ids: list[int]
    performer_ids: list[int]
    primary_file_id: int


class GQLGalleryChapterCreateInput(TypedDict):
    gallery_id: int
    title: str
    image_index: int


class GQLGalleryChapterUpdateInput(TypedDict, total=False):
    id: Required[int]
    gallery_id: int
    title: str
    image_index: int


class GQLBulkGalleryUpdateInput(TypedDict, total=False):
    clientMutationId: str
    ids: list[int]
    code: str
    url: str
    urls: GQLBulkUpdateStrings
    date: str
    details: str
    photographer: str
    rating100: int
    organized: bool
    scene_ids: GQLBulkUpdateIds
    studio_id: int
    tag_ids: GQLBulkUpdateIds
    performer_ids: GQLBulkUpdateIds


class GQLImageUpdateInput(TypedDict, total=False):
    clientMutationId: str
    id: Required[int]
    title: str
    code: str
    rating100: int
    organized: bool
    url: str
    urls: list[str]
    date: str
    details: str
    photographer: str
    studio_id: int
    performer_ids: list[int]
    tag_ids: list[int]
    gallery_ids: list[int]
    primary_file_id: int


class GQLBulkImageUpdateInput(TypedDict, total=False):
    clientMutationId: str
    ids: list[int]
    title: str
    code: str
    rating100: int
    organized: bool
    url: str
    urls: GQLBulkUpdateStrings
    date: str
    details: str
    photographer: str
    studio_id: int
    performer_ids: GQLBulkUpdateIds
    tag_ids: GQLBulkUpdateIds
    gallery_ids: GQLBulkUpdateIds


class GQLSceneGroupInput(TypedDict):
    group_id: int
    scene_index: NotRequired[int]


class GQLSceneMovieInput(TypedDict):
    movie_id: int
    scene_index: NotRequired[int]


class GQLSceneCreateInput(TypedDict, total=False):
    title: str
    code: str
    details: str
    director: str
    url: str
    urls: list[str]
    date: str
    rating100: int
    organized: bool
    studio_id: int
    gallery_ids: list[int]
    performer_ids: list[int]
    groups: list[GQLSceneGroupInput]
    movies: list[GQLSceneMovieInput]
    tag_ids: list[int]
    cover_image: str

    stash_ids: list[GQLStashIDInput]
    file_ids: list[int]


class GQLSceneHashInput(TypedDict, total=False):
    checksum: str
    oshash: str


class GQLSceneUpdateInput(TypedDict, total=False):
    clientMutationId: str
    id: Required[int]
    title: str
    code: str
    details: str
    director: str
    url: str
    urls: list[str]
    date: str
    rating100: int
    o_counter: int
    organized: bool
    studio_id: int
    gallery_ids: list[int]
    performer_ids: list[int]
    groups: list[GQLSceneGroupInput]
    movies: list[GQLSceneMovieInput]
    tag_ids: list[int]
    cover_image: str
    stash_ids: list[GQLStashIDInput]
    resume_time: float
    play_duration: float
    play_count: int
    primary_file_id: int


class GQLBulkSceneUpdateInput(TypedDict, total=False):
    clientMutationId: str
    ids: list[int]
    title: str
    code: str
    details: str
    director: str
    url: str
    urls: GQLBulkUpdateStrings
    date: str
    rating100: int
    organized: bool
    studio_id: int
    gallery_ids: GQLBulkUpdateIds
    performer_ids: GQLBulkUpdateIds
    tag_ids: GQLBulkUpdateIds
    group_ids: GQLBulkUpdateIds
    movie_ids: GQLBulkUpdateIds
