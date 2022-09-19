RELEASE_0_16_0="""
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
fragment stashImage on Image {
	id
	checksum
	title
	rating
	o_counter
	organized
	path
	galleries { id }
	studio { id name }
	tags { ...stashTag }
	performers { id name }
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
DEVELOP="""
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
	__typename
}
fragment scrapedGallery on ScrapedGallery {
	title
	details
	url
	date
	studio{ ...scrapedStudio }
	tags{ ...scrapedTag }
	performers{ ...scrapedPerformer }
	__typename
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
	__typename
}
fragment scrapedTag on ScrapedTag {
	stored_id
	name
	__typename
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
	__typename
}
fragment scrapedStudio on ScrapedStudio {
	stored_id
	name
	url
	remote_site_id
	__typename
}
fragment stashScene on Scene {
	id
	title
	details
	url
	date
	rating
	organized
	o_counter
	files { id path }
	tags { ...stashTag }
	galleries { id name }
	performers { ...stashPerformer }
	scene_markers { ...stashSceneMarker }
	studio{ ...stashStudio }
	stash_ids{ endpoint stash_id }
}
fragment stashSceneSlim on Scene {
	id
	title
	files { id path }
	oshash
	phash
}
fragment stashVideoFile on VideoFile {
   id
   path
   basename
   parent_folder_id
   zip_file_id
   mod_time
   size
   fingerprints { type value }
   format
   width
   height
   duration
   video_codec
   audio_codec
   frame_rate
   bit_rate
   created_at
   updated_at
}
fragment stashGallery on Gallery {
	id
	title
	date
	url
	details
	rating
	organized
   files { id path }
   folder
	scenes { id title }
	studio { id name }
   image_count
	tags { ...stashTag }
	performers { ...stashPerformer }
	images { id }
	cover { id }
   created_at
   updated_at
}
fragment stashGalleryFile on GalleryFile {
   id
   path
   basename
   parent_folder_id
   zip_file_id
   mod_time
   size
   fingerprints { type value }
   created_at
   updated_at
}
fragment stashImage on Image {
	id
	title
	rating
	o_counter
	organized
	files { id path fingerprints { type value } }
	galleries { id }
	studio { id name }
	tags { id name }
	performers { id name }
   created_at
   updated_at
}
fragment stashImageFile on ImageFile {
   id
   path
   basename
   parent_folder_id
   zip_file_id
   mod_time
   size
   fingerprints { type value }
   width
   height
   created_at
   updated_at
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
