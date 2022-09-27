import re, sys, sqlite3
import requests

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
		fragment_matches = re.finditer(r'fragment\s+([A-Za-z]+)\s+on\s+[A-Za-z]+(\s+)?{', fragments_in)
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
				query += f"\n{self.fragments[fragment]}"
			return self.__resolveFragments(query)

	def _callGraphQL(self, query, variables=None):

		query = self.__resolveFragments(query)

		json_request = {'query': query}
		if variables is not None:
			json_request['variables'] = variables

		response = requests.post(self.url, json=json_request, headers=self.headers, cookies=self.cookies)
		content = response.json()

		for error in content.get("errors", []):
			message = error.get("message")
			if len(message) > 2500:
				message = f"{message[:2500]}..."
			code = error.get("extensions", {}).get("code", "GRAPHQL_ERROR")
			path = error.get("path", "")
			fmt_error = f"{code}: {message} {path}".strip()
			self.log.error(fmt_error)

		if response.status_code == 200:
			return content["data"]
		elif response.status_code == 401:
			self.log.error(f"401, Unauthorized. Could not access endpoiont {self.url}. Did you provide an API key?")
		else:
			self.log.error(f"{response.status_code} query failed. {query}. Variables: {variables}")
		sys.exit()

class SQLiteWrapper:
	conn = None

	def __init__(self, db_filepath) -> None:
		## TODO generate uri for read-only connection, all write operations should be done from the API
		## issuses with cross os paths parsing to uri skip for now, opt for warning message
		# db_filepath = Path(db_filepath)
		# db_filepath = db_filepath.resolve()
		# db_uri = f"{db_filepath.as_uri()}?mode=ro"

		self.log.warning("SQL connetion should only be used for read-only operations, all write operations should be done from the API")
		self.conn = sqlite3.connect(db_filepath)

	def query(self, query, args=(), one=False):
		cur = self.conn.cursor()
		cur.execute(query, args)
		r = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
		return (r[0] if r else None) if one else r