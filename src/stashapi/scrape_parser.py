import datetime

from . import log

from .stash_types import OnMultipleMatch
from .stash_types import GenderEnum

class ScrapeParser:

	def __init__(self, stash_interface, logger=None, create_missing_tags:bool=False, create_missing_studios:bool=False, create_missing_performers:bool=False):
		global log
		if logger:
			log = logger

		self.stash = stash_interface
		self.create_missing_tags = create_missing_tags
		self.create_missing_studios = create_missing_studios
		self.create_missing_performers = create_missing_studios

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

	def tag_ids_from_scrape(self, tags):
		tag_ids = [self.tag_from_scrape(t) for t in tags]
		return [t["id"] for t in tag_ids if t.get("id")]

	def tag_from_scrape(self, tag):
		""" maps ScrapedTag to TagUpdateInput

		Args:
			tag (dict): Stash ScrapedTag Object

		Returns:
			dict: Stash TagUpdateInput Object
		"""
		tag_update = {}

		if tag.get("stored_id"):
			tag_update["id"] = tag["stored_id"]
		elif self.create_missing_tags:
			return self.stash.find_tag({"name": tag.get("name")}, create=True)

		tag_update["name"] = tag["name"]
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

		for attr in ["title","details","url","date"]:
			if gallery.get(attr):
				gallery_update[attr] = gallery[attr]
		if gallery.get("tags"):
			gallery_update["tag_ids"] = self.tag_ids_from_scrape(gallery["tags"]) 
		if gallery.get("performers"):
			gallery_update["performer_ids"] = self.performer_ids_from_scrape(gallery["performers"])
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
			movie_update["studio_id"] = self.studio_from_scrape(movie["studio"]).get("id")

		for attr in ["name","aliases","date","rating","director","url","synopsis","front_image","back_image"]:
			if movie.get(attr):
				movie_update[attr] = movie[attr]

		return movie_update

	def group_from_scrape(self, group):
		"""
		v0.27.2
		type ScrapedGroup {
				stored_id: ID
				name: String
				aliases: String
				duration: String
				date: String
				rating: String
				director: String
				urls: [String!]
				synopsis: String
				studio: ScrapedStudio
				tags: [ScrapedTag!]
				front_image: String
				back_image: String
		}
		type GroupUpdateInput {
				id: ID!
				name: String
				aliases: String
				duration: Int
				date: String
				rating100: Int
				studio_id: ID
				director: String
				synopsis: String
				urls: [String!]
				tag_ids: [ID!]
				containing_groups: [GroupDescriptionInput!]
				sub_groups: [GroupDescriptionInput!]
				front_image: String
				back_image: String
		}
		"""
		# NOTE
		#  duration: String (HH:MM:SS) => duration: Int (Total Seconds)
		#  studio: <ScrapedStudio> => studio_id: ID
		#  tags: <ScrapedTags> => tag_ids: [ID!]
		group_update = {}
		
		if group.get("stored_id"):
			group_update["id"] = group["stored_id"]
			return group_update

		if group.get("name"):
			group_update["name"] = group["name"].title()

		# duration value from scraped movie is string, update expects an int
		if group.get("duration"):
			if group["duration"].count(':') == 0:
				group["duration"] = f'00:00:{group["duration"]}'
			if group["duration"].count(':') == 1:
				group["duration"] = f'00:{group["duration"]}'
			h,m,s = group["duration"].split(':')
			duration = datetime.timedelta(hours=int(h),minutes=int(m),seconds=int(s)).total_seconds()
			group_update['duration'] = int(duration)

		if group.get("studio"):
			group_update["studio_id"] = self.studio_from_scrape(group["studio"]).get("id")

		if group.get("tags"):
			group_update["tag_ids"] = self.tag_ids_from_scrape(group["tags"])

		for attr in ["aliases","date","rating","director","urls","synopsis","front_image","back_image"]:
			if group.get(attr):
				group_update[attr] = group[attr]

		if group.get("url"):
			group_update["urls"] = group["url"]

		return group_update

	def performer_ids_from_scrape(self, performers):
		performer_ids = []
		for p in performers:
			if p.get("stored_id"):
				performer_ids.append(p["stored_id"])
				continue
			performer_match = self.stash.find_performer(p, fragment="id", create=self.create_missing_performers, on_multiple=OnMultipleMatch.RETURN_NONE)
			if performer_match:
				performer_ids.append(performer_match["id"])
			else:
				log.warning(f'Could not find performer "{p["name"]}" {self.create_missing_performers=}')

		return performer_ids

	def performer_from_scrape(self, scrape) -> dict:
		"""maps performer scrape data to performer create data 

		Args:
			scrape (dict): ScrapedPerformer

		Returns:
			dict: PerformerCreateInput

		Note:
			ScrapedPerformer.gender (String) => PerformerCreateInput.gender (GenderEnum)
			ScrapedPerformer.weight (String) => PerformerCreateInput.weight: (Int {kg})
		"""
		performer_update = {}

		# if performer.get("disambiguation"):
		# 	if re.match(r'[a-z0-9\-]+\.[a-z]{2,}',performer["disambiguation"]):
		# 		performer["aliases"] = performer["name"] 
		# 		performer["name"] = performer["name"]+":"+performer["disambiguation"]

		if scrape.get("stored_id"):
			performer_update["id"] = scrape["stored_id"]
			return performer_update

		common_attributes = [
			"name",
			"url",
			"birthdate",
			"ethnicity",
			"country",
			"eye_color",
			"height",
			"measurements",
			"fake_tits",
			"career_length",
			"tattoos",
			"piercings",
			"aliases",
			"details",
			"death_date",
			"hair_color"
		]
		for attr in common_attributes:
			if scrape.get(attr):
				performer_update[attr] = scrape[attr]

		if scrape.get("images") and len(scrape["images"]) > 0:
			performer_update["image"] = scrape["images"][0]
			
		if scrape.get("tags"):
			performer_update["tag_ids"] = self.tag_ids_from_scrape(scrape["tags"])

		if scrape.get("weight"):
			try:
				performer_update["weight"] = int(scrape["weight"])
			except:
				log.warning(f'Could not parse performer weight "{scrape["weight"]}" it Int for {scrape["name"]}')

		if scrape.get("gender"):
			try:
				performer_update["gender"] = GenderEnum[scrape["gender"].upper()].value
			except:
				log.warning(f'Could not map performer Gender "{scrape["gender"]}" for {scrape["name"]}')

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
		
		if scene.get("code"):
			scene_update["code"] = str(scene["code"])
		
		if scene.get("image"):
			scene_update["cover_image"] = scene["image"]

		if scene.get("studio"):
			scene_update["studio_id"] = self.studio_from_scrape(scene["studio"]).get("id")

		if scene.get("tags"):
			scene_update["tag_ids"] = self.tag_ids_from_scrape(scene["tags"])

		if scene.get("performers"):
			scene_update["performer_ids"] = []
			for p in scene["performers"]:
				performer = self.performer_from_scrape(p)
				if performer.get("id"):
					scene_update["performer_ids"].append(performer["id"])
				else:
					log.debug(f"could not match performer {p['name']}")

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

		# log.info(scraped_scene)
		if scraped_scene.get("performers"):
			for performer in scraped_scene["performers"]:
				if performer.get("stored_id"):
					continue
				performer_match = self.stash.find_performer(performer, on_multiple=OnMultipleMatch.RETURN_NONE)
				if performer_match:
					performer["stored_id"] = performer_match["id"]

		return scraped_scene
	
	def localize_scraped_gallery(self, scraped_gallery):
		# casts ScrapedScene to ScrapedScene while resolving aliases
		"""
		v0.27.2
		type ScrapedGallery {
			title: String
			code: String
			details: String
			photographer: String
			urls: [String!]
			date: String
			studio: ScrapedStudio
			tags: [ScrapedTag!]
			performers: [ScrapedPerformer!]
		}
		"""
		if not scraped_gallery:
			return

		# log.info(scraped_scene)
		if scraped_gallery.get("performers"):
			for performer in scraped_gallery["performers"]:
				if performer.get("stored_id"):
					continue
				performer_match = self.stash.find_performer(performer, on_multiple=OnMultipleMatch.RETURN_NONE)
				if performer_match:
					performer["stored_id"] = performer_match["id"]

		return scraped_gallery