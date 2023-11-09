import re, math, requests
from enum import Enum

from requests.structures import CaseInsensitiveDict

from .classes import GQLWrapper
from .log import StashLogger

from .tools import file_to_base64, url_to_base64, str_compare

STASH_ID_PATTERN = r'(?:[0-9a-fA-F]){8}-(?:[0-9a-fA-F]){4}-(?:[0-9a-fA-F]){4}-(?:[0-9a-fA-F]){4}-(?:[0-9a-fA-F]){12}'

class StashboxTarget(Enum):
	SCENE = "SCENE"
	STUDIO = "STUDIO"
	PERFORMER = "PERFORMER"
	TAG = "TAG"

class StashBoxInterface(GQLWrapper):
	port = None
	url = None
	headers = {
		"Accept-Encoding": "gzip, deflate",
		"Content-Type": "application/json",
		"Accept": "application/json",
		"Connection": "keep-alive",
		"DNT": "1"
	}
	cookies = {}

	def __init__(self, conn={}, fragments:list[str]=[]):

		conn = CaseInsensitiveDict(conn)
		
		self.log = conn.get("Logger", StashLogger())
		
		self.url = conn.get('endpoint', "https://stashdb.org/graphql")
		self.endpoint = self.url

		if not self.url:
			raise Exception("REQUIRED key 'endpoint' not provided in connection dict")

		if "metadataapi.net" in self.url:
			self.log.warning("metadataapi.net is not an actual Stash-Box instance, things may not work as expected, use their API")

		stash = conn.get("stash")
		if stash:
			c = stash.get_stashbox_connection(self.url)	
			api_key = c.get("api_key")
			if not api_key:
				raise Exception(f"Could not find api_key for '{self.url}' with provided stash connection")
		else:
			api_key = conn.get('api_key', None)
			if not api_key:
				raise Exception(f"REQUIRED key 'api_key' not provided in connection dict ({conn})")

		self.headers['ApiKey'] = api_key
		try:
			# test query to check connection
			r = self._callGraphQL("query Me{me {name email}}")
			self.log.debug(f'Connected to "{self.url}" as {r["me"]["name"]} ({r["me"]["email"]})')
		except Exception as e:
			self.log.exit(f"Could not connect to Stash-Box at {self.url}", e)

		global_overrides = {
			"Scene": "{ id }",
			"Studio": "{ id name }",
			"Performer": "{ id }",
			"Edit": "{ id }",
			"Tag": "{ id name }",
			"URL": "{ type url }",
		}
		fragment_overrides = {
			"Studio": { "performers": None }
		}
		self.fragments = self._getFragmentsIntrospection(global_overrides, fragment_overrides)
		for fragment in fragments:
			self.parse_fragments(fragment)

	def __match_search_item(self, input, __find, search_attr="name"):
		search = None
		if isinstance(input, dict) and input.get(search_attr):
			search = input[search_attr]
		if isinstance(input, str):
			search = input
		if not search:
			self.log.warning(f"could not find a string search target from '{input}'")
			return
		
		matches = set()
		for tag in __find(search):
			if str_compare(tag[search_attr], search):
				matches.add(tag["id"])
			if tag.get("aliases") and any(str_compare(alias, search) for alias in tag["aliases"] ):
				matches.add(tag["id"])
		matches = list(matches)
		if len(matches) > 1:
			self.log.warning(f"Matched multiple tags with '{search}' {matches}")
			return
		if len(matches) == 1:
			return matches[0]

	def __find_by_id(self, query, item, fragment:tuple[str, str]=(None, None)):
		item_id = None
		if isinstance(item, dict):
			if item.get("id") and isinstance(item["id"], str):
				item = item["id"]
		if isinstance(item, str):
			if re.match(STASH_ID_PATTERN, item):
				item_id = item
		if not item_id:
			return
		pattern, substitution = fragment
		if substitution:
			query = re.sub(pattern, substitution, query)
		result = self._callGraphQL(query,  {"id":item_id})
		queryType = list(result.keys())[0]
		return result[queryType]

	def _paginate_query(self, query, type_input, pages=-1, callback=None):
		"""auto paginate graphql query and return pages results

		Args:
			query (str): graphql query string
			type_input (dict): graphql query input
			pages (int, optional): number of pages to get results for, -1 for all pages. Defaults to -1.
			callback (_function_, optional): callback function to run results against between page calls. Defaults to None.

		Returns:
			dict: all results from query up to specified page
		"""
		result = self._callGraphQL(query, {"input": type_input})

		queryType = list(result.keys())[0]
		result = result[queryType]

		itemType = list(result.keys())[1]
		items = result[itemType]
		if callback != None:
			callback(items)

		if pages == -1: # set to all pages if -1
			pages = math.ceil(result["count"] / type_input["per_page"])

		if pages > 1:
			self.log.progress(float(type_input["page"])/float(pages))
			self.log.debug(f'received page {type_input["page"]}/{pages} for {queryType} query')

		if type_input.get("page") < pages:
			type_input["page"] = type_input["page"] + 1 
			next_page = self._paginate_query(query, type_input, pages, callback)
			items.extend(next_page)

		return items

	def upload_image(self, image_in):
		from pathlib import Path

		if re.search(r';base64',image_in):
			b64image = image_in
		if re.match(r'^http', image_in):
			b64image = url_to_base64(image_in)
		if Path(image_in).exists():
			b64image = file_to_base64(image_in)

		if not b64image:
			raise Exception("StashBoxInterface.create_image() requires a base64 string, url, or filepath")

		import base64
		from urllib3 import encode_multipart_formdata
		
		m = re.search(r'data:(?P<mime>.+?);base64,(?P<img_data>.+)',b64image)
		mime = m.group("mime")
		b64bytes = m.group("img_data").encode("utf-8")
		if not mime:
			self.log.warning("could not determine MIME type defaulting to jpeg")
			mime = 'image/jpeg'

		body, multipart_header = encode_multipart_formdata({
			'operations':'{"operationName":"AddImage","variables":{"imageData":{"file":null}},"query":"mutation AddImage($imageData: ImageCreateInput!) {imageCreate(input: $imageData) {id url}}"}',
			'map':'{"1":["variables.imageData.file"]}',
			'1': ('1.jpg', base64.decodebytes(b64bytes), mime)
		})

		request_headers = self.headers.copy()
		request_headers.update({"Content-Type":multipart_header})
		
		response = requests.post(self.url, data=body, headers=request_headers, cookies=self.cookies)
		return self._handleGQLResponse(response)["imageCreate"]

	def pending_edits_count(self, stash_id, target_type):
		"""returns how many pending edits a target has"""

		query = """query PendingEditsCount($type: TargetTypeEnum!, $id: ID!) {
			queryEdits(input: {target_type: $type, target_id: $id, status: PENDING, per_page: 1}) {
				count
			}
		}
		"""
		variables = {
			"type": target_type.name,
			"id": stash_id
		}
		return self._callGraphQL(query, variables)["queryEdits"]["count"]

	# SCENES
	def find_scene(self, scene_id, fragment=None):
		query = """query FindScene($id: ID!) {
			findScene(id: $id) {
				...Scene
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.Scene', fragment, query)

		result = self._callGraphQL(query, {"id":scene_id})
		return result["findScene"]
	def find_scenes(self, scene_query={}, fragment=None, pages=-1, callback=None):
		query = """query FindScenes($input: SceneQueryInput!) {
			queryScenes(input: $input) {
				count
				scenes {
					...Scene
				}
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.Scene', fragment, query)
		
		scene_query["page"] = scene_query.get("page", 1)
		scene_query["per_page"] = 40
		return self._paginate_query(query, scene_query, pages, callback)
	def edit_scene(self, stash_id:str, edit:dict, manual_comment:str):
		if self.pending_edits_count(stash_id, StashboxTarget.SCENE) > 0:
			self.log.warning(f'Edit not submitted Scene:{stash_id} has pending edits')
			return

		comments = []
		details = self.fetch_scene_edit_details(stash_id)
		
		if edit.get("tags"):
			passed_tag_ids = edit["tags"]["ids"]
			mode = edit["tags"]["mode"]
			if mode == "SET":
				details["tag_ids"] = passed_tag_ids
				comments.append("SET Tags")
			if mode == "ADD":
				details["tag_ids"].extend(passed_tag_ids)
				comments.append(f"ADD {len(passed_tag_ids)} Tag(s)")
			if mode == "REMOVE":
				details["tag_ids"] = [tid for tid in details["tag_ids"] if tid not in passed_tag_ids]
				comments.append(f"REMOVE {len(passed_tag_ids)} Tag(s)")

		if edit.get("performers"):
			passed_performer_appearances = edit["performers"]["appearances"]
			mode = edit["performers"]["mode"]
			if mode == "SET":
				details["performers"] = passed_performer_appearances
				comments.append("SET Performers")
			if mode == "ADD":
				details["performers"].extend(passed_performer_appearances)
				comments.append(f"ADD {len(passed_performer_appearances)} Performer(s)")
			if mode == "REMOVE":
				remove_lookup = [p["performer_id"] for p in passed_performer_appearances]
				details["performers"] = [p for p in details["performers"] if p["performer_id"] not in remove_lookup ]
				comments.append(f"REMOVE {len(passed_performer_appearances)} Performer(s)")
		
		if edit.get("urls"):
			passed_url_edits = edit["urls"]["links"]
			mode = edit["urls"]["mode"]
			if mode == "SET":
				details["urls"] = passed_url_edits
				comments.append("SET Url(s)")
			if mode == "ADD":
				details["urls"].extend(passed_url_edits)
				comments.append(f"ADD {len(passed_url_edits)} Url(s)")
			if mode == "REMOVE":
				remove_lookup = [url["url"] for url in passed_url_edits]
				details["urls"] = [url for url in details["urls"] if url["url"] not in remove_lookup ]
				comments.append(f"REMOVE {len(passed_url_edits)} Url(s)")
			if mode == "REPLACE":
				for url_edit in passed_url_edits:
					for url in details["urls"]:
						if url["url"] == url_edit["target_url"]:
							url["url"] = url_edit["url"]
							comments.append(f'REPLACE {url_edit["target_url"]} with {url_edit["url"]}')

		if edit.get("image"):
			cdn_image = self.upload_image(edit["image"])
			details["image_ids"] = [cdn_image["id"]]

		for attr in ["code","date","details","director","duration","studio_id","title"]:
			if edit.get(attr):
				details[attr] = edit[attr]
				comments.append(f"update/correct `{attr}`")

		comments = [f"* {c}" for c in comments]
		comments.insert(0, manual_comment)
		comment = "\n".join(comments)

		query = """mutation SceneEdit($sceneData: SceneEditInput!) { sceneEdit(input: $sceneData) { id } }"""
		input = {
			"sceneData":{
				"edit": {"bot":True, "id":stash_id, "operation":"MODIFY", "comment":comment},
				"details": details
			}
		}

		result = self._callGraphQL(query, input)
		return result["sceneEdit"]
	def fetch_scene_edit_details(self, stash_id):
		slim_scene_edit_details = """
			title
			date
			duration
			director
			code
			details
			studio { id }
			performers {
				performer { id }
				as
			}
			images { id }
			tags { id }
			urls {
				url
				site { id }
			}
		"""
		existing = self.find_scene(stash_id, fragment=slim_scene_edit_details)
		
		# cast existing meta to SceneEditDetailsInput
		existing["studio_id"] = existing["studio"]["id"]
		del existing["studio"]

		existing["image_ids"] = [ i["id"] for i in existing["images"] ]
		del existing["images"]

		existing["tag_ids"] = [ t["id"] for t in existing["tags"] ]
		del existing["tags"]
		
		for p in existing["performers"]:
			p["performer_id"] = p["performer"]["id"]
			del p["performer"]
			
		for url in existing["urls"]:
			url["site_id"] = url["site"]["id"]
			del url["site"]
		
		return existing

	# PERFORMERS
	def find_performer(self, performer_in, fragment=None):
		performer = self.__find_by_id(
			"query FindPerformer($id: ID!) { findPerformer(id: $id) { ...Performer }}",
			performer_in,
			[r'\.\.\.Performer', fragment]
		)
		if performer != None:
			return performer
		
		def find_query(search):
			return self.find_performers({"names": f'"{search}"'}, fragment="id name aliases")
		match = self.__match_search_item(performer_in, find_query)
		if match:
			return self.find_performer(match)
	def find_performers(self, performer_query={}, fragment=None, pages=-1, callback=None):
		query = """query FindPerformers($input: PerformerQueryInput!) {
			queryPerformers(input: $input) {
				count
				performers {
					...Performer
				}
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.Performer', fragment, query)
		
		performer_query["page"] = performer_query.get("page", 1)
		performer_query["per_page"] = 40
		return self._paginate_query(query, performer_query, pages, callback)

	# TAGS
	def find_tag(self, tag_in, fragment=None):
		tag = self.__find_by_id(
			"query FindTag($id: ID!) { findTag(id: $id) { ...Tag }}",
			tag_in,
			[r'\.\.\.Tag', fragment]
		)
		if tag != None:
			return tag
		
		def find_query(search):
			return self.find_tags({"names": search}, fragment="id name aliases")
		match = self.__match_search_item(tag_in, find_query)
		if match:
			return self.find_tag(match)
	def find_tags(self, tag_query={}, fragment=None, pages=-1, callback=None):
		query = """query Tags($input: TagQueryInput!){
			queryTags(input: $input){
				count
				tags{
					...Tag
				}
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.Tag', fragment, query)
		
		tag_query["page"] = tag_query.get("page", 1)
		tag_query["per_page"] = 40
		return self._paginate_query(query, tag_query, pages, callback)

	# DRAFTS
	def find_drafts(self):
		query = """query FindDrafts{
			findDrafts{
				...Draft
			}
		}"""
		return self._callGraphQL(query)["findDrafts"]
	def get_draft_data(self, draft_id):
		query = """query FindDraftData($draft_id: ID!){
			findDraft(id: $draft_id){
				data {
				  ... on PerformerDraft { ...PerformerDraft }
				  ... on SceneDraft { ...SceneDraft }
				}
			}
		}"""
		return self._callGraphQL(query, {"draft_id": draft_id})["findDraft"]

	# STUDIOS
	def find_studio(self, studio_in, fragment=None):
		studio = self.__find_by_id(
			"query FindStudio($id: ID!) { findStudio(id: $id) { ...Studio }}",
			studio_in,
			[r'\.\.\.Studio', fragment]
		)
		if studio != None:
			return studio
		
		def find_query(search):
			return self.find_studios({"name": f'"{search}"'}, fragment="id name")
		match = self.__match_search_item(studio_in, find_query)
		if match:
			return self.find_studio(match)
	def find_studios(self, studio_query={}, fragment=None, pages=-1, callback=None):
		query = """query FindStudios($input: StudioQueryInput!) {
			queryStudios(input: $input) {
				count
				studios {
					...Studio
				}
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.Studio', fragment, query)
		
		studio_query["page"] = studio_query.get("page", 1)
		studio_query["per_page"] = 40
		return self._paginate_query(query, studio_query, pages, callback)

	# SITES
	def find_site(self, site_name):
		query = """query FindSiteId{ querySites{ count sites{ id name url } } }"""
		result = self._callGraphQL(query)
		matches = []
		for site in result["querySites"]["sites"]:
			if str_compare(site["name"], site_name):
				matches.append(site)
		if len(matches) > 1:
			self.log.warning(f"matched site search '{site_name}' to multiple ({len(matches)}) sites")
		if len(matches) == 1:
			return matches[0]
