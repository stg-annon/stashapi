import re, sys

from requests.structures import CaseInsensitiveDict

from . import log as stash_logger

from .types import PhashDistance
from .classes import GQLWrapper
from .classes import SQLiteWrapper
from .classes import StashVersion

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

	def __init__(self, conn:dict={}, fragments:list[str]=[]):
		conn = CaseInsensitiveDict(conn)

		self.log = conn.get("Logger", stash_logger)

		if conn.get("ApiKey"):
			self.headers["ApiKey"] = conn["ApiKey"]

		# Session cookie for authentication
		self.cookies = {}
		if conn.get("SessionCookie"):
			self.cookies['session'] = conn['SessionCookie']['Value']

		scheme = conn.get('Scheme', 'http')
		domain = conn.get('Domain', 'localhost')

		self.port = conn.get('Port', 9999)

		# Stash GraphQL endpoint
		self.url = f'{scheme}://{domain}:{self.port}/graphql'

		try:
			# test query to ensure good connection
			version = self.stash_version()
		except Exception as e:
			self.log.error(f"Could not connect to Stash at {self.url}")
			self.log.error(e)
			sys.exit()

		self.log.debug(f'Using stash ({version}) endpoint at {self.url}')

		self.fragments = self._getFragmentsIntrospection(["Scene","Studio","Performer","Image","Gallery"])
		for fragment in fragments:
			self.parse_fragments(fragment)

	def _parse_obj_for_ID(self, param, str_key="name"):
		if isinstance(param, str):
			try:
				return int(param)
			except:
				return {str_key: param.strip()}
		elif isinstance(param, dict):
			if param.get("stored_id"):
				return int(param["stored_id"])
			if param.get("id"):
				return int(param["id"])
		return param

	def __genric_find(self, query, item, fragment:tuple[str, str]=(None, None)):
		item_id = None
		if isinstance(item, dict):
			if item.get("stored_id"):
				item_id = int(item["stored_id"])
			if item.get("id"):
				item_id = int(item["id"])
		if isinstance(item, int):
			item_id = item
		if not item_id:
			return
		pattern, substitution = fragment
		if substitution:
			query = re.sub(pattern, substitution, query)
		result = self._callGraphQL(query,  {"id":item_id})
		queryType = list(result.keys())[0]
		return result[queryType]

	def __match_alias_item(self, search, items):
		item_matches = {}
		for item in items:
			if re.match(rf'{search}$', item["name"], re.IGNORECASE):
				self.log.debug(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using primary name')
				item_matches[item["id"]] = item
				return list(item_matches.values())
		for item in items:
			if not item["aliases"]:
				continue
			for alias in item["aliases"]:
				if re.match(rf'{search}$', alias.strip(), re.IGNORECASE):
					self.log.info(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using alias')
					item_matches[item["id"]] = item
		return list(item_matches.values())

	def __match_performer_alias(self, search, performers):
		performer_matches = {}

		# attempt to match exclusivly to primary name
		for p in performers:
			if p.get("disambiguation"):
				self.log.debug(f'ignore primary name with disambiguation "{p["name"]}" ({p["disambiguation"]}) pid:{p["id"]}')
				continue

			if re.match(rf'{search}$', p["name"], re.IGNORECASE):
				self.log.info(f'matched performer "{search}" to "{p["name"]}" ({p["id"]}) using primary name')
				performer_matches[p["id"]] = p
				return list(performer_matches.values())

		# no match on primary name attempt aliases
		for item in performers:
			if not item["aliases"]:
				continue
			for alias in item["aliases"]:
				parsed_alias = alias.strip()
				if ":" in alias:
					parsed_alias = alias.split(":")[-1].strip()
				if re.match(rf'{search}$', parsed_alias, re.IGNORECASE):
					self.log.info(f'matched performer "{search}" to "{item["name"]}" ({item["id"]}) using alias')
					performer_matches[item["id"]] = item
		return list(performer_matches.values())

	def call_gql(self, query, variables={}):
		return self._callGraphQL(query, variables)

	def stash_version(self):
		result = self._callGraphQL("query StashVersion{ version { build_time hash version } }")
		return StashVersion(result["version"])

	def get_sql_interface(self):
		if "localhost" in self.url or "127.0.0.1" in self.url:
			sql_file = self.call_gql("query dbPath{configuration{general{databasePath}}}")
			return SQLiteWrapper(sql_file["configuration"]["general"]["databasePath"])
		else:
			raise Exception(f"cannot create sql interface on a non local stash instance ({self.url})")

	def graphql_configuration(self):
		query = """
			query Configuration {
				configuration {
					...ConfigResult
				}
			}
		"""

		result = self._callGraphQL(query)
		return result['configuration']

	def metadata_scan(self, paths:list=[], flags={}):
		query = """
		mutation MetadataScan($input:ScanMetadataInput!) {
			metadataScan(input: $input)
		}
		"""
		scan_metadata_input = {"paths": paths}
		if flags:
			scan_metadata_input.update(flags)
		else:
			scan_metadata_input.update({
				'useFileMetadata': False,
				'stripFileExtension': False,
				'scanGeneratePreviews': False,
				'scanGenerateImagePreviews': False,
				'scanGenerateSprites': False,
				'scanGeneratePhashes': True
			})
		result = self._callGraphQL(query, {"input": scan_metadata_input})
		return result

	def metadata_clean(self, paths:list=[], dry_run=False):
		if not paths:
			return

		query = """
		mutation MetadataClean($input:CleanMetadataInput!) {
			metadataClean(input: $input)
		}
		"""

		clean_metadata_input = {
			"paths": paths,
			"dryRun": dry_run
		}
		result = self._callGraphQL(query, {"input": clean_metadata_input})
		return result


	def destroy_files(self, file_ids:list=[]):
		if not file_ids:
			return

		query = """
		mutation DeleteFiles($ids: [ID!]!) {
			deleteFiles(ids: $ids)
		}
		"""
		variables = {'ids': file_ids}
		result = self._callGraphQL(query, variables)
		return result["deleteFiles"]

	# Tag CRUD
	def create_tag(self, tag_in:dict) -> dict:
		"""creates tag in stash

		Args:
			 tag_in (dict): TagCreateInput to create a tag.

		Returns:
			 dict: stash Tag dict
		"""

		query = """
			mutation tagCreate($input:TagCreateInput!) {
				tagCreate(input: $input){
					...Tag
				}
			}
		"""
		variables = {'input': tag_in}
		result = self._callGraphQL(query, variables)
		return result["tagCreate"]
	def find_tag(self, tag_in, create=False) -> dict:
		"""looks for tag from stash matching aliases

		Args:
			 tag_in (int, str, dict): Tag ID, name, or dict to find.
			 create (bool, optional): Creates the tag if it does not exist. Defaults to False.

		Returns:
			 dict: stash Tag dict
		"""

		# assume input is an ID if int
		if isinstance(tag_in, int):
			return self.__genric_find(
				"query FindTag($id: ID!) { findTag(id: $id) { ...Tag } }",
				tag_in
			)

		name = None
		if isinstance(tag_in, dict):
			if tag_in.get("stored_id"):
				try:
					stored_id = int(tag_in["stored_id"])
					return self.find_tag(stored_id)
				except:
					del tag_in["stored_id"]
			if tag_in.get("name"):
				name = tag_in["name"]
		if isinstance(tag_in, str):
			name = tag_in
			tag_in = {"name": name}

		if not name:
			self.log.warning(f'find_tag expects int, str, or dict not {type(tag_in)} "{tag_in}"')
			return

		for tag in self.find_tags(q=name):
			if tag["name"].lower() == name.lower():
				return tag
			if any(name.lower() == a.lower() for a in tag["aliases"] ):
				return tag
		if create:
			return self.create_tag(tag_in)
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
	def destroy_tag(self, tag_id:int):
		"""deeltes tag from stash

		Args:
			 tag_id (int, str): tag ID from stash
		"""

		query = """
			mutation tagDestroy($input: TagDestroyInput!) {
				tagDestroy(input: $input)
			}
		"""
		variables = {'input': {
			'id': tag_id
		}}

		self._callGraphQL(query, variables)

	# BULK Tags
	def find_tags(self, f:dict={}, filter:dict={"per_page": -1}, q:str="", fragment:str=None, get_count:bool=False) -> list[dict]:
		"""gets tags matching filter/query

		Args:
			 f (TagFilterType, optional): See playground for details. Defaults to {}.
			 filter (FindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
			 q (str, optional): query string, same search bar in stash. Defaults to "".
			 fragment (str, optional): override for gqlFragment. Defaults to "...Tag". example override 'fargment="id name"'
			 get_count (bool, optional): returns tuple (count, [tags]) where count is the number of results from the query, useful when pageing. Defaults to False.

		Returns:
			 _type_: list of tags, or tuple of (count, [tags])
		"""

		query = """
			query FindTags($filter: FindFilterType, $tag_filter: TagFilterType) {
				findTags(filter: $filter, tag_filter: $tag_filter) {
					count
					tags {
						...Tag
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Tag', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"tag_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result["findTags"]["count"], result["findTags"]["tags"]
		else:
			return result["findTags"]["tags"]

	# Performer CRUD
	def create_performer(self, performer_in:dict) -> dict:
		"""creates performer in stash

		Args:
			 performer_in (PerformerCreateInput): performer to create

		Returns:
			 dict: stash performer object
		"""
		query = """
			mutation($input: PerformerCreateInput!) {
				performerCreate(input: $input) {
					...Performer
				}
			}
		"""

		variables = {'input': performer_in}

		result = self._callGraphQL(query, variables)
		return result['performerCreate']
	def find_performer(self, performer_in, create=False) -> dict:
		"""looks for performer from stash matching aliases

		Args:
			 performer_in (int, str, dict): int of performer id, str of performer name/alias, dict of performer oject
			 create (bool, optional): create performer if not found. Defaults to False.

		Returns:
			 dict: performer from stash
		"""

		# assume input is an ID if int
		if isinstance(performer_in, int):
			return self.__genric_find(
				"query FindPerformer($id: ID!) { findPerformer(id: $id) { ...Performer } }",
				performer_in,
			)

		name = None
		if isinstance(performer_in, dict):
			if performer_in.get("stored_id"):
				return self.find_performer(int(performer_in["stored_id"]))
			if performer_in.get("name"):
				name = performer_in["name"]
		if isinstance(performer_in, str):
			name = performer_in

		if not name:
			self.log.warning(f'find_performer() expects int, str, or dict not {type(performer_in)} "{performer_in}"')
			return

		name = name.strip()
		performer_in = {"name": name}

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
				self.log.warning(f'Could not determine delim for aliases "{p["aliases"]}"')

		performer_matches = self.__match_performer_alias(name, performers)

		# none if multiple results from a single name performer
		if len(performer_matches) > 1 and name.count(' ') == 0:
			return None
		elif len(performer_matches) > 0:
			return performer_matches[0]

		if create:
			self.log.info(f'Create missing performer: "{name}"')
			return self.create_performer(performer_in)
	def update_performer(self, performer_in:dict) -> dict:
		"""updates existing performer

		Args:
			 performer_in (PerformerUpdateInput):  update for existing stash performer

		Returns:
			 dict: stash performer object
		"""

		query = """
			mutation performerUpdate($input:PerformerUpdateInput!) {
				performerUpdate(input: $input) {
					...Performer
				}
			}
		"""
		variables = {'input': performer_in}

		result = self._callGraphQL(query, variables)
		return result['performerUpdate']
	# TODO destroy_performer()
	# TODO merge_performers(self, source, destination, values={}):

	# Performers CRUD
	def find_performers(self, f:dict={}, filter:dict={"per_page": -1}, q="", fragment:dict=None, get_count:bool=False) -> list[dict]:
		"""get performers matching filter/query

		Args:
			 f (PerformerFilterType, optional): See playground for details. Defaults to {}.
			 filter (FindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
			 q (str, optional): query string, same search bar in stash. Defaults to "".
			 fragment (dict, optional):  override for gqlFragment. Defaults to "...Performer". example override 'fargment="id name"'
			 get_count (bool, optional): returns tuple (count, [performers]) where count is the number of results from the query, useful when pageing. Defaults to False.

		Returns:
			 _type_: list of performer objects or tuple with count and list (count, [performers])
		"""

		query =  """
			query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {
				findPerformers(filter: $filter, performer_filter: $performer_filter) {
					count
					performers {
						...Performer
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Performer', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"performer_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result['findPerformers']['count'], result['findPerformers']['performers']
		else:
			return result['findPerformers']['performers']
	def update_performers(self, bulk_performer_update_input:dict):
		query = """
			mutation BulkPerformerUpdate($input:BulkPerformerUpdateInput!) {
				bulkPerformerUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': bulk_performer_update_input}

		result = self._callGraphQL(query, variables)
		return result["bulkPerformerUpdate"]

	# Studio CRUD
	def create_studio(self, studio_create_input:dict) -> dict:
		"""create studio in stash

		Args:
			 studio (StudioCreateInput): See playground for details

		Returns:
			 dict: stash studio object
		"""
		query = """
			mutation StudioCreate($input: StudioCreateInput!) {
				studioCreate(input: $input) {
					...Studio
				}
			}
		"""
		variables = {
			'input': studio_create_input
		}

		result = self._callGraphQL(query, variables)
		return result['studioCreate']
	def find_studio(self, studio, fragment=None, create=False) -> dict:
		"""looks for studio from stash matching aliases and URLs if name is like a url

		Args:
			 studio (int, str, dict): int, str, dict of studio to search for
			 create (bool, optional): create studio if not found. Defaults to False.
		Returns:
			 dict: stash studio object
		"""
		studio = self._parse_obj_for_ID(studio)
		if isinstance(studio, int):
			return self.__genric_find(
				"query FindStudio($id: ID!) { findStudio(id: $id) { ...Studio } }",
				studio,
				[r'\.\.\.Studio', fragment]
			)
		if not studio:
			self.log.warning(f'find_studio() expects int, str, or dict not {type(studio)} "{studio}"')
			return

		studio_matches = []

		if studio.get("url"):
			url_search = self.find_studios(f={
				"url":{ "value": studio["url"], "modifier": "INCLUDES" }
			}, fragment="id name")
			if len(url_search) == 1:
				studio_matches.extend(url_search)

		if studio.get("name"):
			studio["name"] = studio["name"].strip()
			name_results = self.find_studios(q=studio["name"], fragment="id name aliases")
			studio_matches.extend(self.__match_alias_item(studio["name"], name_results))

		if len(studio_matches) > 1 and studio["name"].count(' ') == 0:
			return None
		elif len(studio_matches) > 0:
			return self.find_studio(studio_matches[0]["id"], fragment=fragment)

		if create:
			self.log.info(f'Create missing studio: "{studio["name"]}"')
			return self.create_studio(studio)
	def update_studio(self, studio:dict):
		"""update existing stash studio

		Args:
			 studio (StudioUpdateInput): see playground for details

		Returns:
			 dict: stash studio object
		"""

		query = """
			mutation StudioUpdate($input:StudioUpdateInput!) {
				studioUpdate(input: $input) {
					...Studio
				}
			}
		"""
		variables = {'input': studio}

		result = self._callGraphQL(query, variables)
		return result["studioUpdate"]
	# TODO destroy_studio()

	# BULK Studios
	def find_studios(self, f:dict={}, filter:dict={"per_page": -1}, q:str="", fragment:str=None, get_count:bool=False):
		"""get studios matching filter/query

		Args:
			 f (StudioFilterType, optional): See playground for details. Defaults to {}.
			 filter (FindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
			 q (str, optional): query string, same search bar in stash. Defaults to "".
			 fragment (_type_, optional): override for gqlFragment. Defaults to "...Studio". example override 'fargment="id name"'
			 get_count (bool, optional): returns tuple (count, [studios]) where count is the number of results from the query, useful when pageing. Defaults to False.

		Returns:
			 _type_: list of studio ojbests from stash, or tuple (count, [studios])
		"""

		query =  """
		query FindStudios($filter: FindFilterType, $studio_filter: StudioFilterType) {
			findStudios(filter: $filter, studio_filter: $studio_filter) {
			count
			studios {
				...Studio
			}
			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Studio', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"studio_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result['findStudios']['count'], result['findStudios']['studios']
		else:
			return result['findStudios']['studios']

	# Movie CRUD
	def create_movie(self, movie_in):
		if isinstance(movie_in, str):
			movie_in = {"name": movie_in}
		if not isinstance(movie_in, dict):
			self.log.warning(f"could not create movie from {movie_in}")
			return
		query = """
			mutation($input: MovieCreateInput!) {
				movieCreate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': movie_in}
		result = self._callGraphQL(query, variables)
		return result['movieCreate']
	def find_movie(self, movie_in, create=False):
		# assume input is an ID if int
		if isinstance(movie_in, int):
			return self.__genric_find(
				"query FindMovie($id: ID!) { findMovie(id: $id) { ...Movie } }",
				movie_in
			)

		name = None
		if isinstance(movie_in, dict):
			if movie_in.get("stored_id"):
				return self.find_movie(int(movie_in["stored_id"]))
			if movie_in.get("id"):
				return self.find_movie(int(movie_in["id"]))
			if movie_in.get("name"):
				name = movie_in["name"]
		if isinstance(movie_in, str):
			name = movie_in

		movies = self.find_movies(q=name)

		movie_matches = self.__match_alias_item(name, movies)

		if len(movie_matches) > 0:
			if len(movie_matches) == 1:
				return movie_matches[0]
			else:
				self.log.warning(f'Too many matches for movie "{name}"')
				return None

		if create:
			self.log.info(f'Creating missing Movie "{name}"')
			return self.create_movie(movie_in)
	def update_movie(self, movie_in):
		query = """
			mutation MovieUpdate($input:MovieUpdateInput!) {
				movieUpdate(input: $input) {
					...Movie
				}
			}
		"""
		variables = {'input': movie_in}

		result = self._callGraphQL(query, variables)
		return result['movieUpdate']
	# TODO destroy_movie()

	# BULK Movies
	def find_movies(self, f:dict={}, filter:dict={"per_page": -1}, q="", fragment=None, get_count=False):
		query = """
			query FindMovies($filter: FindFilterType, $movie_filter: MovieFilterType) {
				findMovies(filter: $filter, movie_filter: $movie_filter) {
					count
					movies {
						...Movie
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Movie', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"movie_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result['findMovies']['count'], result['findMovies']['movies']
		else:
			return result['findMovies']['movies']

	#Gallery CRUD
	def create_gallery(self, path:str=""):
		if path:
			return self.metadata_scan([path])
	def find_gallery(self, gallery_in, fragment=None):
		if isinstance(gallery_in, int):
			return self.__genric_find(
				"query FindGallery($id: ID!) { findGallery(id: $id) { ...Gallery } }",
				gallery_in,
				(r'\.\.\.Gallery', fragment)
			)

		if isinstance(gallery_in, dict):
			if gallery_in.get("id"):
				return self.find_tag(int(gallery_in["id"]))

		if isinstance(gallery_in, str):
			try:
				return self.find_tag(int(gallery_in))
			except:
				self.log.warning(f"could not parse {gallery_in} to Gallery ID (int)")
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
	def find_galleries(self, f:dict={}, filter:dict={"per_page": -1}, q="", fragment=None, get_count=False):
		query = """
			query FindGalleries($filter: FindFilterType, $gallery_filter: GalleryFilterType) {
				findGalleries(gallery_filter: $gallery_filter, filter: $filter) {
					count
					galleries {
						...Gallery
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Gallery', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"gallery_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result['findGalleries']['count'], result['findGalleries']['galleries']
		else:
			return result['findGalleries']['galleries']
	def update_galleries(self, galleries_input):
		query = """
			mutation BulkGalleryUpdate($input:BulkGalleryUpdateInput!) {
				bulkGalleryUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': galleries_input}

		result = self._callGraphQL(query, variables)
		return result["bulkGalleryUpdate"]

	# Image CRUD
	def create_image(self, path:str=""):
		if path:
			return self.metadata_scan([path])
	def find_image(self, image_in, fragment=None):
		if isinstance(image_in, int):
			return self.__genric_find(
				"query FindImage($id: ID!) { findImage(id: $id) { ...Image } }",
				image_in,
				(r'\.\.\.Image', fragment),
			)

		if isinstance(image_in, dict):
			if image_in.get("stored_id"):
				return self.find_tag(int(image_in["stored_id"]))
			if image_in.get("id"):
				return self.find_tag(int(image_in["id"]))

		if isinstance(image_in, str):
			try:
				return self.find_tag(int(image_in))
			except:
				self.log.warning(f"could not parse {image_in} to Image ID (int)")

		self.log.warning(f'find_image expects int, str, or dict not {type(image_in)} "{image_in}"')
	def update_image(self, update_input):
		query = """
			mutation ImageUpdate($input:ImageUpdateInput!) {
				imageUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': update_input}

		result = self._callGraphQL(query, variables)
		return result["imageUpdate"]
	def destroy_image(self, image_id, delete_file=False):
		query = """
		mutation ImageDestroy($input:ImageDestroyInput!) {
			imageDestroy(input: $input)
		}
		"""
		variables = {
			"input": {
				"delete_file": delete_file,
				"delete_generated": True,
				"id": image_id
			}
		}

		result = self._callGraphQL(query, variables)
		return result['imageDestroy']

	# BULK Images
	def find_images(self, f:dict={}, filter:dict={"per_page": -1}, q="", fragment=None, get_count=False):
		query = """
		query FindImages($filter: FindFilterType, $image_filter: ImageFilterType, $image_ids: [Int!]) {
  			findImages(filter: $filter, image_filter: $image_filter, image_ids: $image_ids) {
	 			count
	 			images {
					...Image
	 			}
  			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Image', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"image_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result['findImages']['count'], result['findImages']['images']
		else:
			return result['findImages']['images']
	def update_images(self, updates_input):
		query = """
			mutation BulkImageUpdate($input:BulkImageUpdateInput!) {
				bulkImageUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': updates_input}

		result = self._callGraphQL(query, variables)
		return result["bulkImageUpdate"]
	def destroy_images(self, image_ids:list, delete_file=False):
		query = """
		mutation ImagesDestroy($input:ImagesDestroyInput!) {
			imagesDestroy(input: $input)
		}
		"""
		variables = {
			"input": {
				"delete_file": delete_file,
				"delete_generated": True,
				"ids": image_ids
			}
		}

		result = self._callGraphQL(query, variables)
		return result['imagesDestroy']

	# Scene CRUD
	def create_scene(self, path:str=""):
		if path:
			return self.metadata_scan([path])
	def find_scene(self, id:int, fragment=None):
		query = """
		query FindScene($scene_id: ID) {
			findScene(id: $scene_id) {
				...Scene
			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Scene', fragment, query)

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
	def find_scenes(self, f:dict={}, filter:dict={"per_page": -1}, q:str="", fragment=None, get_count=False):
		query = """
		query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
			findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
				count
				scenes {
					...Scene
				}
			}
		}
		"""
		if fragment:
			query = re.sub(r'\.\.\.Scene', fragment, query)

		filter["q"] = q
		variables = {
			"filter": filter,
			"scene_filter": f
		}

		result = self._callGraphQL(query, variables)
		if get_count:
			return result['findScenes']['count'], result['findScenes']['scenes']
		else:
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
	def merge_scenes(self, source, destination, values={}):

		if isinstance(source, str):
			source = int(source)
		if isinstance(destination, str):
			destination = int(destination)

		if isinstance(source, int):
			source = [source]

		if not isinstance(source, list):
			raise Exception("merge_scenes() source attribute must be a list of ints")
		if not isinstance(destination, int):
			raise Exception("merge_scenes() destination attribute must be an int")

		query = """
			mutation SceneMerge($merge_input: SceneMergeInput!) {
				sceneMerge(input: $merge_input) {
					id
				}
			}
		"""
		values["id"] = destination
		merge_input = {
			"source": source,
			"destination": destination,
			"values": values,
		}

		return self._callGraphQL(query, {"merge_input":merge_input})["sceneMerge"]

	# Markers CRUD
	def find_scene_markers(self, scene_id, fragment=None) -> list:
		query = """
			query FindSceneMarkers($scene_id: ID) {
				findScene(id: $scene_id) {
					scene_markers {
						...SceneMarker
					}
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.SceneMarker', fragment, query)

		variables = { "scene_id": scene_id }
		return self._callGraphQL(query, variables)["findScene"]["scene_markers"]
	def create_scene_marker(self, marker_create_input:dict, fragment=None):
		query = """
			mutation SceneMarkerCreate($marker_input: SceneMarkerCreateInput!) {
				sceneMarkerCreate(input: $marker_input) {
					...SceneMarker
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.SceneMarker', fragment, query)

		variables = { "marker_input": marker_create_input }
		return self._callGraphQL(query, variables)["sceneMarkerCreate"]
	def destroy_scene_marker(self, marker_id:int):
		query = """
			mutation DestroySceneMarkers($marker_id: ID!) {
				sceneMarkerDestroy(id: $marker_id)
			}
		"""
		self._callGraphQL(query, {"marker_id": marker_id})

	# BULK Markers
	def destroy_scene_markers(self, scene_id:int):
		scene_markers = self.find_scene_markers(scene_id, fragment="id")
		for marker in scene_markers:
			self.destroy_scene_marker(marker["id"])
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

	# Scene Utils
	def destroy_scene_stash_id(self, stash_id):
		scenes = self.find_scenes(f={
			"stash_id": {
				"value": stash_id,
				"modifier": "EQUALS"
			}
		},fragment="id stash_ids {endpoint stash_id}")

		for scene in scenes:
			scene["stash_ids"] = [sid for sid in scene["stash_ids"] if sid["stash_id"] != stash_id ]
			self.update_scene(scene)
	def find_duplicate_scenes(self, distance: PhashDistance=PhashDistance.EXACT, fragment=None):
		query = """
			query FindDuplicateScenes($distance: Int) {
				findDuplicateScenes(distance: $distance) {
					...SceneSlim
				}
			}
		"""
		if fragment:
			query = re.sub(r'\.\.\.SceneSlim', fragment, query)

		variables = { "distance": distance }
		result = self._callGraphQL(query, variables)
		return result['findDuplicateScenes']

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
			self.log.warning('Unexpected Object passed to scrape_single_scene')
			self.log.warning(f'Type: {type(scene)}')
			self.log.warning(f'{scene}')

		query = """query ScrapeSingleScene($source: ScraperSourceInput!, $input: ScrapeSingleSceneInput!) {
			scrapeSingleScene(source: $source, input: $input) {
			  ...ScrapedScene
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
			  ...ScrapedGallery
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
			  ...ScrapedPerformer
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
					...ScrapedScene
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
					...ScrapedMovie
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
					...ScrapedGallery
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
					...ScrapedPerformer
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
	def get_stashbox_connection(self, sbox_endpoint):
		for sbox_idx, sbox_cfg in enumerate(self.get_stashbox_connections()):
			if sbox_endpoint in sbox_cfg["endpoint"]:
				sbox_cfg["index"] = sbox_idx
				return sbox_cfg
		self.log.error(f'could not find stash-box conection to "{sbox_endpoint}"')
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
					...ScrapedScene
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
