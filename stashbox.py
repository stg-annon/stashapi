import sys

from requests.structures import CaseInsensitiveDict

from .classes import GQLWrapper
from . import gql_fragments
from . import log

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

	def __init__(self, conn={}, fragments={}):
		global log

		conn = CaseInsensitiveDict(conn)

		log = conn.get("logger", log)
		if not log:
			raise Exception("No Logger Provided")

		self.url = conn.get('endpoint', "https://stashdb.org/graphql")

		api_key = conn.get('api_key', None)
		if not api_key:
			raise Exception("no api_key provided")
		self.headers['ApiKey'] = api_key
		try:
			# test query to check connection
			r = self._callGraphQL("query Me{me {name email}}")
			log.info(f'Connected to "{self.url}" as {r["me"]["name"]} ({r["me"]["email"]})')
		except Exception as e:
			log.error(f"Could not connect to Stash-Box at {self.url}")
			log.error(e)
			sys.exit()

		self.fragments = fragments
		self.fragments.update(gql_fragments.STASHBOX)

	def get_scene_last_updated(self, scene_id):
		query = """query sceneLastUpdated($id: ID!) {
			findScene(id: $id) {
				updated
			}
		}"""

		result = self._callGraphQL(query, {"id": scene_id})
		return result["findScene"]["updated"]


