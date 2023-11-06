from pydantic import BaseModel
from enum import Enum
from typing import Optional, List

class BlobsStorageType(str, Enum):
    DATABASE = 'DATABASE'
    'Database'
    FILESYSTEM = 'FILESYSTEM'
    'Filesystem'

class BulkUpdateIdMode(str, Enum):
    SET = 'SET'
    ADD = 'ADD'
    REMOVE = 'REMOVE'

class CircumisedEnum(str, Enum):
    CUT = 'CUT'
    UNCUT = 'UNCUT'

class CriterionModifier(str, Enum):
    EQUALS = 'EQUALS'
    '='
    NOT_EQUALS = 'NOT_EQUALS'
    '!='
    GREATER_THAN = 'GREATER_THAN'
    '>'
    LESS_THAN = 'LESS_THAN'
    '<'
    IS_NULL = 'IS_NULL'
    'IS NULL'
    NOT_NULL = 'NOT_NULL'
    'IS NOT NULL'
    INCLUDES_ALL = 'INCLUDES_ALL'
    'INCLUDES ALL'
    INCLUDES = 'INCLUDES'
    EXCLUDES = 'EXCLUDES'
    MATCHES_REGEX = 'MATCHES_REGEX'
    'MATCHES REGEX'
    NOT_MATCHES_REGEX = 'NOT_MATCHES_REGEX'
    'NOT MATCHES REGEX'
    BETWEEN = 'BETWEEN'
    '>= AND <='
    NOT_BETWEEN = 'NOT_BETWEEN'
    '< OR >'

class FilterMode(str, Enum):
    SCENES = 'SCENES'
    PERFORMERS = 'PERFORMERS'
    STUDIOS = 'STUDIOS'
    GALLERIES = 'GALLERIES'
    SCENE_MARKERS = 'SCENE_MARKERS'
    MOVIES = 'MOVIES'
    TAGS = 'TAGS'
    IMAGES = 'IMAGES'

class GenderEnum(str, Enum):
    MALE = 'MALE'
    FEMALE = 'FEMALE'
    TRANSGENDER_MALE = 'TRANSGENDER_MALE'
    TRANSGENDER_FEMALE = 'TRANSGENDER_FEMALE'
    INTERSEX = 'INTERSEX'
    NON_BINARY = 'NON_BINARY'

class HashAlgorithm(str, Enum):
    MD5 = 'MD5'
    OSHASH = 'OSHASH'
    'oshash'

class IdentifyFieldStrategy(str, Enum):
    IGNORE = 'IGNORE'
    'Never sets the field value'
    MERGE = 'MERGE'
    'For multi-value fields, merge with existing.\nFor single-value fields, ignore if already set'
    OVERWRITE = 'OVERWRITE'
    'Always replaces the value if a value is found.\nFor multi-value fields, any existing values are removed and replaced with the\nscraped values.'

class ImageLightboxDisplayMode(str, Enum):
    ORIGINAL = 'ORIGINAL'
    FIT_XY = 'FIT_XY'
    FIT_X = 'FIT_X'

class ImageLightboxScrollMode(str, Enum):
    ZOOM = 'ZOOM'
    PAN_Y = 'PAN_Y'

class ImportDuplicateEnum(str, Enum):
    IGNORE = 'IGNORE'
    OVERWRITE = 'OVERWRITE'
    FAIL = 'FAIL'

class ImportMissingRefEnum(str, Enum):
    IGNORE = 'IGNORE'
    FAIL = 'FAIL'
    CREATE = 'CREATE'

class JobStatus(str, Enum):
    READY = 'READY'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    STOPPING = 'STOPPING'
    CANCELLED = 'CANCELLED'

class JobStatusUpdateType(str, Enum):
    ADD = 'ADD'
    REMOVE = 'REMOVE'
    UPDATE = 'UPDATE'

class LogLevel(str, Enum):
    Trace = 'Trace'
    Debug = 'Debug'
    Info = 'Info'
    Progress = 'Progress'
    Warning = 'Warning'
    Error = 'Error'

class PluginSettingTypeEnum(str, Enum):
    STRING = 'STRING'
    NUMBER = 'NUMBER'
    BOOLEAN = 'BOOLEAN'

class PreviewPreset(str, Enum):
    ultrafast = 'ultrafast'
    'X264_ULTRAFAST'
    veryfast = 'veryfast'
    'X264_VERYFAST'
    fast = 'fast'
    'X264_FAST'
    medium = 'medium'
    'X264_MEDIUM'
    slow = 'slow'
    'X264_SLOW'
    slower = 'slower'
    'X264_SLOWER'
    veryslow = 'veryslow'
    'X264_VERYSLOW'

class ResolutionEnum(str, Enum):
    VERY_LOW = 'VERY_LOW'
    '144p'
    LOW = 'LOW'
    '240p'
    R360P = 'R360P'
    '360p'
    STANDARD = 'STANDARD'
    '480p'
    WEB_HD = 'WEB_HD'
    '540p'
    STANDARD_HD = 'STANDARD_HD'
    '720p'
    FULL_HD = 'FULL_HD'
    '1080p'
    QUAD_HD = 'QUAD_HD'
    '1440p'
    VR_HD = 'VR_HD'
    'DEPRECATED: 1920p'
    FOUR_K = 'FOUR_K'
    '4K'
    FIVE_K = 'FIVE_K'
    '5K'
    SIX_K = 'SIX_K'
    '6K'
    SEVEN_K = 'SEVEN_K'
    '7K'
    EIGHT_K = 'EIGHT_K'
    '8K'
    HUGE = 'HUGE'
    '8K+'

class ScrapeContentType(str, Enum):
    """Type of the content a scraper generates"""
    GALLERY = 'GALLERY'
    MOVIE = 'MOVIE'
    PERFORMER = 'PERFORMER'
    SCENE = 'SCENE'

class ScrapeType(str, Enum):
    NAME = 'NAME'
    'From text query'
    FRAGMENT = 'FRAGMENT'
    'From existing object'
    URL = 'URL'
    'From URL'

class SortDirectionEnum(str, Enum):
    ASC = 'ASC'
    DESC = 'DESC'

class StreamingResolutionEnum(str, Enum):
    LOW = 'LOW'
    '240p'
    STANDARD = 'STANDARD'
    '480p'
    STANDARD_HD = 'STANDARD_HD'
    '720p'
    FULL_HD = 'FULL_HD'
    '1080p'
    FOUR_K = 'FOUR_K'
    '4k'
    ORIGINAL = 'ORIGINAL'
    'Original'

class SystemStatusEnum(str, Enum):
    SETUP = 'SETUP'
    NEEDS_MIGRATION = 'NEEDS_MIGRATION'
    OK = 'OK'

class AddTempDLNAIPInput(BaseModel):
    address: str
    duration: Optional[int]
    'Duration to enable, in minutes. 0 or null for indefinite.'

class AnonymiseDatabaseInput(BaseModel):
    download: Optional[bool]

class AssignSceneFileInput(BaseModel):
    scene_id: str
    file_id: str

class AutoTagMetadataInput(BaseModel):
    paths: Optional[List[str]]
    'Paths to tag, null for all files'
    performers: Optional[List[str]]
    'IDs of performers to tag files with, or "*" for all'
    studios: Optional[List[str]]
    'IDs of studios to tag files with, or "*" for all'
    tags: Optional[List[str]]
    'IDs of tags to tag files with, or "*" for all'

class BackupDatabaseInput(BaseModel):
    download: Optional[bool]

class BulkGalleryUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    ids: Optional[List[str]]
    url: Optional[str]
    urls: Optional['BulkUpdateStrings']
    date: Optional[str]
    details: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    scene_ids: Optional['BulkUpdateIds']
    studio_id: Optional[str]
    tag_ids: Optional['BulkUpdateIds']
    performer_ids: Optional['BulkUpdateIds']

class BulkImageUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    ids: Optional[List[str]]
    title: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    url: Optional[str]
    urls: Optional['BulkUpdateStrings']
    date: Optional[str]
    studio_id: Optional[str]
    performer_ids: Optional['BulkUpdateIds']
    tag_ids: Optional['BulkUpdateIds']
    gallery_ids: Optional['BulkUpdateIds']

class BulkMovieUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    ids: Optional[List[str]]
    rating100: Optional[int]
    studio_id: Optional[str]
    director: Optional[str]

class BulkPerformerUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    ids: Optional[List[str]]
    disambiguation: Optional[str]
    url: Optional[str]
    gender: Optional[GenderEnum]
    birthdate: Optional[str]
    ethnicity: Optional[str]
    country: Optional[str]
    eye_color: Optional[str]
    height_cm: Optional[int]
    measurements: Optional[str]
    fake_tits: Optional[str]
    penis_length: Optional[float]
    circumcised: Optional[CircumisedEnum]
    career_length: Optional[str]
    tattoos: Optional[str]
    piercings: Optional[str]
    alias_list: Optional['BulkUpdateStrings']
    twitter: Optional[str]
    instagram: Optional[str]
    favorite: Optional[bool]
    tag_ids: Optional['BulkUpdateIds']
    rating100: Optional[int]
    details: Optional[str]
    death_date: Optional[str]
    hair_color: Optional[str]
    weight: Optional[int]
    ignore_auto_tag: Optional[bool]

class BulkSceneUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    ids: Optional[List[str]]
    title: Optional[str]
    code: Optional[str]
    details: Optional[str]
    director: Optional[str]
    url: Optional[str]
    urls: Optional['BulkUpdateStrings']
    date: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    studio_id: Optional[str]
    gallery_ids: Optional['BulkUpdateIds']
    performer_ids: Optional['BulkUpdateIds']
    tag_ids: Optional['BulkUpdateIds']
    movie_ids: Optional['BulkUpdateIds']

class BulkUpdateIds(BaseModel):
    ids: Optional[List[str]]
    mode: BulkUpdateIdMode

class BulkUpdateStrings(BaseModel):
    values: Optional[List[str]]
    mode: BulkUpdateIdMode

class CircumcisionCriterionInput(BaseModel):
    value: Optional[List[CircumisedEnum]]
    modifier: CriterionModifier

class CleanMetadataInput(BaseModel):
    paths: Optional[List[str]]
    dryRun: bool
    "Do a dry run. Don't delete any files"

class ConfigDLNAInput(BaseModel):
    serverName: Optional[str]
    enabled: Optional[bool]
    'True if DLNA service should be enabled by default'
    whitelistedIPs: Optional[List[str]]
    'List of IPs whitelisted for DLNA service'
    interfaces: Optional[List[str]]
    'List of interfaces to run DLNA on. Empty for all'
    videoSortOrder: Optional[str]
    'Order to sort videos'

class ConfigDefaultSettingsInput(BaseModel):
    scan: Optional['ScanMetadataInput']
    identify: Optional['IdentifyMetadataInput']
    autoTag: Optional[AutoTagMetadataInput]
    generate: Optional['GenerateMetadataInput']
    deleteFile: Optional[bool]
    'If true, delete file checkbox will be checked by default'
    deleteGenerated: Optional[bool]
    'If true, delete generated files checkbox will be checked by default'

class ConfigDisableDropdownCreateInput(BaseModel):
    performer: Optional[bool]
    tag: Optional[bool]
    studio: Optional[bool]
    movie: Optional[bool]

class ConfigGeneralInput(BaseModel):
    stashes: Optional[List['StashConfigInput']]
    'Array of file paths to content'
    databasePath: Optional[str]
    'Path to the SQLite database'
    backupDirectoryPath: Optional[str]
    'Path to backup directory'
    generatedPath: Optional[str]
    'Path to generated files'
    metadataPath: Optional[str]
    'Path to import/export files'
    scrapersPath: Optional[str]
    'Path to scrapers'
    cachePath: Optional[str]
    'Path to cache'
    blobsPath: Optional[str]
    'Path to blobs - required for filesystem blob storage'
    blobsStorage: Optional[BlobsStorageType]
    'Where to store blobs'
    calculateMD5: Optional[bool]
    'Whether to calculate MD5 checksums for scene video files'
    videoFileNamingAlgorithm: Optional[HashAlgorithm]
    'Hash algorithm to use for generated file naming'
    parallelTasks: Optional[int]
    'Number of parallel tasks to start during scan/generate'
    previewAudio: Optional[bool]
    'Include audio stream in previews'
    previewSegments: Optional[int]
    'Number of segments in a preview file'
    previewSegmentDuration: Optional[float]
    'Preview segment duration, in seconds'
    previewExcludeStart: Optional[str]
    'Duration of start of video to exclude when generating previews'
    previewExcludeEnd: Optional[str]
    'Duration of end of video to exclude when generating previews'
    previewPreset: Optional[PreviewPreset]
    'Preset when generating preview'
    transcodeHardwareAcceleration: Optional[bool]
    'Transcode Hardware Acceleration'
    maxTranscodeSize: Optional[StreamingResolutionEnum]
    'Max generated transcode size'
    maxStreamingTranscodeSize: Optional[StreamingResolutionEnum]
    'Max streaming transcode size'
    transcodeInputArgs: Optional[List[str]]
    'ffmpeg transcode input args - injected before input file\nThese are applied to generated transcodes (previews and transcodes)'
    transcodeOutputArgs: Optional[List[str]]
    'ffmpeg transcode output args - injected before output file\nThese are applied to generated transcodes (previews and transcodes)'
    liveTranscodeInputArgs: Optional[List[str]]
    'ffmpeg stream input args - injected before input file\nThese are applied when live transcoding'
    liveTranscodeOutputArgs: Optional[List[str]]
    'ffmpeg stream output args - injected before output file\nThese are applied when live transcoding'
    drawFunscriptHeatmapRange: Optional[bool]
    'whether to include range in generated funscript heatmaps'
    writeImageThumbnails: Optional[bool]
    'Write image thumbnails to disk when generating on the fly'
    createImageClipsFromVideos: Optional[bool]
    'Create Image Clips from Video extensions when Videos are disabled in Library'
    username: Optional[str]
    'Username'
    password: Optional[str]
    'Password'
    maxSessionAge: Optional[int]
    'Maximum session cookie age'
    logFile: Optional[str]
    'Name of the log file'
    logOut: Optional[bool]
    'Whether to also output to stderr'
    logLevel: Optional[str]
    'Minimum log level'
    logAccess: Optional[bool]
    'Whether to log http access'
    createGalleriesFromFolders: Optional[bool]
    'True if galleries should be created from folders with images'
    galleryCoverRegex: Optional[str]
    'Regex used to identify images as gallery covers'
    videoExtensions: Optional[List[str]]
    'Array of video file extensions'
    imageExtensions: Optional[List[str]]
    'Array of image file extensions'
    galleryExtensions: Optional[List[str]]
    'Array of gallery zip file extensions'
    excludes: Optional[List[str]]
    'Array of file regexp to exclude from Video Scans'
    imageExcludes: Optional[List[str]]
    'Array of file regexp to exclude from Image Scans'
    customPerformerImageLocation: Optional[str]
    'Custom Performer Image Location'
    stashBoxes: Optional[List['StashBoxInput']]
    'Stash-box instances used for tagging'
    pythonPath: Optional[str]
    'Python path - resolved using path if unset'

class ConfigImageLightboxInput(BaseModel):
    slideshowDelay: Optional[int]
    displayMode: Optional[ImageLightboxDisplayMode]
    scaleUp: Optional[bool]
    resetZoomOnNav: Optional[bool]
    scrollMode: Optional[ImageLightboxScrollMode]
    scrollAttemptsBeforeChange: Optional[int]

class ConfigInterfaceInput(BaseModel):
    menuItems: Optional[List[str]]
    'Ordered list of items that should be shown in the menu'
    soundOnPreview: Optional[bool]
    'Enable sound on mouseover previews'
    wallShowTitle: Optional[bool]
    'Show title and tags in wall view'
    wallPlayback: Optional[str]
    'Wall playback type'
    showScrubber: Optional[bool]
    'Show scene scrubber by default'
    maximumLoopDuration: Optional[int]
    'Maximum duration (in seconds) in which a scene video will loop in the scene player'
    autostartVideo: Optional[bool]
    'If true, video will autostart on load in the scene player'
    autostartVideoOnPlaySelected: Optional[bool]
    'If true, video will autostart when loading from play random or play selected'
    continuePlaylistDefault: Optional[bool]
    'If true, next scene in playlist will be played at video end by default'
    showStudioAsText: Optional[bool]
    'If true, studio overlays will be shown as text instead of logo images'
    css: Optional[str]
    'Custom CSS'
    cssEnabled: Optional[bool]
    javascript: Optional[str]
    'Custom Javascript'
    javascriptEnabled: Optional[bool]
    customLocales: Optional[str]
    'Custom Locales'
    customLocalesEnabled: Optional[bool]
    language: Optional[str]
    'Interface language'
    imageLightbox: Optional[ConfigImageLightboxInput]
    disableDropdownCreate: Optional[ConfigDisableDropdownCreateInput]
    'Set to true to disable creating new objects via the dropdown menus'
    handyKey: Optional[str]
    'Handy Connection Key'
    funscriptOffset: Optional[int]
    'Funscript Time Offset'
    useStashHostedFunscript: Optional[bool]
    'Whether to use Stash Hosted Funscript'
    noBrowser: Optional[bool]
    'True if we should not auto-open a browser window on startup'
    notificationsEnabled: Optional[bool]
    'True if we should send notifications to the desktop'

class ConfigScrapingInput(BaseModel):
    scraperUserAgent: Optional[str]
    'Scraper user agent string'
    scraperCDPPath: Optional[str]
    'Scraper CDP path. Path to chrome executable or remote address'
    scraperCertCheck: Optional[bool]
    'Whether the scraper should check for invalid certificates'
    excludeTagPatterns: Optional[List[str]]
    'Tags blacklist during scraping'

class DateCriterionInput(BaseModel):
    value: str
    value2: Optional[str]
    modifier: CriterionModifier

class DestroyFilterInput(BaseModel):
    id: str

class DisableDLNAInput(BaseModel):
    duration: Optional[int]
    'Duration to enable, in minutes. 0 or null for indefinite.'

class EnableDLNAInput(BaseModel):
    duration: Optional[int]
    'Duration to enable, in minutes. 0 or null for indefinite.'

class ExportObjectTypeInput(BaseModel):
    ids: Optional[List[str]]
    all: Optional[bool]

class ExportObjectsInput(BaseModel):
    scenes: Optional[ExportObjectTypeInput]
    images: Optional[ExportObjectTypeInput]
    studios: Optional[ExportObjectTypeInput]
    performers: Optional[ExportObjectTypeInput]
    tags: Optional[ExportObjectTypeInput]
    movies: Optional[ExportObjectTypeInput]
    galleries: Optional[ExportObjectTypeInput]
    includeDependencies: Optional[bool]

class FindFilterType(BaseModel):
    q: Optional[str]
    page: Optional[int]
    per_page: Optional[int]
    'use per_page = -1 to indicate all results. Defaults to 25.'
    sort: Optional[str]
    direction: Optional[SortDirectionEnum]

class FindJobInput(BaseModel):
    id: str

class FloatCriterionInput(BaseModel):
    value: float
    value2: Optional[float]
    modifier: CriterionModifier

class GalleryAddInput(BaseModel):
    gallery_id: str
    image_ids: List[str]

class GalleryChapterCreateInput(BaseModel):
    gallery_id: str
    title: str
    image_index: int

class GalleryChapterUpdateInput(BaseModel):
    id: str
    gallery_id: Optional[str]
    title: Optional[str]
    image_index: Optional[int]

class GalleryCreateInput(BaseModel):
    title: str
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]
    details: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    scene_ids: Optional[List[str]]
    studio_id: Optional[str]
    tag_ids: Optional[List[str]]
    performer_ids: Optional[List[str]]

class GalleryDestroyInput(BaseModel):
    ids: List[str]
    delete_file: Optional[bool]
    'If true, then the zip file will be deleted if the gallery is zip-file-based.\nIf gallery is folder-based, then any files not associated with other\ngalleries will be deleted, along with the folder, if it is not empty.'
    delete_generated: Optional[bool]

class GalleryFilterType(BaseModel):
    AND: Optional['GalleryFilterType']
    OR: Optional['GalleryFilterType']
    NOT: Optional['GalleryFilterType']
    id: Optional['IntCriterionInput']
    title: Optional['StringCriterionInput']
    details: Optional['StringCriterionInput']
    checksum: Optional['StringCriterionInput']
    'Filter by file checksum'
    path: Optional['StringCriterionInput']
    'Filter by path'
    file_count: Optional['IntCriterionInput']
    'Filter by zip-file count'
    is_missing: Optional[str]
    'Filter to only include galleries missing this property'
    is_zip: Optional[bool]
    'Filter to include/exclude galleries that were created from zip'
    rating100: Optional['IntCriterionInput']
    organized: Optional[bool]
    'Filter by organized'
    average_resolution: Optional['ResolutionCriterionInput']
    'Filter by average image resolution'
    has_chapters: Optional[str]
    'Filter to only include galleries that have chapters. `true` or `false`'
    studios: Optional['HierarchicalMultiCriterionInput']
    'Filter to only include galleries with this studio'
    tags: Optional['HierarchicalMultiCriterionInput']
    'Filter to only include galleries with these tags'
    tag_count: Optional['IntCriterionInput']
    'Filter by tag count'
    performer_tags: Optional['HierarchicalMultiCriterionInput']
    'Filter to only include galleries with performers with these tags'
    performers: Optional['MultiCriterionInput']
    'Filter to only include galleries with these performers'
    performer_count: Optional['IntCriterionInput']
    'Filter by performer count'
    performer_favorite: Optional[bool]
    'Filter galleries that have performers that have been favorited'
    performer_age: Optional['IntCriterionInput']
    'Filter galleries by performer age at time of gallery'
    image_count: Optional['IntCriterionInput']
    'Filter by number of images in this gallery'
    url: Optional['StringCriterionInput']
    'Filter by url'
    date: Optional[DateCriterionInput]
    'Filter by date'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class GalleryRemoveInput(BaseModel):
    gallery_id: str
    image_ids: List[str]

class GalleryUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    id: str
    title: Optional[str]
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]
    details: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    scene_ids: Optional[List[str]]
    studio_id: Optional[str]
    tag_ids: Optional[List[str]]
    performer_ids: Optional[List[str]]
    primary_file_id: Optional[str]

class GenderCriterionInput(BaseModel):
    value: Optional[GenderEnum]
    modifier: CriterionModifier

class GenerateAPIKeyInput(BaseModel):
    clear: Optional[bool]

class GenerateMetadataInput(BaseModel):
    covers: Optional[bool]
    sprites: Optional[bool]
    previews: Optional[bool]
    imagePreviews: Optional[bool]
    previewOptions: Optional['GeneratePreviewOptionsInput']
    markers: Optional[bool]
    markerImagePreviews: Optional[bool]
    markerScreenshots: Optional[bool]
    transcodes: Optional[bool]
    forceTranscodes: Optional[bool]
    'Generate transcodes even if not required'
    phashes: Optional[bool]
    interactiveHeatmapsSpeeds: Optional[bool]
    clipPreviews: Optional[bool]
    sceneIDs: Optional[List[str]]
    'scene ids to generate for'
    markerIDs: Optional[List[str]]
    'marker ids to generate for'
    overwrite: Optional[bool]
    'overwrite existing media'

class GeneratePreviewOptionsInput(BaseModel):
    previewSegments: Optional[int]
    'Number of segments in a preview file'
    previewSegmentDuration: Optional[float]
    'Preview segment duration, in seconds'
    previewExcludeStart: Optional[str]
    'Duration of start of video to exclude when generating previews'
    previewExcludeEnd: Optional[str]
    'Duration of end of video to exclude when generating previews'
    previewPreset: Optional[PreviewPreset]
    'Preset when generating preview'

class HierarchicalMultiCriterionInput(BaseModel):
    value: Optional[List[str]]
    modifier: CriterionModifier
    depth: Optional[int]
    excludes: Optional[List[str]]

class IdentifyFieldOptionsInput(BaseModel):
    field: str
    strategy: IdentifyFieldStrategy
    createMissing: Optional[bool]
    'creates missing objects if needed - only applicable for performers, tags and studios'

class IdentifyMetadataInput(BaseModel):
    sources: List['IdentifySourceInput']
    'An ordered list of sources to identify items with. Only the first source that finds a match is used.'
    options: Optional['IdentifyMetadataOptionsInput']
    'Options defined here override the configured defaults'
    sceneIDs: Optional[List[str]]
    'scene ids to identify'
    paths: Optional[List[str]]
    'paths of scenes to identify - ignored if scene ids are set'

class IdentifyMetadataOptionsInput(BaseModel):
    fieldOptions: Optional[List[IdentifyFieldOptionsInput]]
    'any fields missing from here are defaulted to MERGE and createMissing false'
    setCoverImage: Optional[bool]
    'defaults to true if not provided'
    setOrganized: Optional[bool]
    includeMalePerformers: Optional[bool]
    'defaults to true if not provided'
    skipMultipleMatches: Optional[bool]
    'defaults to true if not provided'
    skipMultipleMatchTag: Optional[str]
    'tag to tag skipped multiple matches with'
    skipSingleNamePerformers: Optional[bool]
    'defaults to true if not provided'
    skipSingleNamePerformerTag: Optional[str]
    'tag to tag skipped single name performers with'

class IdentifySourceInput(BaseModel):
    source: 'ScraperSourceInput'
    options: Optional[IdentifyMetadataOptionsInput]
    'Options defined for a source override the defaults'

class ImageDestroyInput(BaseModel):
    id: str
    delete_file: Optional[bool]
    delete_generated: Optional[bool]

class ImageFilterType(BaseModel):
    AND: Optional['ImageFilterType']
    OR: Optional['ImageFilterType']
    NOT: Optional['ImageFilterType']
    title: Optional['StringCriterionInput']
    id: Optional['IntCriterionInput']
    ' Filter by image id'
    checksum: Optional['StringCriterionInput']
    'Filter by file checksum'
    path: Optional['StringCriterionInput']
    'Filter by path'
    file_count: Optional['IntCriterionInput']
    'Filter by file count'
    rating100: Optional['IntCriterionInput']
    date: Optional[DateCriterionInput]
    'Filter by date'
    url: Optional['StringCriterionInput']
    'Filter by url'
    organized: Optional[bool]
    'Filter by organized'
    o_counter: Optional['IntCriterionInput']
    'Filter by o-counter'
    resolution: Optional['ResolutionCriterionInput']
    'Filter by resolution'
    is_missing: Optional[str]
    'Filter to only include images missing this property'
    studios: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include images with this studio'
    tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include images with these tags'
    tag_count: Optional['IntCriterionInput']
    'Filter by tag count'
    performer_tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include images with performers with these tags'
    performers: Optional['MultiCriterionInput']
    'Filter to only include images with these performers'
    performer_count: Optional['IntCriterionInput']
    'Filter by performer count'
    performer_favorite: Optional[bool]
    'Filter images that have performers that have been favorited'
    galleries: Optional['MultiCriterionInput']
    'Filter to only include images with these galleries'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class ImageUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    id: str
    title: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]
    studio_id: Optional[str]
    performer_ids: Optional[List[str]]
    tag_ids: Optional[List[str]]
    gallery_ids: Optional[List[str]]
    primary_file_id: Optional[str]

class ImagesDestroyInput(BaseModel):
    ids: List[str]
    delete_file: Optional[bool]
    delete_generated: Optional[bool]

class ImportObjectsInput(BaseModel):
    file: str
    duplicateBehaviour: ImportDuplicateEnum
    missingRefBehaviour: ImportMissingRefEnum

class IntCriterionInput(BaseModel):
    value: int
    value2: Optional[int]
    modifier: CriterionModifier

class MigrateBlobsInput(BaseModel):
    deleteOld: Optional[bool]

class MigrateInput(BaseModel):
    backupPath: str

class MigrateSceneScreenshotsInput(BaseModel):
    deleteFiles: Optional[bool]
    overwriteExisting: Optional[bool]

class MoveFilesInput(BaseModel):
    ids: List[str]
    destination_folder: Optional[str]
    'valid for single or multiple file ids'
    destination_folder_id: Optional[str]
    'valid for single or multiple file ids'
    destination_basename: Optional[str]
    'valid only for single file id. If empty, existing basename is used'

class MovieCreateInput(BaseModel):
    name: str
    aliases: Optional[str]
    duration: Optional[int]
    'Duration in seconds'
    date: Optional[str]
    rating100: Optional[int]
    studio_id: Optional[str]
    director: Optional[str]
    synopsis: Optional[str]
    url: Optional[str]
    front_image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    back_image: Optional[str]
    'This should be a URL or a base64 encoded data URL'

class MovieDestroyInput(BaseModel):
    id: str

class MovieFilterType(BaseModel):
    name: Optional['StringCriterionInput']
    director: Optional['StringCriterionInput']
    synopsis: Optional['StringCriterionInput']
    duration: Optional[IntCriterionInput]
    'Filter by duration (in seconds)'
    rating100: Optional[IntCriterionInput]
    studios: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include movies with this studio'
    is_missing: Optional[str]
    'Filter to only include movies missing this property'
    url: Optional['StringCriterionInput']
    'Filter by url'
    performers: Optional['MultiCriterionInput']
    'Filter to only include movies where performer appears in a scene'
    date: Optional[DateCriterionInput]
    'Filter by date'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class MovieUpdateInput(BaseModel):
    id: str
    name: Optional[str]
    aliases: Optional[str]
    duration: Optional[int]
    date: Optional[str]
    rating100: Optional[int]
    studio_id: Optional[str]
    director: Optional[str]
    synopsis: Optional[str]
    url: Optional[str]
    front_image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    back_image: Optional[str]
    'This should be a URL or a base64 encoded data URL'

class MultiCriterionInput(BaseModel):
    value: Optional[List[str]]
    modifier: CriterionModifier
    excludes: Optional[List[str]]

class PHashDuplicationCriterionInput(BaseModel):
    duplicated: Optional[bool]
    distance: Optional[int]
    'Currently unimplemented'

class PerformerCreateInput(BaseModel):
    name: str
    disambiguation: Optional[str]
    url: Optional[str]
    gender: Optional[GenderEnum]
    birthdate: Optional[str]
    ethnicity: Optional[str]
    country: Optional[str]
    eye_color: Optional[str]
    height_cm: Optional[int]
    measurements: Optional[str]
    fake_tits: Optional[str]
    penis_length: Optional[float]
    circumcised: Optional[CircumisedEnum]
    career_length: Optional[str]
    tattoos: Optional[str]
    piercings: Optional[str]
    alias_list: Optional[List[str]]
    twitter: Optional[str]
    instagram: Optional[str]
    favorite: Optional[bool]
    tag_ids: Optional[List[str]]
    image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    stash_ids: Optional[List['StashIDInput']]
    rating100: Optional[int]
    details: Optional[str]
    death_date: Optional[str]
    hair_color: Optional[str]
    weight: Optional[int]
    ignore_auto_tag: Optional[bool]

class PerformerDestroyInput(BaseModel):
    id: str

class PerformerFilterType(BaseModel):
    AND: Optional['PerformerFilterType']
    OR: Optional['PerformerFilterType']
    NOT: Optional['PerformerFilterType']
    name: Optional['StringCriterionInput']
    disambiguation: Optional['StringCriterionInput']
    details: Optional['StringCriterionInput']
    filter_favorites: Optional[bool]
    'Filter by favorite'
    birth_year: Optional[IntCriterionInput]
    'Filter by birth year'
    age: Optional[IntCriterionInput]
    'Filter by age'
    ethnicity: Optional['StringCriterionInput']
    'Filter by ethnicity'
    country: Optional['StringCriterionInput']
    'Filter by country'
    eye_color: Optional['StringCriterionInput']
    'Filter by eye color'
    height_cm: Optional[IntCriterionInput]
    'Filter by height in cm'
    measurements: Optional['StringCriterionInput']
    'Filter by measurements'
    fake_tits: Optional['StringCriterionInput']
    'Filter by fake tits value'
    penis_length: Optional[FloatCriterionInput]
    'Filter by penis length value'
    circumcised: Optional[CircumcisionCriterionInput]
    'Filter by ciricumcision'
    career_length: Optional['StringCriterionInput']
    'Filter by career length'
    tattoos: Optional['StringCriterionInput']
    'Filter by tattoos'
    piercings: Optional['StringCriterionInput']
    'Filter by piercings'
    aliases: Optional['StringCriterionInput']
    'Filter by aliases'
    gender: Optional[GenderCriterionInput]
    'Filter by gender'
    is_missing: Optional[str]
    'Filter to only include performers missing this property'
    tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include performers with these tags'
    tag_count: Optional[IntCriterionInput]
    'Filter by tag count'
    scene_count: Optional[IntCriterionInput]
    'Filter by scene count'
    image_count: Optional[IntCriterionInput]
    'Filter by image count'
    gallery_count: Optional[IntCriterionInput]
    'Filter by gallery count'
    o_counter: Optional[IntCriterionInput]
    'Filter by o count'
    stash_id_endpoint: Optional['StashIDCriterionInput']
    'Filter by StashID'
    rating100: Optional[IntCriterionInput]
    url: Optional['StringCriterionInput']
    'Filter by url'
    hair_color: Optional['StringCriterionInput']
    'Filter by hair color'
    weight: Optional[IntCriterionInput]
    'Filter by weight'
    death_year: Optional[IntCriterionInput]
    'Filter by death year'
    studios: Optional[HierarchicalMultiCriterionInput]
    'Filter by studios where performer appears in scene/image/gallery'
    performers: Optional[MultiCriterionInput]
    'Filter by performers where performer appears with another performer in scene/image/gallery'
    ignore_auto_tag: Optional[bool]
    'Filter by autotag ignore value'
    birthdate: Optional[DateCriterionInput]
    'Filter by birthdate'
    death_date: Optional[DateCriterionInput]
    'Filter by death date'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class PerformerUpdateInput(BaseModel):
    id: str
    name: Optional[str]
    disambiguation: Optional[str]
    url: Optional[str]
    gender: Optional[GenderEnum]
    birthdate: Optional[str]
    ethnicity: Optional[str]
    country: Optional[str]
    eye_color: Optional[str]
    height_cm: Optional[int]
    measurements: Optional[str]
    fake_tits: Optional[str]
    penis_length: Optional[float]
    circumcised: Optional[CircumisedEnum]
    career_length: Optional[str]
    tattoos: Optional[str]
    piercings: Optional[str]
    alias_list: Optional[List[str]]
    twitter: Optional[str]
    instagram: Optional[str]
    favorite: Optional[bool]
    tag_ids: Optional[List[str]]
    image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    stash_ids: Optional[List['StashIDInput']]
    rating100: Optional[int]
    details: Optional[str]
    death_date: Optional[str]
    hair_color: Optional[str]
    weight: Optional[int]
    ignore_auto_tag: Optional[bool]

class PhashDistanceCriterionInput(BaseModel):
    value: str
    modifier: CriterionModifier
    distance: Optional[int]

class PluginArgInput(BaseModel):
    key: str
    value: Optional['PluginValueInput']

class PluginValueInput(BaseModel):
    str: Optional[str]
    i: Optional[int]
    b: Optional[bool]
    f: Optional[float]
    o: Optional[List[PluginArgInput]]
    a: Optional[List['PluginValueInput']]

class RemoveTempDLNAIPInput(BaseModel):
    address: str

class ResolutionCriterionInput(BaseModel):
    value: ResolutionEnum
    modifier: CriterionModifier

class SaveFilterInput(BaseModel):
    id: Optional[str]
    'provide ID to overwrite existing filter'
    mode: FilterMode
    name: str
    find_filter: Optional[FindFilterType]
    object_filter: Optional[dict]
    ui_options: Optional[dict]

class ScanMetaDataFilterInput(BaseModel):
    """Filter options for meta data scannning"""
    minModTime: Optional[str]
    'If set, files with a modification time before this time point are ignored by the scan'

class ScanMetadataInput(BaseModel):
    paths: Optional[List[str]]
    scanGenerateCovers: Optional[bool]
    'Generate covers during scan'
    scanGeneratePreviews: Optional[bool]
    'Generate previews during scan'
    scanGenerateImagePreviews: Optional[bool]
    'Generate image previews during scan'
    scanGenerateSprites: Optional[bool]
    'Generate sprites during scan'
    scanGeneratePhashes: Optional[bool]
    'Generate phashes during scan'
    scanGenerateThumbnails: Optional[bool]
    'Generate image thumbnails during scan'
    scanGenerateClipPreviews: Optional[bool]
    'Generate image clip previews during scan'
    filter: Optional[ScanMetaDataFilterInput]
    'Filter options for the scan'

class SceneCreateInput(BaseModel):
    title: Optional[str]
    code: Optional[str]
    details: Optional[str]
    director: Optional[str]
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]
    rating100: Optional[int]
    organized: Optional[bool]
    studio_id: Optional[str]
    gallery_ids: Optional[List[str]]
    performer_ids: Optional[List[str]]
    movies: Optional[List['SceneMovieInput']]
    tag_ids: Optional[List[str]]
    cover_image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    stash_ids: Optional[List['StashIDInput']]
    file_ids: Optional[List[str]]
    'The first id will be assigned as primary.\nFiles will be reassigned from existing scenes if applicable.\nFiles must not already be primary for another scene.'

class SceneDestroyInput(BaseModel):
    id: str
    delete_file: Optional[bool]
    delete_generated: Optional[bool]

class SceneFilterType(BaseModel):
    AND: Optional['SceneFilterType']
    OR: Optional['SceneFilterType']
    NOT: Optional['SceneFilterType']
    id: Optional[IntCriterionInput]
    title: Optional['StringCriterionInput']
    code: Optional['StringCriterionInput']
    details: Optional['StringCriterionInput']
    director: Optional['StringCriterionInput']
    oshash: Optional['StringCriterionInput']
    'Filter by file oshash'
    checksum: Optional['StringCriterionInput']
    'Filter by file checksum'
    phash: Optional['StringCriterionInput']
    'Filter by file phash'
    phash_distance: Optional[PhashDistanceCriterionInput]
    'Filter by file phash distance'
    path: Optional['StringCriterionInput']
    'Filter by path'
    file_count: Optional[IntCriterionInput]
    'Filter by file count'
    rating100: Optional[IntCriterionInput]
    organized: Optional[bool]
    'Filter by organized'
    o_counter: Optional[IntCriterionInput]
    'Filter by o-counter'
    duplicated: Optional[PHashDuplicationCriterionInput]
    'Filter Scenes that have an exact phash match available'
    resolution: Optional[ResolutionCriterionInput]
    'Filter by resolution'
    framerate: Optional[IntCriterionInput]
    'Filter by frame rate'
    video_codec: Optional['StringCriterionInput']
    'Filter by video codec'
    audio_codec: Optional['StringCriterionInput']
    'Filter by audio codec'
    duration: Optional[IntCriterionInput]
    'Filter by duration (in seconds)'
    has_markers: Optional[str]
    'Filter to only include scenes which have markers. `true` or `false`'
    is_missing: Optional[str]
    'Filter to only include scenes missing this property'
    studios: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include scenes with this studio'
    movies: Optional[MultiCriterionInput]
    'Filter to only include scenes with this movie'
    tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include scenes with these tags'
    tag_count: Optional[IntCriterionInput]
    'Filter by tag count'
    performer_tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include scenes with performers with these tags'
    performer_favorite: Optional[bool]
    'Filter scenes that have performers that have been favorited'
    performer_age: Optional[IntCriterionInput]
    'Filter scenes by performer age at time of scene'
    performers: Optional[MultiCriterionInput]
    'Filter to only include scenes with these performers'
    performer_count: Optional[IntCriterionInput]
    'Filter by performer count'
    stash_id_endpoint: Optional['StashIDCriterionInput']
    'Filter by StashID'
    url: Optional['StringCriterionInput']
    'Filter by url'
    interactive: Optional[bool]
    'Filter by interactive'
    interactive_speed: Optional[IntCriterionInput]
    'Filter by InteractiveSpeed'
    captions: Optional['StringCriterionInput']
    'Filter by captions'
    resume_time: Optional[IntCriterionInput]
    'Filter by resume time'
    play_count: Optional[IntCriterionInput]
    'Filter by play count'
    play_duration: Optional[IntCriterionInput]
    'Filter by play duration (in seconds)'
    date: Optional[DateCriterionInput]
    'Filter by date'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class SceneHashInput(BaseModel):
    checksum: Optional[str]
    oshash: Optional[str]

class SceneMarkerCreateInput(BaseModel):
    title: str
    seconds: float
    scene_id: str
    primary_tag_id: str
    tag_ids: Optional[List[str]]

class SceneMarkerFilterType(BaseModel):
    tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include scene markers with these tags'
    scene_tags: Optional[HierarchicalMultiCriterionInput]
    'Filter to only include scene markers attached to a scene with these tags'
    performers: Optional[MultiCriterionInput]
    'Filter to only include scene markers with these performers'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'
    scene_date: Optional[DateCriterionInput]
    'Filter by scene date'
    scene_created_at: Optional['TimestampCriterionInput']
    'Filter by scene creation time'
    scene_updated_at: Optional['TimestampCriterionInput']
    'Filter by scene last update time'

class SceneMarkerUpdateInput(BaseModel):
    id: str
    title: Optional[str]
    seconds: Optional[float]
    scene_id: Optional[str]
    primary_tag_id: Optional[str]
    tag_ids: Optional[List[str]]

class SceneMergeInput(BaseModel):
    source: List[str]
    'If destination scene has no files, then the primary file of the\nfirst source scene will be assigned as primary'
    destination: str
    values: Optional['SceneUpdateInput']

class SceneMovieInput(BaseModel):
    movie_id: str
    scene_index: Optional[int]

class SceneParserInput(BaseModel):
    ignoreWords: Optional[List[str]]
    whitespaceCharacters: Optional[str]
    capitalizeTitle: Optional[bool]
    ignoreOrganized: Optional[bool]

class SceneUpdateInput(BaseModel):
    clientMutationId: Optional[str]
    id: str
    title: Optional[str]
    code: Optional[str]
    details: Optional[str]
    director: Optional[str]
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]
    rating100: Optional[int]
    o_counter: Optional[int]
    organized: Optional[bool]
    studio_id: Optional[str]
    gallery_ids: Optional[List[str]]
    performer_ids: Optional[List[str]]
    movies: Optional[List[SceneMovieInput]]
    tag_ids: Optional[List[str]]
    cover_image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    stash_ids: Optional[List['StashIDInput']]
    resume_time: Optional[float]
    'The time index a scene was left at'
    play_duration: Optional[float]
    'The total time a scene has spent playing'
    play_count: Optional[int]
    'The number ot times a scene has been played'
    primary_file_id: Optional[str]

class ScenesDestroyInput(BaseModel):
    ids: List[str]
    delete_file: Optional[bool]
    delete_generated: Optional[bool]

class ScrapeMultiPerformersInput(BaseModel):
    performer_ids: Optional[List[str]]
    'Instructs to query by scene fingerprints'

class ScrapeMultiScenesInput(BaseModel):
    scene_ids: Optional[List[str]]
    'Instructs to query by scene fingerprints'

class ScrapeSingleGalleryInput(BaseModel):
    query: Optional[str]
    'Instructs to query by string'
    gallery_id: Optional[str]
    'Instructs to query by gallery id'
    gallery_input: Optional['ScrapedGalleryInput']
    'Instructs to query by gallery fragment'

class ScrapeSingleMovieInput(BaseModel):
    query: Optional[str]
    'Instructs to query by string'
    movie_id: Optional[str]
    'Instructs to query by movie id'
    movie_input: Optional['ScrapedMovieInput']
    'Instructs to query by gallery fragment'

class ScrapeSinglePerformerInput(BaseModel):
    query: Optional[str]
    'Instructs to query by string'
    performer_id: Optional[str]
    'Instructs to query by performer id'
    performer_input: Optional['ScrapedPerformerInput']
    'Instructs to query by performer fragment'

class ScrapeSingleSceneInput(BaseModel):
    query: Optional[str]
    'Instructs to query by string'
    scene_id: Optional[str]
    'Instructs to query by scene fingerprints'
    scene_input: Optional['ScrapedSceneInput']
    'Instructs to query by scene fragment'

class ScrapeSingleStudioInput(BaseModel):
    query: Optional[str]
    'Query can be either a name or a Stash ID'

class ScrapedGalleryInput(BaseModel):
    title: Optional[str]
    details: Optional[str]
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]

class ScrapedMovieInput(BaseModel):
    name: Optional[str]
    aliases: Optional[str]
    duration: Optional[str]
    date: Optional[str]
    rating: Optional[str]
    director: Optional[str]
    url: Optional[str]
    synopsis: Optional[str]

class ScrapedPerformerInput(BaseModel):
    stored_id: Optional[str]
    'Set if performer matched'
    name: Optional[str]
    disambiguation: Optional[str]
    gender: Optional[str]
    url: Optional[str]
    twitter: Optional[str]
    instagram: Optional[str]
    birthdate: Optional[str]
    ethnicity: Optional[str]
    country: Optional[str]
    eye_color: Optional[str]
    height: Optional[str]
    measurements: Optional[str]
    fake_tits: Optional[str]
    penis_length: Optional[str]
    circumcised: Optional[str]
    career_length: Optional[str]
    tattoos: Optional[str]
    piercings: Optional[str]
    aliases: Optional[str]
    details: Optional[str]
    death_date: Optional[str]
    hair_color: Optional[str]
    weight: Optional[str]
    remote_site_id: Optional[str]

class ScrapedSceneInput(BaseModel):
    title: Optional[str]
    code: Optional[str]
    details: Optional[str]
    director: Optional[str]
    url: Optional[str]
    urls: Optional[List[str]]
    date: Optional[str]
    remote_site_id: Optional[str]

class ScraperSourceInput(BaseModel):
    stash_box_index: Optional[int]
    'Index of the configured stash-box instance to use. Should be unset if scraper_id is set'
    stash_box_endpoint: Optional[str]
    'Stash-box endpoint'
    scraper_id: Optional[str]
    'Scraper ID to scrape with. Should be unset if stash_box_index is set'

class SetDefaultFilterInput(BaseModel):
    mode: FilterMode
    find_filter: Optional[FindFilterType]
    'null to clear'
    object_filter: Optional[dict]
    ui_options: Optional[dict]

class SetupInput(BaseModel):
    configLocation: str
    'Empty to indicate $HOME/.stash/config.yml default'
    stashes: List['StashConfigInput']
    databaseFile: str
    'Empty to indicate default'
    generatedLocation: str
    'Empty to indicate default'
    cacheLocation: str
    'Empty to indicate default'
    storeBlobsInDatabase: bool
    blobsLocation: str
    'Empty to indicate default - only applicable if storeBlobsInDatabase is false'

class StashBoxBatchTagInput(BaseModel):
    """If neither ids nor names are set, tag all items"""
    endpoint: int
    'Stash endpoint to use for the tagging'
    exclude_fields: Optional[List[str]]
    'Fields to exclude when executing the tagging'
    refresh: bool
    'Refresh items already tagged by StashBox if true. Only tag items with no StashBox tagging if false'
    createParent: bool
    'If batch adding studios, should their parent studios also be created?'
    ids: Optional[List[str]]
    'If set, only tag these ids'
    names: Optional[List[str]]
    'If set, only tag these names'
    performer_ids: Optional[List[str]]
    'If set, only tag these performer ids'
    performer_names: Optional[List[str]]
    'If set, only tag these performer names'

class StashBoxDraftSubmissionInput(BaseModel):
    id: str
    stash_box_index: int

class StashBoxFingerprintSubmissionInput(BaseModel):
    scene_ids: List[str]
    stash_box_index: int

class StashBoxInput(BaseModel):
    endpoint: str
    api_key: str
    name: str

class StashBoxPerformerQueryInput(BaseModel):
    stash_box_index: int
    'Index of the configured stash-box instance to use'
    performer_ids: Optional[List[str]]
    'Instructs query by scene fingerprints'
    q: Optional[str]
    'Query by query string'

class StashBoxSceneQueryInput(BaseModel):
    stash_box_index: int
    'Index of the configured stash-box instance to use'
    scene_ids: Optional[List[str]]
    'Instructs query by scene fingerprints'
    q: Optional[str]
    'Query by query string'

class StashConfigInput(BaseModel):
    """Stash configuration details"""
    path: str
    excludeVideo: bool
    excludeImage: bool

class StashIDCriterionInput(BaseModel):
    endpoint: Optional[str]
    'If present, this value is treated as a predicate.\nThat is, it will filter based on stash_ids with the matching endpoint'
    stash_id: Optional[str]
    modifier: CriterionModifier

class StashIDInput(BaseModel):
    endpoint: str
    stash_id: str

class StringCriterionInput(BaseModel):
    value: str
    modifier: CriterionModifier

class StudioCreateInput(BaseModel):
    name: str
    url: Optional[str]
    parent_id: Optional[str]
    image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    stash_ids: Optional[List[StashIDInput]]
    rating100: Optional[int]
    details: Optional[str]
    aliases: Optional[List[str]]
    ignore_auto_tag: Optional[bool]

class StudioDestroyInput(BaseModel):
    id: str

class StudioFilterType(BaseModel):
    AND: Optional['StudioFilterType']
    OR: Optional['StudioFilterType']
    NOT: Optional['StudioFilterType']
    name: Optional[StringCriterionInput]
    details: Optional[StringCriterionInput]
    parents: Optional[MultiCriterionInput]
    'Filter to only include studios with this parent studio'
    stash_id_endpoint: Optional[StashIDCriterionInput]
    'Filter by StashID'
    is_missing: Optional[str]
    'Filter to only include studios missing this property'
    rating100: Optional[IntCriterionInput]
    scene_count: Optional[IntCriterionInput]
    'Filter by scene count'
    image_count: Optional[IntCriterionInput]
    'Filter by image count'
    gallery_count: Optional[IntCriterionInput]
    'Filter by gallery count'
    url: Optional[StringCriterionInput]
    'Filter by url'
    aliases: Optional[StringCriterionInput]
    'Filter by studio aliases'
    ignore_auto_tag: Optional[bool]
    'Filter by autotag ignore value'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class StudioUpdateInput(BaseModel):
    id: str
    name: Optional[str]
    url: Optional[str]
    parent_id: Optional[str]
    image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    stash_ids: Optional[List[StashIDInput]]
    rating100: Optional[int]
    details: Optional[str]
    aliases: Optional[List[str]]
    ignore_auto_tag: Optional[bool]

class TagCreateInput(BaseModel):
    name: str
    description: Optional[str]
    aliases: Optional[List[str]]
    ignore_auto_tag: Optional[bool]
    image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    parent_ids: Optional[List[str]]
    child_ids: Optional[List[str]]

class TagDestroyInput(BaseModel):
    id: str

class TagFilterType(BaseModel):
    AND: Optional['TagFilterType']
    OR: Optional['TagFilterType']
    NOT: Optional['TagFilterType']
    name: Optional[StringCriterionInput]
    'Filter by tag name'
    aliases: Optional[StringCriterionInput]
    'Filter by tag aliases'
    description: Optional[StringCriterionInput]
    'Filter by tag description'
    is_missing: Optional[str]
    'Filter to only include tags missing this property'
    scene_count: Optional[IntCriterionInput]
    'Filter by number of scenes with this tag'
    image_count: Optional[IntCriterionInput]
    'Filter by number of images with this tag'
    gallery_count: Optional[IntCriterionInput]
    'Filter by number of galleries with this tag'
    performer_count: Optional[IntCriterionInput]
    'Filter by number of performers with this tag'
    marker_count: Optional[IntCriterionInput]
    'Filter by number of markers with this tag'
    parents: Optional[HierarchicalMultiCriterionInput]
    'Filter by parent tags'
    children: Optional[HierarchicalMultiCriterionInput]
    'Filter by child tags'
    parent_count: Optional[IntCriterionInput]
    'Filter by number of parent tags the tag has'
    child_count: Optional[IntCriterionInput]
    'Filter by number f child tags the tag has'
    ignore_auto_tag: Optional[bool]
    'Filter by autotag ignore value'
    created_at: Optional['TimestampCriterionInput']
    'Filter by creation time'
    updated_at: Optional['TimestampCriterionInput']
    'Filter by last update time'

class TagUpdateInput(BaseModel):
    id: str
    name: Optional[str]
    description: Optional[str]
    aliases: Optional[List[str]]
    ignore_auto_tag: Optional[bool]
    image: Optional[str]
    'This should be a URL or a base64 encoded data URL'
    parent_ids: Optional[List[str]]
    child_ids: Optional[List[str]]

class TagsMergeInput(BaseModel):
    source: List[str]
    destination: str

class TimestampCriterionInput(BaseModel):
    value: str
    value2: Optional[str]
    modifier: CriterionModifier
BulkGalleryUpdateInput.update_forward_refs()
BulkImageUpdateInput.update_forward_refs()
BulkPerformerUpdateInput.update_forward_refs()
BulkSceneUpdateInput.update_forward_refs()
ConfigDefaultSettingsInput.update_forward_refs()
ConfigGeneralInput.update_forward_refs()
GalleryFilterType.update_forward_refs()
GenerateMetadataInput.update_forward_refs()
IdentifyMetadataInput.update_forward_refs()
IdentifySourceInput.update_forward_refs()
ImageFilterType.update_forward_refs()
MovieFilterType.update_forward_refs()
PerformerCreateInput.update_forward_refs()
PerformerFilterType.update_forward_refs()
PerformerUpdateInput.update_forward_refs()
PluginArgInput.update_forward_refs()
PluginValueInput.update_forward_refs()
SceneCreateInput.update_forward_refs()
SceneFilterType.update_forward_refs()
SceneMarkerFilterType.update_forward_refs()
SceneMergeInput.update_forward_refs()
SceneUpdateInput.update_forward_refs()
ScrapeSingleGalleryInput.update_forward_refs()
ScrapeSingleMovieInput.update_forward_refs()
ScrapeSinglePerformerInput.update_forward_refs()
ScrapeSingleSceneInput.update_forward_refs()
SetupInput.update_forward_refs()
StudioFilterType.update_forward_refs()
TagFilterType.update_forward_refs()