STASHAPP = """
fragment scrapedScene on ScrapedScene {
	title
	details
	url
	date
	image
	studio{ ...scrapedStudio }
	tags{ ...scrapedTag }
	performers{ ...scrapedPerformer }
	movies{ ...scrapedMovie }
	duration
}
fragment scrapedGallery on ScrapedGallery {
	title
	details
	url
	date
	studio{ ...scrapedStudio }
	tags{ ...scrapedTag }
	performers{ ...scrapedPerformer }
}
fragment scrapedPerformer on ScrapedPerformer {
	stored_id
	name
	gender
	url
	twitter
	instagram
	birthdate
	ethnicity
	country
	eye_color
	height
	measurements
	fake_tits
	career_length
	tattoos
	piercings
	aliases
	tags { ...scrapedTag }
	images
	details
	death_date
	hair_color
	weight
	remote_site_id
}
fragment scrapedTag on ScrapedTag {
	stored_id
	name
}
fragment scrapedMovie on ScrapedMovie {
	stored_id
	name
	aliases
	duration
	date
	rating
	director
	synopsis
	url
	studio { ...scrapedStudio }
	front_image
	back_image
}
fragment scrapedStudio on ScrapedStudio {
	stored_id
	name
	url
	remote_site_id
}
fragment stashScene on Scene {
	id
	checksum
	oshash
	phash
	title
	details
	url
	date
	rating
	organized
	o_counter
	path
	tags {
	...stashTag
	}
	file {
	size
	duration
	video_codec
	audio_codec
	width
	height
	framerate
	bitrate
	__typename
	}
	galleries {
	id
	checksum
	path
	title
	url
	date
	details
	rating
	organized
	studio {
		id
		name
		url
		__typename
	}
	image_count
	tags {
		...stashTag
	}
	}
	performers {
	...stashPerformer
	}
	scene_markers { 
	...stashSceneMarker
	}
	studio{
	...stashStudio
	}
	stash_ids{
	endpoint
	stash_id
	__typename
	}
	__typename
}
fragment stashSceneSlim on Scene {
	id
	title
	path
	oshash
	phash
	file {
	size
	duration
	video_codec
	width
	height
	framerate
	bitrate
	__typename
	}
	__typename
}
fragment stashGallery on Gallery {
	id
	checksum
	path
	title
	date
	url
	details
	rating
	organized
	image_count
	cover {
		paths {
			thumbnail
		}
	}
	studio {
		id
		name
		__typename
	}
	tags {
		...stashTag
	}
	performers {
		...stashPerformer
	}
	scenes {
		id
		title
		__typename
	}
	images {
		id
		title
	}
	__typename
}
fragment stashPerformer on Performer {
	id
	checksum
	name
	url
	gender
	twitter
	instagram
	birthdate
	ethnicity
	country
	eye_color
	height
	measurements
	fake_tits
	career_length
	tattoos
	piercings
	aliases
	favorite
	tags { ...stashTag }
	image_path
	scene_count
	image_count
	gallery_count
	stash_ids {
		stash_id
		endpoint
		__typename
	}
	rating
	details
	death_date
	hair_color
	weight
	__typename
}
fragment stashSceneMarker on SceneMarker {
	id
	scene { id }
	title
	seconds
	primary_tag { ...stashTag }
	tags { ...stashTag }
	__typename
}
fragment stashMovie on Movie {
	id
	name
	aliases
	duration
	date
	rating
	studio { id }
	director
	synopsis
	url
	created_at
	updated_at
	scene_count
	__typename
}
fragment stashTag on Tag {
	id
	name
	aliases
	image_path
	scene_count
	__typename
}
fragment stashStudio on Studio {
	id
	name
	url
	aliases
	rating
	details
	stash_ids{
		endpoint
		stash_id
		__typename
	}
	parent_studio {
		id
		name
	}
	__typename
}
fragment ConfigData on ConfigResult {
	general {
		...ConfigGeneralData
	}
	interface {
		...ConfigInterfaceData
	}
	dlna {
		...ConfigDLNAData
	}
}
fragment ConfigGeneralData on ConfigGeneralResult {
	stashes {
		path
		excludeVideo
		excludeImage
	}
	databasePath
	generatedPath
	configFilePath
	cachePath
	calculateMD5
	videoFileNamingAlgorithm
	parallelTasks
	previewAudio
	previewSegments
	previewSegmentDuration
	previewExcludeStart
	previewExcludeEnd
	previewPreset
	maxTranscodeSize
	maxStreamingTranscodeSize
	apiKey
	username
	password
	maxSessionAge
	logFile
	logOut
	logLevel
	logAccess
	createGalleriesFromFolders
	videoExtensions
	imageExtensions
	galleryExtensions
	excludes
	imageExcludes
	scraperUserAgent
	scraperCertCheck
	scraperCDPPath
	stashBoxes {
		name
		endpoint
		api_key
	}
}
fragment ConfigInterfaceData on ConfigInterfaceResult {
	menuItems
	soundOnPreview
	wallShowTitle
	wallPlayback
	maximumLoopDuration
	autostartVideo
	showStudioAsText
	css
	cssEnabled
	language
	slideshowDelay
	handyKey
}
fragment ConfigDLNAData on ConfigDLNAResult {
	serverName
	enabled
	whitelistedIPs
	interfaces
}
"""

STASHBOX = """
fragment URLFragment on URL {
	url
	type
}
fragment ImageFragment on Image {
	id
	url
	width
	height
}
fragment StudioFragment on Studio {
	name
	id
	urls {
		...URLFragment
	}
	images {
		...ImageFragment
	}
}
fragment TagFragment on Tag {
	name
	id
}
fragment FuzzyDateFragment on FuzzyDate {
	date
	accuracy
}
fragment MeasurementsFragment on Measurements {
	band_size
	cup_size
	waist
	hip
}
fragment BodyModificationFragment on BodyModification {
	location
	description
}
fragment PerformerFragment on Performer {
	id
	name
	disambiguation
	aliases
	gender
	merged_ids
	urls {
		...URLFragment
	}
	images {
		...ImageFragment
	}
	birthdate {
		...FuzzyDateFragment
	}
	ethnicity
	country
	eye_color
	hair_color
	height
	measurements {
		...MeasurementsFragment
	}
	breast_type
	career_start_year
	career_end_year
	tattoos {
		...BodyModificationFragment
	}
	piercings {
		...BodyModificationFragment
	}
}
fragment PerformerAppearanceFragment on PerformerAppearance {
	as
	performer {
		...PerformerFragment
	}
}
fragment FingerprintFragment on Fingerprint {
	algorithm
	hash
	duration
}
fragment SceneFragment on Scene {
	id
	title
	details
	duration
	date
	urls {
		...URLFragment
	}
	images {
		...ImageFragment
	}
	studio {
		...StudioFragment
	}
	tags {
		...TagFragment
	}
	performers {
		...PerformerAppearanceFragment
	}
	fingerprints {
		...FingerprintFragment
	}
}
fragment EditFragment on Edit {
	applied
	closed
	created
	destructive
	details
	expires
	id
	old_details
	operation
	updated
	user { name }
	vote_count
}
"""