import re, math, requests
from enum import Enum

from requests.structures import CaseInsensitiveDict

from .classes import GQLWrapper
from . import stashbox_gql_fragments
from . import log as StashLogger

from .tools import file_to_base64, url_to_base64

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

	def __init__(self, conn={}, fragments:list[str]=[stashbox_gql_fragments.DEVELOP]):

		conn = CaseInsensitiveDict(conn)
		
		self.log = conn.get("Logger", StashLogger)
		
		self.url = conn.get('endpoint', "https://stashdb.org/graphql")
		self.endpoint = self.url

		if not self.url:
			raise Exception("REQUIRED key 'endpoint' not provided in connection dict")

		stash = conn.get("stash")
		if stash:
			c = stash.get_stashbox_connection(self.url)	
			api_key = c.get("api_key")
			if not api_key:
				raise Exception(f"Could not find api_key for '{self.url}' with prorivded stash connection")
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

		self.fragments = {}
		for fragment in fragments:
			self.parse_fragments(fragment)

	def create_image(self, b64image=None, path=None, url=None):
		if path:
			b64image = file_to_base64(path)
		elif url:
			b64image = url_to_base64(url)
		if not b64image:
			raise Exception("StashBoxInterface.create_image() requires one kwarg to be defined")

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

	def get_scene_last_updated(self, scene_id):
		query = """query sceneLastUpdated($id: ID!) {
			findScene(id: $id) {
				id
				updated
				deleted
			}
		}"""

		result = self._callGraphQL(query, {"id": scene_id})
		return result["findScene"]

	def pending_edits_count(self, stash_id, target_type):
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

	def get_tag(self, tag_id, fragment=None):
		query = """query FindTag($id: ID!) {
			findTag(id: $id) {
				...TagFragment
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.TagFragment', fragment, query)

		result = self._callGraphQL(query, {"id":tag_id})
		return result["findTag"]

	def find_tags(self, tag_query, fragment=None, pages=-1, callback=None):
		query = """query Tags($input: TagQueryInput!){
			queryTags(input: $input){
				count
				tags{
					...TagFragment
				}
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.TagFragment', fragment, query)
		
		tag_query["page"] = tag_query.get("page", 1)
		tag_query["per_page"] = 40
		return self._paginate_query(query, tag_query, pages, callback)

	def find_scene(self, scene_id, fragment=None):
		query = """query FindScene($id: ID!) {
			findScene(id: $id) {
				...SceneFragment
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.SceneFragment', fragment, query)

		result = self._callGraphQL(query, {"id":scene_id})
		return result["findScene"]

	def find_scenes_count(self, scene_query):
		query = """query FindScenes($input: SceneQueryInput!) {
			queryScenes(input: $input) {
				count
				scenes { id }
			}
		}"""
		return self._callGraphQL(query, {"input":scene_query})["queryScenes"]["count"]

	def find_scenes(self, scene_query, fragment=None, pages=-1, callback=None):
		query = """query FindScenes($input: SceneQueryInput!) {
			queryScenes(input: $input) {
				count
				scenes {
					...SceneFragment
				}
			}
		}"""
		if fragment:
			query = re.sub(r'\.\.\.SceneFragment', fragment, query)
		
		scene_query["page"] = scene_query.get("page", 1)
		scene_query["per_page"] = 40
		return self._paginate_query(query, scene_query, pages, callback)

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

	# returns items up to specified page, -1 for all pages (default: -1)
	def _paginate_query(self, query, type_input, pages=-1, callback=None):
		result = self._callGraphQL(query, {"input": type_input})

		queryType = list(result.keys())[0]
		result = result[queryType]

		itemType = list(result.keys())[1]
		items = result[itemType]
		if callback != None:
			callback(items)

		if pages == -1: # set to all pages if -1
			pages = math.ceil(result["count"] / type_input["per_page"])


		self.log.progress(float(type_input["page"])/float(pages))
		self.log.debug(f'received page {type_input["page"]}/{pages} for {queryType} query')

		if type_input.get("page") < pages:
			type_input["page"] = type_input["page"] + 1 
			next_page = self._paginate_query(query, type_input, pages, callback)
			items.extend(next_page)

		return items

	def find_site_id(self, site_name):
		query = """query FindSiteId{ querySites{ count sites{ id name url } } }"""
		result = self._callGraphQL(query)
		for site in result["querySites"]["sites"]:
			if site["name"].upper() == site_name.upper():
				return site["id"]

	def fetch_scene_edit_details(self, stash_id):
		existing = self.find_scene(stash_id, fragment="...SceneEditFragment")
		
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

	def callGQL(self, q, v):
		return self._callGraphQL(q, v)