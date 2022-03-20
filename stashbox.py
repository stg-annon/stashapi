import sys

from requests.structures import CaseInsensitiveDict

from .classes import GQLWrapper
from . import gql_fragments

# add default fallback key here
STASHDB_DEFAULT_KEY=""

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
		
		log = conn.get("logger", None)
		if not log:
			raise Exception("No Logger Provided")

		self.endpoint = conn.get('endpoint', "https://stashdb.org/graphql")
		self.headers['ApiKey'] = conn.get('api_key', STASHDB_DEFAULT_KEY)
		try:
			# test query to check connection
			r = self._callGraphQL("query Me{me {name email}}")
			log.info(f'Connected to "{self.endpoint}" as {r["me"]["name"]} ({r["me"]["email"]})')
		except Exception:
			log.error(f"Could not connect to Stash-Box at {self.endpoint}")
			sys.exit()

		self.fragments = fragments
		self.fragments.update(gql_fragments)

	def get_scene_last_updated(self, scene_id):
		query = """query sceneLastUpdated($id: ID!) {
			findScene(id: $id) {
				updated
			}
		}"""

		result = self._callGraphQL(query, {"id": scene_id})
		return result["findScene"]["updated"]


