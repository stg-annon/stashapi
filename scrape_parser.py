import datetime

from . import log as StashLogger

from .types import Gender

class ScrapeParser:

	def __init__(self, stash_interface, logger=StashLogger, create_missing_tags:bool=False, create_missing_studios:bool=False):
		global log
		log = logger

		self.stash = stash_interface
		self.create_missing_tags = create_missing_tags
		self.create_missing_studios = create_missing_studios

	def detect(self, scraped_item):

		if not scraped_item.get("__typename"):
			return None
		
		if scraped_item["__typename"] == "ScrapedTag":
			return self.tag_from_scrape(scraped_item)
		if scraped_item["__typename"] == "ScrapedGallery":
			return self.gallery_from_scrape(scraped_item)
		if scraped_item["__typename"] == "ScrapedStudio":
			return self.studio_from_scrape(scraped_item)
		if scraped_item["__typename"] == "ScrapedMovie":
			return self.movie_from_scrape(scraped_item)
		if scraped_item["__typename"] == "ScrapedPerformer":
			return self.performer_from_scrape(scraped_item)
		if scraped_item["__typename"] == "ScrapedScene":
			return self.scene_from_scrape(scraped_item)

	def tag_from_scrape(self, tag):
		"""
		v0.12.0-40
		type ScrapedTag {
			stored_id: ID
			name: String!
		}

		type TagUpdateInput {
			id: ID!
			name: String
			aliases: [String!]
			image: String
			parent_ids: [ID!]
			child_ids: [ID!]
		}
		"""
		tag_update = {}

		if tag.get("stored_id"):
			tag_update["id"] = tag["stored_id"]
		elif self.create_missing_tags:
			return self.stash.find_tag({"name": tag.get("name")}, create=True)

		return tag_update

	def gallery_from_scrape(self, gallery):
		"""
		v0.12.0-40
		type ScrapedGallery {
			title: String
			details: String
			url: String
			date: String
			studio: ScrapedStudio
			tags: [ScrapedTag!]
			performers: [ScrapedPerformer!]
		}

		type GalleryUpdateInput {
			clientMutationId: String
			id: ID!
			title: String
			url: String
			date: String
			details: String
			rating: Int
			organized: Boolean
			scene_ids: [ID!]
			studio_id: ID
			tag_ids: [ID!]
			performer_ids: [ID!]
		}
		"""
		gallery_update = {}

		if gallery.get("tags"):
			gallery_update["tag_ids"] = [self.tag_from_scrape(t)["id"] for t in gallery["tags"]]
		if gallery.get("performers"):
			gallery_update["performer_ids"] = [self.performer_from_scrape(p)["id"] for p in gallery["performers"]]
		if gallery.get("studio"):
			gallery_update["studio_id"] = self.studio_from_scrape(gallery["studio"]).get("id", None)
			
		return gallery_update

	def studio_from_scrape(self, studio):
		"""
		v0.12.0-40
		type ScrapedStudio {
			stored_id: ID
			name: String!
			url: String
			image: String
			remote_site_id: String
		}

		type StudioUpdateInput {
			id: ID!
			name: String
			url: String
			parent_id: ID
			image: String
			stash_ids: [StashIDInput!]
			rating: Int
			details: String
			aliases: [String!]
		}
		"""
		studio_update = {}
		
		if studio.get("stored_id"):
			studio_update["id"] = studio["stored_id"]
		elif self.create_missing_studios:
			return self.stash.create_studio({
				"name"  : studio.get("name"),
				"url"   : studio.get("url"),
				"image" : studio.get("image"),
			})
		return studio_update

	def scene_movie_input_from_scrape(self, movie):
		stash_movie = self.stash.find_movie(self.movie_from_scrape(movie), create=True)
		scene_movie_input = {"movie_id": stash_movie["id"], "scene_index":None }
		if movie.get("scene_index"):
			scene_movie_input["scene_index"] = movie["scene_index"]
		return scene_movie_input

	def movie_from_scrape(self, movie):
		"""
		v0.12.0-40
		type ScrapedMovie {
				stored_id: ID
				name: String
				aliases: String
				duration: String
				date: String
				rating: String
				director: String
				url: String
				synopsis: String
				studio: ScrapedStudio
				front_image: String
				back_image: String
		}
		
		type MovieUpdateInput {
				id: ID!
				name: String
				aliases: String
				duration: Int
				date: String
				rating: Int
				studio_id: ID
				director: String
				synopsis: String
				url: String
				front_image: String
				back_image: String
		}
		"""
		# NOTE
		#  duration: String (HH:MM:SS) => duration: Int (Total Seconds)
		#  studio: {ScrapedMovieStudio} => studio_id: ID
		movie_update = {}
		
		if movie.get("stored_id"):
			movie_update["id"] = movie["stored_id"]
			return movie_update

		# duration value from scraped movie is string, update expects an int
		if movie.get("duration"):
			if movie["duration"].count(':') == 0:
				movie["duration"] = f'00:00:{movie["duration"]}'
			if movie["duration"].count(':') == 1:
				movie["duration"] = f'00:{movie["duration"]}'
			h,m,s = movie["duration"].split(':')
			duration = datetime.timedelta(hours=int(h),minutes=int(m),seconds=int(s)).total_seconds()
			movie_update['duration'] = int(duration)

		if movie.get("studio"):
			movie_update["studio_id"] = self.studio_from_scrape(movie["studio"])["id"]

		for attr in ["name","aliases","date","rating","director","url","synopsis","front_image","back_image"]:
			if movie.get(attr):
				movie_update[attr] = movie[attr]

		return movie_update

	def performer_from_scrape(self, performer):
		"""
		v0.12.0-40
		type ScrapedPerformer {
				stored_id: ID
				name: String
				gender: String
				url: String
				twitter: String
				instagram: String
				birthdate: String
				ethnicity: String
				country: String
				eye_color: String
				height: String
				measurements: String
				fake_tits: String
				career_length: String
				tattoos: String
				piercings: String
				aliases: String
				tags: [ScrapedTag!]
				images: [String!]
				details: String
				death_date: String
				hair_color: String
				weight: String
				remote_site_id: String

				# Deprecated: use images instead
				image: String
		}

		type PerformerUpdateInput {
				id: ID!
				name: String
				url: String
				gender: GenderEnum
				birthdate: String
				ethnicity: String
				country: String
				eye_color: String
				height: String
				measurements: String
				fake_tits: String
				career_length: String
				tattoos: String
				piercings: String
				aliases: String
				twitter: String
				instagram: String
				favorite: Boolean
				tag_ids: [ID!]
				image: String
				stash_ids: [StashIDInput!]
				rating: Int
				details: String
				death_date: String
				hair_color: String
				weight: Int
		}
		"""
		# NOTE
		# 	ScrapedPerformer.gender: String => PerformerCreateInput.gender: GenderEnum
		#  ScrapedPerformer.weight: String (kg?) => PerformerCreateInput.weight: Int (kg)
		performer_update = {}

		if performer.get("stored_id"):
			performer_update["id"] = performer["stored_id"]
			return performer_update

		if performer.get("images") and len(performer["images"]) > 0:
			performer_update["image"] = performer["images"][0]
			
		if performer.get("tags"):
			performer_update["tag_ids"] = [self.tag_from_scrape(t)["id"] for t in performer.get("tags")]

		if performer.get("weight"):
			try:
				performer_update["weight"] = int(performer["weight"])
			except:
				log.warning(f'Could not parse performer weight "{performer["weight"]}" it Int for {performer["name"]}')

		if performer.get("gender"):
			try:
				performer_update["gender"] = Gender[performer["gender"].upper()].value
			except:
				log.warning(f'Cannot map performer Gender "{performer["gender"]}" for {performer["name"]}')

		for attr in ["name","url","gender","birthdate","ethnicity","country","eye_color","height","measurements","fake_tits","career_length","tattoos","piercings","aliases","details","death_date","hair_color"]:
			if performer.get(attr):
				performer_update[attr] = performer[attr]

		return performer_update

	def scene_from_scrape(self, scene):
		"""
		v0.12.0-40
		type ScrapedScene {
			title: String
			details: String
			url: String
			date: String
			image: String
			file: SceneFileType
			studio: ScrapedStudio
			tags: [ScrapedTag!]
			performers: [ScrapedPerformer!]
			movies: [ScrapedMovie!]
			remote_site_id: String
			duration: Int
			fingerprints: [StashBoxFingerprint!]
		}
		type SceneUpdateInput {
			clientMutationId: String
			id: ID!
			title: String
			details: String
			url: String
			date: String
			rating: Int
			organized: Boolean
			studio_id: ID
			gallery_ids: [ID!]
			performer_ids: [ID!]
			movies: [SceneMovieInput!]
			tag_ids: [ID!]
			cover_image: String
			stash_ids: [StashIDInput!]
		}
		"""
		scene_update = {}
		
		if scene.get("image"):
			scene_update["cover_image"] = scene["image"]

		if scene.get("studio"):
			scene_update["studio_id"] = self.studio_from_scrape(scene["studio"]).get("id")

		if scene.get("tags"):
			scene_update["tag_ids"] = [self.tag_from_scrape(t).get("id") for t in scene["tags"] if t]

		if scene.get("performers"):
			scene_update["performer_ids"] = []
			for p in scene["performers"]:
				performer = self.performer_from_scrape(p)
				if performer.get("id"):
					scene_update["performer_ids"].append(performer["id"])
				else:
					log.debug(f"could not match {p}")

		if scene.get("movies"):
			scene_update["movies"] = [self.scene_movie_input_from_scrape(m) for m in scene["movies"] if m]

		for attr in ["title","details","url","date","url","synopsis"]:
			if scene.get(attr):
				scene_update[attr] = scene[attr]

		return scene_update


	def localize_scraped_scene(self, scraped_scene):
		# casts ScrapedScene to ScrapedScene while resolving aliases
		"""
		v0.12.0-40
		type ScrapedScene {
			title: String
			details: String
			url: String
			date: String
			image: String
			file: SceneFileType
			studio: ScrapedStudio
			tags: [ScrapedTag!]
			performers: [ScrapedPerformer!]
			movies: [ScrapedMovie!]
			remote_site_id: String
			duration: Int
			fingerprints: [StashBoxFingerprint!]
		}
		"""
		if not scraped_scene:
			return

		if scraped_scene.get("performers"):
			for performer in scraped_scene["performers"]:
				if performer.get("stored_id"):
					continue
				performer_match = self.stash.find_performer(performer)
				if performer_match:
					performer["stored_id"] = performer_match["id"]

		return scraped_scene