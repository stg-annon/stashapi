RELEASE_0_16_1="""
fragment ScrapedScene on ScrapedScene {
   title
   details
   url
   date
   image
   studio{ ...ScrapedStudio }
   tags{ ...ScrapedTag }
   performers{ ...ScrapedPerformer }
   movies{ ...ScrapedMovie }
   duration
}
fragment ScrapedGallery on ScrapedGallery {
   title
   details
   url
   date
   studio{ ...ScrapedStudio }
   tags{ ...ScrapedTag }
   performers{ ...ScrapedPerformer }
}
fragment ScrapedPerformer on ScrapedPerformer {
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
   tags { ...ScrapedTag }
   images
   details
   death_date
   hair_color
   weight
   remote_site_id
}
fragment ScrapedTag on ScrapedTag {
   stored_id
   name
}
fragment ScrapedMovie on ScrapedMovie {
   stored_id
   name
   aliases
   duration
   date
   rating
   director
   synopsis
   url
   studio { ...ScrapedStudio }
   front_image
   back_image
}
fragment ScrapedStudio on ScrapedStudio {
   stored_id
   name
   url
   remote_site_id
}
fragment Scene on Scene {
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
   tags { ...Tag }
   file {
      size
      duration
      video_codec
      audio_codec
      width
      height
      framerate
      bitrate
   }
   galleries { ...Gallery }
   performers { ...Performer }
   scene_markers { ...SceneMarker }
   studio{ ...Studio }
   stash_ids{ ...StashID }
}
fragment SceneSlim on Scene {
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
   }
}
fragment Gallery on Gallery {
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
   }
   tags {
      ...Tag
   }
   performers {
      ...Performer
   }
   scenes {
      id
      title
   }
   images {
      id
      title
   }
}
fragment Image on Image {
   id
   checksum
   title
   rating
   o_counter
   organized
   path
   galleries { id }
   studio { id name }
   tags { ...Tag }
   performers { id name }
}
fragment Performer on Performer {
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
   tags { ...Tag }
   image_path
   scene_count
   image_count
   gallery_count
   stash_ids { ...StashID }
   rating
   details
   death_date
   hair_color
   weight
}
fragment SceneMarker on SceneMarker {
   id
   scene { id }
   title
   seconds
   primary_tag { ...Tag }
   tags { ...Tag }
}
fragment Movie on Movie {
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
}
fragment Tag on Tag {
   id
   name
   aliases
   image_path
   scene_count
}
fragment Studio on Studio {
   id
   name
   url
   aliases
   rating
   details
   stash_ids { ...StashID }
   parent_studio {
      id
      name
   }
}
fragment StashID on StashID {
   stash_id
   endpoint
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
fragment ScrapedScene on ScrapedScene {
   title
   details
   url
   date
   image
   studio{ ...ScrapedStudio }
   tags{ ...ScrapedTag }
   performers{ ...ScrapedPerformer }
   movies{ ...ScrapedMovie }
   duration
}
fragment ScrapedGallery on ScrapedGallery {
   title
   details
   url
   date
   studio{ ...ScrapedStudio }
   tags{ ...ScrapedTag }
   performers{ ...ScrapedPerformer }
}
fragment ScrapedPerformer on ScrapedPerformer {
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
   tags { ...ScrapedTag }
   images
   details
   death_date
   hair_color
   weight
   remote_site_id
}
fragment ScrapedTag on ScrapedTag {
   stored_id
   name
}
fragment ScrapedMovie on ScrapedMovie {
   stored_id
   name
   aliases
   duration
   date
   rating
   director
   synopsis
   url
   studio { ...ScrapedStudio }
   front_image
   back_image
}
fragment ScrapedStudio on ScrapedStudio {
   stored_id
   name
   url
   remote_site_id
}
fragment Scene on Scene {
   id
   title
   details
   url
   date
   rating
   organized
   o_counter
   files { ...VideoFile }
   tags { ...Tag }
   galleries { ...Gallery }
   performers { ...Performer }
   scene_markers { ...SceneMarker }
   studio{ ...Studio }
   stash_ids{ ...StashID }
}
fragment SceneSlim on Scene {
   id
   title
   files { ...VideoFile }
   oshash
   phash
}
fragment Gallery on Gallery {
   id
   title
   date
   url
   details
   rating
   organized
   files { ...GalleryFile }
   folder { ...Folder }
   scenes { id title }
   studio { id name }
   image_count
   tags { ...Tag }
   performers { ...Performer }
   cover { id }
   created_at
   updated_at
}
fragment Image on Image {
   id
   title
   rating
   o_counter
   organized
   files { ...ImageFile }
   galleries { id }
   studio { id name }
   tags { id name }
   performers { id name }
   created_at
   updated_at
}
fragment Performer on Performer {
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
   tags { ...Tag }
   image_path
   scene_count
   image_count
   gallery_count
   stash_ids { ...StashID }
   rating
   details
   death_date
   hair_color
   weight
}
fragment SceneMarker on SceneMarker {
   id
   scene { id }
   title
   seconds
   primary_tag { ...Tag }
   tags { ...Tag }
}
fragment Movie on Movie {
   id
   name
   aliases
   duration
   date
   rating
   studio { id name }
   director
   synopsis
   url
   created_at
   updated_at
   scene_count
}
fragment Tag on Tag {
   id
   name
   aliases
   image_path
   scene_count
}
fragment Studio on Studio {
   id
   name
   url
   aliases
   rating
   details
   stash_ids{ ...StashID }
   parent_studio { id name }
}
fragment StashID on StashID {
   stash_id
   endpoint
}
fragment Fingerprint on Fingerprint {
   type
   value
}
fragment Folder on Folder {
   id
   path
   parent_folder_id
   zip_file_id
   mod_time
   created_at
   updated_at
}
fragment VideoFile on VideoFile {
   id
   path
   basename
   parent_folder_id
   zip_file_id
   mod_time
   size
   fingerprints { ...Fingerprint }
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
fragment ImageFile on ImageFile {
   id
   path
   basename
   parent_folder_id
   zip_file_id
   mod_time
   size
   fingerprints {...Fingerprints}
   width
   height
   created_at
   updated_at
}
fragment GalleryFile on GalleryFile {
   id
   path
   basename
   parent_folder_id
   zip_file_id
   mod_time
   size
   fingerprints { ...Fingerprint }
   created_at
   updated_at
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
