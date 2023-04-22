import re, sys, time, traceback

from requests.structures import CaseInsensitiveDict

from . import log as stash_logger

from .stash_types import StashItem
from .stash_types import PhashDistance
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
			self.log.error(traceback.format_exc())
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

	def __generic_find(self, query, item, fragment:tuple[str, str]=(None, None)):
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
		search = re.escape(search)
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

		# attempt to match exclusively to primary name
		for p in performers:
			if p.get("disambiguation"):
				self.log.debug(f'ignore primary name with disambiguation "{p["name"]}" ({p["disambiguation"]}) pid:{p["id"]}')
				continue

			if re.match(rf'{search}$', p["name"], re.IGNORECASE):
				self.log.debug(f'matched performer "{search}" to "{p["name"]}" ({p["id"]}) using primary name')
				performer_matches[p["id"]] = p
				return list(performer_matches.values())

		# no match on primary name attempt aliases
		for p in performers:
			aliases = []
			# new versions of stash NOTE: wont be needed after performer alias matching
			if p.get("alias_list"):
				aliases = p["alias_list"]
			# old versions of stash
			if p.get("aliases"):
				if not isinstance(p["aliases"], str):
					self.log.warning(f'Expecting type str for performer aliases not {type(p["aliases"])}')
					return
				alias_delim = re.search(r'(\/|\n|,|;)', p["aliases"])
				if alias_delim:
					p["aliases"] = p["aliases"].split(alias_delim.group(1))
				elif len(p["aliases"]) > 0:
					p["aliases"] = [p["aliases"]]
				else:
					self.log.warning(f'Could not determine delim for aliases "{p["aliases"]}"')

			if not aliases:
				continue
			for alias in aliases:
				parsed_alias = alias.strip()
				if re.match(rf'{search}$', parsed_alias, re.IGNORECASE):
					self.log.info(f'matched performer "{search}" to "{p["name"]}" ({p["id"]}) using alias')
					performer_matches[p["id"]] = p
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

	def find_job(self, job_id):
		query = "query FindJob($input:FindJobInput!) { findJob(input: $input){ ...Job } }"
		result = self._callGraphQL(query, {"input": {"id":job_id}})
		return result["findJob"]
	
	def wait_for_job(self, job_id, status="FINISHED", period=1.5, timeout=120):
		timeout_value = time.time() + timeout
		while time.time() < timeout_value:
			job = self.find_job(job_id)
			if not job:
				return False
			if job["status"] == status:
				return True
			if job["status"] in ["FINISHED", "CANCELLED"]:
				return False
			time.sleep(period)
		raise Exception("Hit timeout waiting for Job to complete")

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
				'scanGenerateCovers': True,
				'scanGeneratePreviews': False,
				'scanGenerateImagePreviews': False,
				'scanGenerateSprites': False,
				'scanGeneratePhashes': True,
				'scanGenerateThumbnails': False
			})
		result = self._callGraphQL(query, {"input": scan_metadata_input})
		return result["metadataScan"]

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
			return self.__generic_find(
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
		"""deletes tag from stash

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
	def destroy_tags(self, tag_ids:list[int]):
		"""deletes tags from stash

		Args:
			 tag_ids ([int]): tag IDs from stash to delete
		"""

		query = """
			mutation tagsDestroy($ids: [ID!]!) {
				tagsDestroy(ids: $ids)
			}
		"""

		self._callGraphQL(query, {'ids': tag_ids})



	# BULK Tags
	def find_tags(self, f:dict={}, filter:dict={"per_page": -1}, q:str="", fragment:str=None, get_count:bool=False) -> list[dict]:
		"""gets tags matching filter/query

		Args:
			 f (TagFilterType, optional): See playground for details. Defaults to {}.
			 filter (FindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
			 q (str, optional): query string, same search bar in stash. Defaults to "".
			 fragment (str, optional): override for gqlFragment. Defaults to "...Tag". example override 'fragment="id name"'
			 get_count (bool, optional): returns tuple (count, [tags]) where count is the number of results from the query, useful when paging. Defaults to False.

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
	def find_performer(self, performer, create=False, fragment=None) -> dict:
		"""looks for performer from stash matching aliases

		Args:
			 performer (int, str, dict): int of performer id, str of performer name/alias, dict of performer object
			 create (bool, optional): create performer if not found. Defaults to False.

		Returns:
			 dict: performer from stash
		"""
		performer = self._parse_obj_for_ID(performer)
		# assume input is an ID if int
		if isinstance(performer, int):
			return self.__generic_find(
				"query FindPerformer($id: ID!) { findPerformer(id: $id) { ...Performer } }",
				performer,
				[r'\.\.\.Performer', fragment]
			)
		if not performer:
			self.log.warning(f'find_performer() expects int, str, or dict not {type(performer)} "{performer}"')
			return

		performer_search = self.find_performers(q=performer["name"], fragment="id name alias_list")
		performer_matches = self.__match_performer_alias(performer["name"], performer_search)

		# self.log.warning(performer_matches)

		# none if multiple results from a single name performer
		if len(performer_matches) > 1 and performer["name"].count(' ') == 0:
			return None
		elif len(performer_matches) > 0:
			return self.find_performer(performer_matches[0]["id"])

		if create:
			self.log.info(f'Create missing performer: "{performer["name"]}"')
			return self.create_performer(performer)
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
	def destroy_performer(self, performer_ids):
		if isinstance(performer_ids, int):
			performer_ids = [performer_ids]
		if not isinstance(performer_ids, list):
			raise Exception("destroy_gallery only accepts an int or list of ints")

		query = """
		mutation performersDestroy($performer_ids:[ID!]!) {
			performersDestroy(ids: $performer_ids)
		}
		"""
		result = self._callGraphQL(query, {"performer_ids": performer_ids})
		return result['performersDestroy']
	def merge_performers(self, source, destination, values={}):

		performer_update_fragment = """
			id
			name
			disambiguation
			url
			twitter
			instagram
			gender
			birthdate
			death_date
			ethnicity
			country
			eye_color
			height_cm
			measurements
			fake_tits
			career_length
			tattoos
			piercings
			alias_list
			favorite
			tags { id }
			stash_ids { endpoint stash_id }
			rating
			rating100
			details
			hair_color
			weight
			ignore_auto_tag
		"""

		if isinstance(source, str):
			source = int(source)
		if isinstance(destination, str):
			destination = int(destination)

		if isinstance(source, int):
			source = [source]

		if not isinstance(source, list):
			raise Exception("merge_performers() source attribute must be a list of ints")
		if not isinstance(destination, int):
			raise Exception("merge_performers() destination attribute must be an int")

		destination = self.find_performer(destination, fragment=performer_update_fragment)
		sources = [self.find_performer(pid) for pid in source]

		performer_update = {}
		for attr in destination:
			if attr == "tags":
				performer_update["tag_ids"] = [t["id"] for t in destination["tags"]]
			else:
				performer_update[attr] = destination[attr]		

		def pick_string(s1, s2):
			if len(s1.replace(" ", "")) > len(s2.replace(" ", "")):
				return s1
			else:
				return s2
		ignore_attrs = ["id","name"]
		use_longest_string = [
			"disambiguation",
			"measurements",
			"career_length",
			"tattoos",
			"piercings",
			"details",
		]
		for d_attr in performer_update:
			if d_attr in ignore_attrs:
				continue
			for source in sources:
				if d_attr in use_longest_string:
					performer_update[d_attr] = pick_string(performer_update[d_attr], source[d_attr])
					continue
				if d_attr == "stash_ids":
					existing_ids = [id["stash_id"] for id in performer_update["stash_ids"]]
					performer_update["stash_ids"].extend([id for id in performer_update["stash_ids"] if id["stash_id"] not in existing_ids])
					continue
				if d_attr == "tags":
					performer_update["tag_ids"].extend([t["id"] for t in source["tags"]])
					performer_update["tag_ids"] = list(set(performer_update["tag_ids"]))
					continue
				if d_attr == "alias_list":
					performer_update["alias_list"].append(source["name"])
					performer_update["alias_list"].extend(source["alias_list"])
					performer_update["alias_list"] = list(set(performer_update["alias_list"]))
					continue
				if not performer_update[d_attr] and source[d_attr]:
					performer_update[d_attr] = source[d_attr]
		performer_update["alias_list"] = [a for a in performer_update["alias_list"] if a != performer_update["name"]]
		
		self.update_performer(performer_update)

		source_ids = [p["id"] for p in sources]
		# reassign items with performers
		scenes = self.find_scenes(f={"performers": {"value":source_ids, "modifier":"INCLUDES"}}, fragment="id")
		if scenes:
			self.update_scenes({
				"ids": [s["id"] for s in scenes],
				"performer_ids": {
					"ids": [destination["id"]],
					"mode": "ADD"
				}
			})

		galleries = self.find_galleries(f={"performers": {"value":source_ids, "modifier":"INCLUDES"}}, fragment="id")
		if galleries:
			self.update_galleries({
				"ids": [g["id"] for g in galleries],
				"performer_ids": {
					"ids": [destination["id"]],
					"mode": "ADD"
				}
			})

		self.destroy_performer(source_ids)

	# Performers CRUD
	def find_performers(self, f:dict={}, filter:dict={"per_page": -1}, q="", fragment:dict=None, get_count:bool=False) -> list[dict]:
		"""get performers matching filter/query

		Args:
			 f (PerformerFilterType, optional): See playground for details. Defaults to {}.
			 filter (FindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
			 q (str, optional): query string, same search bar in stash. Defaults to "".
			 fragment (dict, optional):  override for gqlFragment. Defaults to "...Performer". example override 'fragment="id name"'
			 get_count (bool, optional): returns tuple (count, [performers]) where count is the number of results from the query, useful when paging. Defaults to False.

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
			return self.__generic_find(
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
			 fragment (_type_, optional): override for gqlFragment. Defaults to "...Studio". example override 'fragment="id name"'
			 get_count (bool, optional): returns tuple (count, [studios]) where count is the number of results from the query, useful when paging. Defaults to False.

		Returns:
			 _type_: list of studio objects from stash, or tuple (count, [studios])
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
			return self.__generic_find(
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

	# Gallery CRUD
	def create_gallery(self, path:str=""):
		if path:
			return self.metadata_scan([path])
	def find_gallery(self, gallery_in, fragment=None):
		if isinstance(gallery_in, int):
			return self.__generic_find(
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

	# Gallery Images
	def update_gallery_images(self, gallery_images_input):
		mode = gallery_images_input.get("mode")
		if not mode:
			raise Exception("update_gallery_images() expects mode argument")
		mode = mode.strip().upper()
		if mode == "ADD":
			return self.add_gallery_images(gallery_images_input["id"], gallery_images_input["image_ids"])
		if mode == "REMOVE":
			return self.remove_gallery_images(gallery_images_input["id"], gallery_images_input["image_ids"])
		if mode == "SET":
			gallery_images = self.find_images({
				"galleries": {"value":gallery_images_input["id"],
		  		"modifier":"INCLUDES_ALL"}},
				fragment="id"
			)
			# remove all existing images
			self.remove_gallery_images(gallery_images_input["id"], [f["id"] for f in gallery_images])
			# set gallery images to input or return if no value provided
			if not gallery_images_input.get("image_ids"):
				return
			return self.add_gallery_images(gallery_images_input["id"], gallery_images_input["image_ids"])
	def remove_gallery_images(self, gallery_id, image_ids):
		query = """
			mutation RemoveGalleryImages($gallery_id: ID!, $image_ids: [ID!]!) {
				removeGalleryImages(input: { gallery_id: $gallery_id, image_ids: $image_ids }) 
			}
		"""
		variables = {
			'gallery_id': gallery_id,
			'image_ids': image_ids
		}
		result = self._callGraphQL(query, variables)
		return result["removeGalleryImages"]
	def add_gallery_images(self, gallery_id, image_ids):
		query = """
			mutation AddGalleryImages($gallery_id: ID!, $image_ids: [ID!]!) {
				addGalleryImages(input: { gallery_id: $gallery_id, image_ids: $image_ids })
			}
		"""
		variables = {
			'gallery_id': gallery_id,
			'image_ids': image_ids
		}
		result = self._callGraphQL(query, variables)
		return result["addGalleryImages"]

	# Gallery Chapters
	def create_gallery_chapter(self, chapter_data):
		query = """
			mutation GalleryChapterCreate($input:GalleryChapterCreateInput!) {
				galleryChapterCreate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': chapter_data}
		result = self._callGraphQL(query, variables)
		return result["galleryChapterCreate"]["id"]
	def update_gallery_chapter(self, chapter_data):
		query = """
			mutation GalleryChapterUpdate($input:GalleryChapterUpdateInput!) {
				galleryChapterUpdate(input: $input) {
					id
				}
			}
		"""
		variables = {'input': chapter_data}
		result = self._callGraphQL(query, variables)
		return result["galleryChapterUpdate"]["id"]
	def destroy_gallery_chapter(self, chapter_id):
		query = """
			mutation GalleryChapterDestroy($chapter_id:ID!) {
				galleryChapterDestroy(id: $chapter_id) {
					id
				}
			}
		"""
		variables = {'chapter_id': chapter_id}
		result = self._callGraphQL(query, variables)
		return result["galleryChapterDestroy"]["id"]


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
			return self.__generic_find(
				"query FindImage($id: ID!) { findImage(id: $id) { ...Image } }",
				image_in,
				(r'\.\.\.Image', fragment),
			)
		image_id = None
		if isinstance(image_in, dict):
			if image_in.get("stored_id"):
				image_id = int(image_in["stored_id"])
			if image_in.get("id"):
				image_id = int(image_in["id"])
		if isinstance(image_in, str):
			try:
				image_id = int(image_in)
			except:
				self.log.warning(f"could not parse {image_in} to Image ID (int)")
		if image_id:
			return self.find_image(image_id, fragment)

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
	def create_scene(self, scene_create_input:dict={}):
		query = """
		query SceneCrate($input: SceneCreateInput!) {
			sceneCreate(input: $input) {
				id
			}
		}
		"""

		variables = {"input": scene_create_input}

		result = self._callGraphQL(query, variables)
		return result['sceneCreate']

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
	def create_scenes(self, scene_create_inputs:list=[]):
		responses = []
		for input in scene_create_inputs:
			responses.append(self.create_scene(input))
		return responses
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

	def list_scrapers(self, types:list[StashItem]):
		query = """
		query ListScrapers ($types: [ScrapeContentType!]!) {
			listScrapers(types: $types) {
			  id
			  name
			  performer { supported_scrapes }
			  scene { supported_scrapes }
			  gallery { supported_scrapes }
			  movie { supported_scrapes }
			}
		  }
		"""
		result = self._callGraphQL(query, {"types":[t.value for t in types]})
		return result["listScrapers"]
	def list_performer_scrapers(self):
		return [{k: scraper[k] for k in ["id", "name", "performer"]} for scraper in self.list_scrapers([StashItem.PERFORMER])]
	def list_scene_scrapers(self):
		return [{k: scraper[k] for k in ["id", "name", "scene"]} for scraper in self.list_scrapers([StashItem.SCENE])]
	def list_gallery_scrapers(self):
		return [{k: scraper[k] for k in ["id", "name", "gallery"]} for scraper in self.list_scrapers([StashItem.GALLERY])]
	def list_movie_scrapers(self):
		return [{k: scraper[k] for k in ["id", "name", "movie"]} for scraper in self.list_scrapers([StashItem.MOVIE])]

	# Fragment Scrape
	def scrape_scene(self, scraper_id:int, scene):

		scene_id = None
		scene_input = {}

		sid = self._parse_obj_for_ID(scene)
		if isinstance(sid, int):
			scene_id = sid

		if not scene_id:
			self.log.warning('Unexpected Object passed to scrape_scene')
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
		query = "query($url: String!) { scrapeSceneURL(url: $url) { ...ScrapedScene } }"
		return self._callGraphQL(query, { 'url': url })['scrapeSceneURL']
	def scrape_movie_url(self, url):
		query = "query($url: String!) { scrapeMovieURL(url: $url) { ...ScrapedMovie } }"
		return self._callGraphQL(query, { 'url': url })['scrapeMovieURL']
	def scrape_gallery_url(self, url):
		query = "query($url: String!) { scrapeGalleryURL(url: $url) { ...ScrapedGallery } }"
		return self._callGraphQL(query, { 'url': url })['scrapeGalleryURL']
	def scrape_performer_url(self, url):
		query = "query($url: String!) { scrapePerformerURL(url: $url) { ...ScrapedPerformer } }"
		return self._callGraphQL(query, { 'url': url })['scrapePerformerURL']

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
		self.log.error(f'could not find stash-box connection to "{sbox_endpoint}"')
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
