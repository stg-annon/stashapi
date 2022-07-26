import re, sys

from requests.structures import CaseInsensitiveDict

from .stashbox import StashBoxInterface

from . import gql_fragments
from . import log as stash_logger

from .types import PhashDistance
from .classes import GQLWrapper
from .classes import SQLiteWrapper

class StashInterface(GQLWrapper):
	port = ""
	url = ""
	headers = {
		"Accept-Encoding": "gzip, deflate",
		"Content-Type": "application/json",
		"Accept": "application/json",
		"Connection": "keep-alive",
		"DNT": "1"
	}
	cookies = {}

	def __init__(self, conn:dict={}, fragments:list=[]):
		global log

		conn = CaseInsensitiveDict(conn)

		log = conn.get("Logger", stash_logger)

		# Session cookie for authentication
		self.cookies = {}
		if conn.get("SessionCookie"):
			self.cookies['session'] = conn['SessionCookie']['Value']

		scheme = conn.get('Scheme', 'http')
		domain = conn.get('Domain', 'localhost')

		self.port = conn.get('Port', 9999)

		# Stash GraphQL endpoint
		self.url = f'{scheme}://{domain}:{self.port}/graphql'
		log.debug(f"Using stash GraphQl endpoint at {self.url}")

		try:
			# test query to ensure good connection
			self.call_gql("query Configuration {configuration{general{stashes{path}}}}")
		except Exception as e:
			log.error(f"Could not connect to Stash at {self.url}")
			log.error(e)
			sys.exit()

		self.sql = None
		if domain in ['localhost', '127.0.0.1']:
			sql_file = self.call_gql("query dbPath{configuration{general{databasePath}}}")
			self.sql = SQLiteWrapper(sql_file["configuration"]["general"]["databasePath"])
			
		self.sbox_endpoints = {}

		self.fragments = {}
		if isinstance(fragments, str):
			fragments = [fragments]
		if isinstance(fragments, list):
			for f in fragments:
				if isinstance(f, str):
					self.parse_fragments(f)

		self.parse_fragments(gql_fragments.STASHAPP)


	def __match_alias_item(self, search, items):
		item_matches = {}
		for item in items:
			if re.match(rf'{search}$', item["name"], re.IGNORECASE):
				log.debug(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using primary name')
				item_matches[item["id"]] = item
				break
			if not item["aliases"]:
				continue
			for alias in item["aliases"]:
				if re.match(rf'{search}$', alias.strip(), re.IGNORECASE):
					log.info(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using alias')
					item_matches[item["id"]] = item
		return list(item_matches.values())

	def __match_performer_alias(self, search, performers):
		item_matches = {}
		for item in performers:
			if re.match(rf'{search}$', item["name"], re.IGNORECASE):
				log.info(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using primary name')
				item_matches[item["id"]] = item
				break
			if not item["aliases"]:
				continue
			for alias in item["aliases"]:
				parsed_alias = alias.strip()
				if ":" in alias:
					parsed_alias = alias.split(":")[-1].strip()
				if re.match(rf'{search}$', parsed_alias, re.IGNORECASE):
					log.info(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using alias')
					item_matches[item["id"]] = item
		return list(item_matches.values())

	def call_gql(self, query, variables={}):
		return self._callGraphQL(query, variables)

	def graphql_configuration(self):
		query = """
			query Configuration {
				configuration {
					...ConfigData
				}
			}
		"""
		
		result = self._callGraphQL(query)
		return result['configuration']

	def metadata_scan(self, paths:list=[]):
		query = """
		mutation metadataScan($input:ScanMetadataInput!) {
			metadataScan(input: $input)
		}
		"""
		variables = {
			'input': {
				'paths' : paths,
				'useFileMetadata': False,
				'stripFileExtension': False,
				'scanGeneratePreviews': False,
				'scanGenerateImagePreviews': False,
				'scanGenerateSprites': False,
				'scanGeneratePhashes': True
			}
		}
		result = self._callGraphQL(query, variables)
		return result

	# Tag CRUD
	def find_tag(self, tag_in, create=False):

		# assume input is a tag ID if int
		if isinstance(tag_in, int):
			query = "query FindTag($id: ID!) { findTag(id: $id) { ...stashTag } }"
			variables = {"id": tag_in }
			result = self._callGraphQL(query, variables)
			return result["findTag"]

		name = None
		if isinstance(tag_in, dict):
			if tag_in.get("stored_id"):
				return self.find_tag(int(tag_in["stored_id"]))
			if tag_in.get("name"):
				name = tag_in["name"]
		if isinstance(tag_in, str):
			name = tag_in

		if not name:
			log.warning(f'find_tag expects int, str, or dict not {type(tag_in)} "{tag_in}"')
			return

		for tag in self.find_tags(q=name):
			if tag["name"].lower() == name.lower():
				return tag
			if any(name.lower() == a.lower() for a in tag["aliases"] ):
				return tag
		if create:
			return self.create_tag({"name":name})
	def create_tag(self, tag):
		query = """
			mutation tagCreate($input:TagCreateInput!) {
				tagCreate(input: $input){
					...stashTag
				}
			}
		"""
		variables = {'input': tag}
		result = self._callGraphQL(query, variables)
		return result["tagCreate"]
	def update_tag(self, tag_update):
		query = """
		mutation TagUpdate($input: TagUpdateInput!) {
			tagUpdate(input: $input) {
				id
			}
		}
		"""
		variables = {'input': tag_update}

		self._callGraphQL(query, variables)
	def destroy_tag(self, tag_id):
		query = """
			mutation tagDestroy($input: TagDestroyInput!) {
				tagDestroy(input: $input)
			}
		"""
		variables = {'input': {
			'id': tag_id
		}}

		self._callGraphQL(query, variables)

	# Tags CRUD
	def find_tags(self, q="", f={}, fragment=None):
		query = """
			query FindTags($filter: FindFilterType, $tag_filter: TagFilterType) {
				findTags(filter: $filter, tag_filter: $tag_filter) {
					count
					tags {
						...stashTag
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashTag', fragment, query)

		variables = {
		"filter": {
			"direction": "ASC",
			"per_page": -1,
			"q": q,
			"sort": "name"
		},
		"tag_filter": f
		}
		
		result = self._callGraphQL(query, variables)
		return result["findTags"]["tags"]

	# Performer CRUD
	def find_performer(self, performer_data, create=False):

		# assume input is a tag ID if int
		if isinstance(performer_data, int):
			query = "query FindPerformer($id: ID!) { findPerformer(id: $id) { ...stashPerformer } }"
			variables = {"id": performer_data }
			result = self._callGraphQL(query, variables)
			return result["findPerformer"]

		name = None
		if isinstance(performer_data, dict):
			if performer_data.get("stored_id"):
				return self.find_tag(int(performer_data["stored_id"]))
			if performer_data.get("name"):
				name = performer_data["name"]
		if isinstance(performer_data, str):
			name = performer_data

		if not name:
			log.warning(f'find_tag expects int, str, or dict not {type(performer_data)} "{performer_data}"')
			return

		name = name.strip()
		performer_data = {"name": name}

		performers = self.find_performers(q=name)
		for p in performers:
			if not p.get("aliases"):
				continue
			alias_delim = re.search(r'(\/|\n|,|;)', p["aliases"])
			if alias_delim:
				p["aliases"] = p["aliases"].split(alias_delim.group(1))
			elif len(p["aliases"]) > 0:
				p["aliases"] = [p["aliases"]]
			else:
				log.warning(f'Could not determine delim for aliases "{p["aliases"]}"')

		performer_matches = self.__match_performer_alias(name, performers)

		# none if multiple results from a single name performer
		if len(performer_matches) > 1 and name.count(' ') == 0:
			return None
		elif len(performer_matches) > 0:
			return performer_matches[0] 


		if create:
			log.info(f'Create missing performer: "{name}"')
			return self.create_performer(performer_data)
	def create_performer(self, performer_data):
		query = """
			mutation($input: PerformerCreateInput!) {
				performerCreate(input: $input) {
					id
				}
			}
		"""

		variables = {'input': performer_data}

		result = self._callGraphQL(query, variables)
		return result['performerCreate']['id']
	def update_performer(self, performer_data):
		query = """
			mutation performerUpdate($input:PerformerUpdateInput!) {
				performerUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': performer_data}

		result = self._callGraphQL(query, variables)
		return result['performerUpdate']['id']
	# TODO delete_performer()

	# Performers CRUD
	def find_performers(self, q="", f={}, fragment=None):
		query =  """
			query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {
				findPerformers(filter: $filter, performer_filter: $performer_filter) {
					count
					performers {
						...stashPerformer
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashPerformer', fragment, query)

		variables = {
			"filter": {
				"q": q,
				"per_page": -1,
				"sort": "name",
				"direction": "ASC"
			},
			"performer_filter": f
		}

		result = self._callGraphQL(query, variables)
		return result['findPerformers']['performers']

	# Studio CRUD
	def find_studio(self, studio, create=False, domain_pattern=r'[^.]*\.[^.]{2,3}(?:\.[^.]{2,3})?$'):
		if not studio.get("name"):
			return None

		name = studio["name"]

		studio_matches = []

		if re.match(domain_pattern, name):
			url_search = self.find_studios(f={
				"url":{ "value": name, "modifier": "INCLUDES" }
			})
			for s in url_search:
				if re.search(rf'{name}',s["url"]):
					log.info(f'matched "{name}" to {s["url"]} using URL')
					studio_matches.append(s)

		name_results = self.find_studios(q=name)
		studio_matches.extend(self.__match_alias_item(name, name_results))

		if len(studio_matches) > 1 and name.count(' ') == 0:
			return None
		elif len(studio_matches) > 0:
			return studio_matches[0] 

		if create:
			log.info(f'Create missing studio: "{name}"')
			return self.create_studio(studio)
	def create_studio(self, studio):
		query = """
			mutation($name: String!) {
				studioCreate(input: { name: $name }) {
					id
				}
			}
		"""
		variables = {
			'name': studio['name']
		}

		result = self._callGraphQL(query, variables)
		studio['id'] = result['studioCreate']['id']

		return self.update_studio(studio)
	def update_studio(self, studio):
		query = """
			mutation StudioUpdate($input:StudioUpdateInput!) {
				studioUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': studio}

		result = self._callGraphQL(query, variables)
		return result["studioUpdate"]["id"]
	# TODO delete_studio()

	def get_studio(self, studio, get_root_parent=False):
		query =  """
		query FindStudio($studio_id: ID!) {
			findStudio(id: $studio_id) {
				...stashStudio
			}
		}
		"""
		variables = {
			"studio_id": studio.get("id")
		}
		result = self._callGraphQL(query, variables)
		studio = result['findStudio']

		if get_root_parent and studio and studio.get("parent_studio"):
			return self.get_studio(studio["parent_studio"], get_root_parent=True)
		return studio
		

	def find_studios(self, q="", f={}, fragment=None):
		query =  """
		query FindStudios($filter: FindFilterType, $studio_filter: StudioFilterType) {
			findStudios(filter: $filter, studio_filter: $studio_filter) {
			count
			studios {
				...stashStudio
			}
			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashStudio', fragment, query)

		variables = {
			"filter": {
			"q": q,
			"per_page": -1,
			"sort": "name",
			"direction": "ASC"
			},
			"studio_filter": f
		}

		result = self._callGraphQL(query, variables)
		return result['findStudios']['studios']

	# Movie CRUD
	def find_movie(self, movie, create=False):

		name = movie["name"]
		movies = self.find_movies(q=name)

		movie_matches = self.__match_alias_item(name, movies)

		if len(movie_matches) > 0:
			if len(movie_matches) == 1:
				return movie_matches[0]
			else:
				log.warning(f'Too many matches for movie "{name}"')
				return None

		if create:
			log.info(f'Creating missing Movie "{name}"')
			return self.create_movie(movie)
	def create_movie(self, movie):
		name = movie["name"]
		query = """
			mutation($name: String!) {
				movieCreate(input: { name: $name }) {
					id
				}
			}
		"""
		variables = {'name': name}
		result = self._callGraphQL(query, variables)
		movie['id'] = result['movieCreate']['id']
		return self.update_movie(movie)
	def update_movie(self, movie):
		query = """
			mutation MovieUpdate($input:MovieUpdateInput!) {
				movieUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': movie}

		result = self._callGraphQL(query, variables)
		return result['movieUpdate']['id']
	# TODO delete_movie()

	# Movies CRUD
	def find_movies(self, q="", f={}, fragment=None):
		query = """
			query FindMovies($filter: FindFilterType, $movie_filter: MovieFilterType) {
				findMovies(filter: $filter, movie_filter: $movie_filter) {
					count
					movies {
						...stashMovie
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashMovie', fragment, query)

		variables = {
			"filter": {
				"per_page": -1,
				"q": q
			},
			"movie_filter": f
		}
		
		result = self._callGraphQL(query, variables)
		return result['findMovies']['movies']

	#Gallery CRUD
	def create_gallery(self, path:str=""):
		if path:
			return self.metadata_scan([path])
	# TODO find_gallery()
	def update_gallery(self, gallery_data):
		query = """
			mutation GalleryUpdate($input:GalleryUpdateInput!) {
				galleryUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': gallery_data}

		result = self._callGraphQL(query, variables)
		return result["galleryUpdate"]["id"]
	def destroy_gallery(self, gallery_ids, delete_file=False, delete_generated=True):
		if isinstance(gallery_ids, int):
			gallery_ids = [gallery_ids]
		if not isinstance(gallery_ids, list):
			raise Exception("destroy_gallery only accepts an int or list of ints")

		query = """
		mutation galleryDestroy($input:GalleryDestroyInput!) {
			galleryDestroy(input: $input)
		}
		"""
		variables = {
			"input": {
				"delete_file": delete_file,
				"delete_generated": delete_generated,
				"ids": gallery_ids
			}
		}
		result = self._callGraphQL(query, variables)
		return result['galleryDestroy']

	# BULK Gallery
	def find_galleries(self, q="", f={}, fragment=None):
		query = """
			query FindGalleries($filter: FindFilterType, $gallery_filter: GalleryFilterType) {
				findGalleries(gallery_filter: $gallery_filter, filter: $filter) {
					count
					galleries {
						...stashGallery
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashGallery', fragment, query)

		variables = {
			"filter": {
				"q": q,
				"per_page": -1,
				"sort": "path",
				"direction": "ASC"
			},
			"gallery_filter": f
		}

		result = self._callGraphQL(query, variables)
		return result['findGalleries']['galleries']


	# Scene CRUD
	def create_scene(self, path:str=""):
		if path:
			return self.metadata_scan([path])
	def find_scene(self, id:int, fragment=None):
		query = """
		query FindScene($scene_id: ID) {
			findScene(id: $scene_id) {
				...stashScene
			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashScene', fragment, query)

		variables = {"scene_id": id}

		result = self._callGraphQL(query, variables)
		return result['findScene']
	def update_scene(self, update_input):
		query = """
			mutation sceneUpdate($input:SceneUpdateInput!) {
				sceneUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': update_input}

		result = self._callGraphQL(query, variables)
		return result["sceneUpdate"]["id"]
	def destroy_scene(self, scene_id, delete_file=False):
		query = """
		mutation SceneDestroy($input:SceneDestroyInput!) {
			sceneDestroy(input: $input)
		}
		"""
		variables = {
			"input": {
				"delete_file": delete_file,
				"delete_generated": True,
				"id": scene_id
			}
		}
			
		result = self._callGraphQL(query, variables)
		return result['sceneDestroy']
	
	# BULK Scenes
	def create_scenes(self, paths:list=[]):
		return self.metadata_scan(paths)
	def find_scenes(self, f={}, filter={"per_page": -1}, fragment=None):
		query = """
		query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
			findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
				count
				scenes {
					...stashScene
				}
			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashScene', fragment, query)

		variables = {
			"filter": filter,
			"scene_filter": f
		}
			
		result = self._callGraphQL(query, variables)
		return result['findScenes']['scenes']
	def update_scenes(self, updates_input):
		query = """
			mutation BulkSceneUpdate($input:BulkSceneUpdateInput!) {
				bulkSceneUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': updates_input}

		result = self._callGraphQL(query, variables)
		return result["bulkSceneUpdate"]
	def destroy_scenes(self, scene_ids, delete_file=False):
		query = """
		mutation ScenesDestroy($input:ScenesDestroyInput!) {
			scenesDestroy(input: $input)
		}
		"""
		variables = {
			"input": {
				"delete_file": delete_file,
				"delete_generated": True,
				"ids": scene_ids
			}
		}
			
		result = self._callGraphQL(query, variables)
		return result['scenesDestroy']

	def find_scene_markers(self, scene_id, fragment=None) -> list:
		query = """
			query FindSceneMarkers($scene_id: ID) {
				findScene(id: $scene_id) {
					scene_markers {
						...stashSceneMarker
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashSceneMarker', fragment, query)

		variables = { "scene_id": scene_id }
		return self._callGraphQL(query, variables)["findScene"]["scene_markers"]

	def create_scene_marker(self, marker_create_input:dict, fragment=None):
		query = """
			mutation SceneMarkerCreate($marker_input: SceneMarkerCreateInput!) {
				sceneMarkerCreate(input: $marker_input) {
					...stashSceneMarker
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashSceneMarker', fragment, query)
			
		variables = { "marker_input": marker_create_input }
		return self._callGraphQL(query, variables)["sceneMarkerCreate"]
	def destroy_scene_markers(self, scene_id:int):
		query = """
			mutation DestroySceneMarkers($marker_id: ID!) {
				sceneMarkerDestroy(id: $marker_id)
			}
		"""
		scene_markers = self.find_scene_markers(scene_id, fragment="id")
		for marker in scene_markers:
			self._callGraphQL(query, {"marker_id": marker["id"]})

	def merge_scene_markers(self, target_scene_id: int, source_scene_ids: list):
		existing_marker_timestamps = [marker["seconds"] for marker in self.find_scene_markers(target_scene_id)]

		markers_to_merge = []
		for source_scene_id in source_scene_ids:
			markers_to_merge.extend(self.find_scene_markers(source_scene_id))

		created_markers = []
		for marker in markers_to_merge:
			if marker["seconds"] in existing_marker_timestamps:
				# skip existing marker
				# TODO merge missing data between markers
				continue
			marker_id = self.create_scene_marker({
				"title": marker["title"],
				"seconds": marker["seconds"],
				"scene_id": target_scene_id,
				"primary_tag_id": marker["primary_tag"]["id"],
				"tag_ids": [t["id"] for t in marker["tags"]],
			})
			created_markers.append(marker_id)
		return created_markers

	def merge_scenes(self, target_scene_id:int, source_scene_ids:list, exclusions={}):

		min_scene_fragment="""
			title
			details
			url
			date
			rating
			studio { id }
			galleries { id }
			performers { id }
			tags { id }
			movies { movie { id } scene_index }
		"""

		merged_markers = self.merge_scene_markers(target_scene_id, source_scene_ids)
		log.info(f"Merged {len(merged_markers)} markers from {source_scene_ids} to {target_scene_id}")

		target_meta = self.find_scene(target_scene_id, fragment=min_scene_fragment)

		for source_id in source_scene_ids:
			source_data = self.find_scene(source_id, fragment=min_scene_fragment)
			scene_update = {
				"ids": [target_scene_id],
				"gallery_ids": {
					 "ids": [ g["id"] for g in source_data["galleries"] if g["id"] not in exclusions.get("gallery_ids",[]) ],
					 "mode": "ADD"
				},
				"performer_ids": {
					 "ids": [ p["id"] for p in source_data["performers"] if p["id"] not in exclusions.get("performer_ids",[]) ],
					 "mode": "ADD"
				},
				"tag_ids": {
					 "ids": [ t["id"] for t in source_data["tags"] if t["id"] not in exclusions.get("tag_ids",[]) ],
					 "mode": "ADD"
				},
				"movie_ids": {
					 "ids": [ sm["movie"]["id"] for sm in source_data["movies"] ],
					 "mode": "ADD"
				},
			}
			if source_data.get("studio"):
				scene_update["studio_id"] = source_data["studio"]["id"]


			sdate = source_data.get("date")
			tdate = target_meta.get("date", "9999-99-99")
			if tdate == None:
				tdate = "9999-99-99"
			if sdate and tdate > sdate:
				scene_update["date"] = source_data["date"]
			if source_data.get("url"):
				scene_update["url"] = source_data["url"]
				
			updated_scene_ids = self.update_scenes(scene_update)

		return updated_scene_ids

	# Scraper Operations
	def reload_scrapers(self):
		query = """ 
			mutation ReloadScrapers {
				reloadScrapers
			}
		"""
		
		result = self._callGraphQL(query)
		return result["reloadScrapers"]
	
	def list_performer_scrapers(self, type):
		query = """
		query ListPerformerScrapers {
			listPerformerScrapers {
			  id
			  name
			  performer {
				supported_scrapes
			  }
			}
		  }
		"""
		ret = []
		result = self._callGraphQL(query)
		for r in result["listPerformerScrapers"]:
			if type in r["performer"]["supported_scrapes"]:
				ret.append(r["id"])
		return ret
	def list_scene_scrapers(self, type):
		query = """
		query listSceneScrapers {
			listSceneScrapers {
			  id
			  name
			  scene{
				supported_scrapes
			  }
			}
		  }
		"""
		ret = []
		result = self._callGraphQL(query)
		for r in result["listSceneScrapers"]:
			if type in r["scene"]["supported_scrapes"]:
				ret.append(r["id"])
		return ret
	def list_gallery_scrapers(self, type):
		query = """
		query ListGalleryScrapers {
			listGalleryScrapers {
			  id
			  name
			  gallery {
				supported_scrapes
			  }
			}
		  }
		"""
		ret = []
		result = self._callGraphQL(query)
		for r in result["listGalleryScrapers"]:
			if type in r["gallery"]["supported_scrapes"]:
				ret.append(r["id"])
		return ret
	def list_movie_scrapers(self, type):
		query = """
		query listMovieScrapers {
			listMovieScrapers {
			  id
			  name
			  movie {
				supported_scrapes
			  }
			}
		  }
		"""
		ret = []
		result = self._callGraphQL(query)
		for r in result["listMovieScrapers"]:
			if type in r["movie"]["supported_scrapes"]:
				ret.append(r["id"])
		return ret

	# Fragment Scrape
	def scrape_scene(self, scraper_id:int, scene):

		scene_id = None
		scene_input = {}

		try:
			if isinstance(scene, str):
				scene_id = int(scene)
			if isinstance(scene, int):
				scene_id = scene
			if isinstance(scene, dict):
				scene_id = int(scene.get("id"))
				scene_input = {
					"title": scene["title"],
					"details": scene["details"],
					"url": scene["url"],
					"date": scene["date"],
					"remote_site_id": None
				}
			if not isinstance(scene_id, int):
				raise Exception("scene_id must be an int")
		except:
			log.warning('Unexpected Object passed to scrape_single_scene')
			log.warning(f'Type: {type(scene)}')
			log.warning(f'{scene}')

		query = """query ScrapeSingleScene($source: ScraperSourceInput!, $input: ScrapeSingleSceneInput!) {
			scrapeSingleScene(source: $source, input: $input) {
			  ...scrapedScene
			}
		  }
		"""
		
		variables = {
			"source": {
				"scraper_id": scraper_id
			},
			"input": {
				"query": None,
				"scene_id": scene_id,
				"scene_input": scene_input
			}
		}
		result = self._callGraphQL(query, variables)
		if not result:
			return None
		scraped_scene_list = result["scrapeSingleScene"]
		if len(scraped_scene_list) == 0:
			return None
		else:
			return scraped_scene_list[0]
	def scrape_gallery(self, scraper_id:int, gallery):
		query = """query ScrapeGallery($scraper_id: ID!, $gallery: GalleryUpdateInput!) {
			scrapeGallery(scraper_id: $scraper_id, gallery: $gallery) {
			  ...scrapedGallery
			}
		  }
		"""
		variables = {
			"scraper_id": scraper_id,
			"gallery": {
				"id": gallery["id"],
				"title": gallery["title"],
				"url": gallery["url"],
				"date": gallery["date"],
				"details": gallery["details"],
				"rating": gallery["rating"],
				"scene_ids": [],
				"studio_id": None,
				"tag_ids": [],
				"performer_ids": [],
			}
		}

		result = self._callGraphQL(query, variables)
		return result["scrapeGallery"]
	def scrape_performer(self, scraper_id:int, performer):
		query = """query ScrapePerformer($scraper_id: ID!, $performer: ScrapedPerformerInput!) {
			scrapePerformer(scraper_id: $scraper_id, performer: $performer) {
			  ...scrapedPerformer
			}
		  }
		"""
		variables = {
			"scraper_id": scraper_id,
			"performer": {
			"name": performer["name"],
			"gender": None,
			"url": performer["url"],
			"twitter": None,
			"instagram": None,
			"birthdate": None,
			"ethnicity": None,
			"country": None,
			"eye_color": None,
			"height": None,
			"measurements": None,
			"fake_tits": None,
			"career_length": None,
			"tattoos": None,
			"piercings": None,
			"aliases": None,
			"tags": None,
			"image": None,
			"details": None,
			"death_date": None,
			"hair_color": None,
			"weight": None,
		}
		}
		result = self._callGraphQL(query, variables)
		return result["scrapePerformer"]

	# URL Scrape
	def scrape_scene_url(self, url):
		query = """
			query($url: String!) {
				scrapeSceneURL(url: $url) {
					...scrapedScene
				}
			}
		"""
		variables = { 'url': url }
		scraped_scene = self._callGraphQL(query, variables)['scrapeSceneURL']
		if scraped_scene and not scraped_scene.get("url"):
			scraped_scene["url"] = url
		return scraped_scene
	def scrape_movie_url(self, url):
		query = """
			query($url: String!) {
				scrapeMovieURL(url: $url) {
					...scrapedMovie
				}
			}
		"""
		variables = { 'url': url }
		scraped_movie = self._callGraphQL(query, variables)['scrapeMovieURL']
		if scraped_movie and not scraped_movie.get("url"):
			scraped_movie["url"] = url
		return scraped_movie
	def scrape_gallery_url(self, url):
		query = """
			query($url: String!) {
				scrapeGalleryURL(url: $url) {
					...scrapedGallery 
				}
			}
		"""
		variables = { 'url': url }
		scraped_gallery = self._callGraphQL(query, variables)['scrapeGalleryURL']
		if scraped_gallery and not scraped_gallery.get("url"):
			scraped_gallery["url"] = url
		return scraped_gallery
	def scrape_performer_url(self, url):
		query = """
			query($url: String!) {
				scrapePerformerURL(url: $url) {
					...scrapedPerformer
				}
			}
		"""
		variables = { 'url': url }
		scraped_performer = self._callGraphQL(query, variables)['scrapePerformerURL']
		if scraped_performer and not scraped_performer.get("url"):
			scraped_performer["url"] = url
		return scraped_performer

	#Identify
	def get_identify_config(self):
		query= """
		query getIdentifyConfig{
			configuration {
				defaults {
					identify {
						options {
							fieldOptions {
								field
								strategy
								createMissing
							}
							setCoverImage
							setOrganized
							includeMalePerformers
						}
					}
				}
			}
		}"""
		result = self._callGraphQL(query)
		return result['configuration']['defaults']['identify']['options']
	def get_identify_source_config(self, source_identifier):
		query= """
		query getIdentifySourceConfig{
			configuration {
				defaults {
					identify {
						sources {
							source {
								stash_box_endpoint
								scraper_id
							}
							options {
								fieldOptions {
									field
									strategy
									createMissing
								}
								setCoverImage
								setOrganized
								includeMalePerformers
							}
						}
					}
				}
			}
		}"""
		configs = self._callGraphQL(query)['configuration']['defaults']['identify']['sources']
		for c in configs:
			if c['source']['stash_box_endpoint'] == source_identifier:
				return c['options']
			if c['source']['scraper_id'] == source_identifier:
				return c['options']
		return None

	# Stash Box
	def get_stashbox_interface(self, sbox_target_endpoint) -> StashBoxInterface:
		# intended for internal use for when this weapper wants to query one of many stashbox endpoints for a given stash_id
		for endpoint, sbox in self.sbox_endpoints.items():
			if sbox_target_endpoint == endpoint:
				return sbox
		sbox_config = {"logger": log}.update(self.get_stashbox_connection(sbox_target_endpoint))
		sbox = StashBoxInterface(sbox_config)
		self.sbox_endpoints[sbox.url] = sbox
		return sbox
	def get_stashbox_connection(self, sbox_endpoint, return_index=False):
		for sbox_idx, sbox_cfg in enumerate(self.get_stashbox_connections()):
			if sbox_endpoint in sbox_cfg["endpoint"]:
				if return_index:
					return sbox_idx
				else:
					return sbox_cfg			
		log.error(f'could not find stash-box conection to "{sbox_endpoint}"')
		return {}
	def get_stashbox_connections(self):
		query = """
		query configuration{
			configuration {
				general {
					stashBoxes {
						name
						endpoint
						api_key
					} 
				}
			}
		}"""
		result = self._callGraphQL(query)
		return result["configuration"]["general"]["stashBoxes"]
	def stashbox_scene_scraper(self, scene_ids, stashbox_index:int=0):
		query = """
			query QueryStashBoxScene($input: StashBoxSceneQueryInput!) {
				queryStashBoxScene(input: $input) {
					...scrapedScene
				}
			}
		"""
		variables = {
			"input": {
				"scene_ids": scene_ids,
				"stash_box_index": stashbox_index
			}
		}

		result = self._callGraphQL(query, variables)

		return result["queryStashBoxScene"]
	def stashbox_submit_scene_fingerprints(self, scene_ids, stashbox_index:int=0):
		query = """
			mutation SubmitStashBoxFingerprints($input: StashBoxFingerprintSubmissionInput!) {
				submitStashBoxFingerprints(input: $input)
			}
		"""
		variables = {
			"input": {
				"scene_ids": scene_ids,
				"stash_box_index": stashbox_index
			}
		}

		result = self._callGraphQL(query, variables)
		return result['submitStashBoxFingerprints']
	def stashbox_identify_task(self, scene_ids, stashbox_endpoint="https://stashdb.org/graphql"):
		query = """
			mutation MetadataIdentify($input: IdentifyMetadataInput!) {
			metadataIdentify(input: $input)
			}
		"""
		variables = {}
		variables["input"] = {
			"options": self.get_identify_config(),
			"sceneIDs": scene_ids,
			"sources": [
				{
					"options": self.get_identify_source_config(stashbox_endpoint),
					"source": {
						"stash_box_endpoint": stashbox_endpoint
					}
				}
			]
		}
		return self._callGraphQL(query, variables)

	def submit_scene_draft(self, scene_id, sbox_index=0):
		query = """
			mutation submitScenesToStashbox($input: StashBoxDraftSubmissionInput!) {
				  submitStashBoxSceneDraft(input: $input)
			}
		"""
		variables = { "input": {
			"id": scene_id,
			"stash_box_index": sbox_index
		} }
		result = self._callGraphQL(query, variables)
		return result['submitStashBoxSceneDraft']

	def find_duplicate_scenes(self, distance: PhashDistance=PhashDistance.EXACT, fragment=None):
		query = """
			query FindDuplicateScenes($distance: Int) {
				  findDuplicateScenes(distance: $distance) {
					...stashSceneSlim
					__typename
				  }
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.stashSceneSlim', fragment, query)

		variables = { "distance": distance }
		result = self._callGraphQL(query, variables)
		return result['findDuplicateScenes']
