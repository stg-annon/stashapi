import re, sys, json, sqlite3
import requests
from pathlib import Path

from .tools import defaultify
from . import log

class GQLWrapper:
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

	def __init__(self):
		return

	def parse_fragments(self, fragments_in):
		fragments = {}
		fragment_matches = re.finditer(r'fragment ([A-Za-z]+) on [A-Za-z]+ {', fragments_in)
		for fagment_match in fragment_matches:
			start = fagment_match.end()
			end = start

			depth = 0
			for i in range(end, len(fragments_in)):
				c = fragments_in[i]
				if c == "{":
					depth += 1
				if c == "}":
					if depth > 0:
						depth -= 1
					else:
						end = i
						break
			fragments[fagment_match.group(1)] = fragments_in[fagment_match.start():end+1]
		self.fragments.update(fragments)
		return fragments

	def __resolveFragments(self, query):
		fragmentReferences = list(set(re.findall(r'(?<=\.\.\.)\w+', query)))
		fragments = []
		for ref in fragmentReferences:
			fragments.append({
				"fragment": ref,
				"defined": bool(re.search("fragment {}".format(ref), query))
			})

		if all([f["defined"] for f in fragments]):
			return query
		else:
			for fragment in [f["fragment"] for f in fragments if not f["defined"]]:
				if fragment not in self.fragments:
					raise Exception(f'GraphQL error: fragment "{fragment}" not defined')
				query += self.fragments[fragment]
			return self.__resolveFragments(query)

	def _callGraphQL(self, query, variables=None):

		query = self.__resolveFragments(query)

		json_request = {'query': query}
		if variables is not None:
			json_request['variables'] = variables

		response = requests.post(self.url, json=json_request, headers=self.headers, cookies=self.cookies)
		
		if response.status_code == 200:
			result = response.json()

			if result.get("errors"):
				for error in result["errors"]:
					log.error(f"GraphQL error: {error}")
			if result.get("error"):
				for error in result["error"]["errors"]:
					log.error(f"GraphQL error: {error}")
			if result.get("data"):
				result_data = defaultify(result)
				return result_data['data']
		elif response.status_code == 401:
			sys.exit("HTTP Error 401, Unauthorized. Cookie authentication most likely failed")
		else:
			raise ConnectionError(
				"GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
					response.status_code, response.content, query, variables)
			)

class SQLiteWrapper:
	conn = None

	def __init__(self, db_filepath) -> None:
		# generate uri for read-only connection, all write operations should be done from the API
		db_uri = f"{Path(db_filepath).as_uri()}?mode=ro"
		self.conn = sqlite3.connect(db_uri, uri=True)

	def query(self, query, args=(), one=False):
		cur = self.conn.cursor()
		cur.execute(query, args)
		r = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
		return (r[0] if r else None) if one else r