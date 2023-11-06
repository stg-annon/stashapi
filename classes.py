import re, math
import requests

from .stash_types import StashEnum

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
	version = None
	verify_ssl = True

	def __init__(self):
		return

	def parse_fragments(self, fragments_in):
		fragments = {}
		fragment_matches = re.finditer(r'fragment\s+([A-Za-z]+)\s+on\s+[A-Za-z]+(\s+)?{', fragments_in)
		for fragment_match in fragment_matches:
			start = fragment_match.end()
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
			fragments[fragment_match.group(1)] = fragments_in[fragment_match.start():end+1]
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
					raise Exception(f'StashAPI error: fragment "{fragment}" not defined')
				query += f"\n{self.fragments[fragment]}"
			return self.__resolveFragments(query)

	def _getFragmentsIntrospection(self, global_overrides, fragment_overrides={}):
		"""Automatically generates fragments for GQL endpoint via introspection

		Args:
			global_overrides (dict, optional): mapping of objects and their fragments, any occurrence of these objects will use the defined fragment instead of a generated one
			fragment_overrides (dict, optional): mapping of objects and specific attributes to override attributes to override. Defaults to {}.

		Returns:
			dict: mapping of fragment names and values

		Examples:
		.. code-block:: python
			global_overrides = { "Scene": "{ id }" }
			fragment_overrides = { "ScrapedStudio": {"parent": "{ stored_id }"} }

		"""		


		fragments = {}

		query = """{ __schema { types { ...FullType } } }

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
	 name
	 description
	 args {
		...InputValue
	 }
	 type {
		...TypeRef
	 }
	 isDeprecated
	 deprecationReason
  }
  inputFields {
	 ...InputValue
  }
  interfaces {
	 ...TypeRef
  }
  enumValues(includeDeprecated: true) {
	 name
	 description
	 isDeprecated
	 deprecationReason
  }
  possibleTypes {
	 ...TypeRef
  }
}
fragment InputValue on __InputValue {
  name
  description
  type {
	 ...TypeRef
  }
  defaultValue
}
fragment TypeRef on __Type {
  kind
  name
  ofType {
	 kind
	 name
	 ofType {
		kind
		name
		ofType {
		  kind
		  name
		  ofType {
			 kind
			 name
			 ofType {
				kind
				name
				ofType {
				  kind
				  name
				  ofType {
					 kind
					 name
				  }
				}
			 }
		  }
		}
	 }
  }
}"""

		stash_schema = self._callGraphQL(query)
		stash_types = stash_schema.get('__schema',{}).get('types',[])

		def has_object_name(type):
			if type.get("kind") in ["OBJECT", "UNION"]:
				return type["name"]
			if type.get("type"):
				return has_object_name(type["type"])
			if type.get("ofType"):
				return has_object_name(type["ofType"])

		for type in stash_types:
			if type["kind"] != "OBJECT":
				continue
			if not type['fields']:
				continue

			type_name = type["name"]
			fragment_override = fragment_overrides.get(type_name, {})

			fragment = "fragment "+type_name+" on "+type_name+" {"
			for field in type['fields']:
				if field.get("isDeprecated"):
					continue
				attr = field["name"]
				field_type_name = has_object_name(field)
				if field_type_name:
					if field_type_name in global_overrides:
						attr += " "+global_overrides[field_type_name]
					elif field["name"] in fragment_override:
						if fragment_override[field["name"]] == None:
							continue
						attr += " "+fragment_override[field["name"]]
					else:
						attr += " { ..."+field_type_name+" }"
				fragment += f"\n\t{attr}"
			fragment += "\n}"
			fragments[type_name] = fragment

		#Handle UNION Fragments as well
		for type in stash_types:
			if type["kind"] != "UNION":
				continue
			if not type["possibleTypes"]:
				continue
			type_name = type["name"]
			fragment = f"fragment {type_name} on {type_name} "+"{"
			for field in type['possibleTypes']:
				if field.get("isDeprecated"):
					continue
				attr = "... on " + field["name"]
				field_type_name = has_object_name(field)
				if field_type_name:
					if field_type_name in global_overrides:
						attr += " "+global_overrides[field_type_name]
					elif field["name"] in fragment_override:
						if fragment_override[field["name"]] == None:
							continue
						attr += " "+fragment_override[field["name"]]
					else:
						attr += " {"
						#Search for the object used in the UNION. Basically the loop above, but limited to one Object
						objectType = [x for x in stash_types if x["kind"] == "OBJECT" and x["fields"] and x["name"] == field_type_name][0]
						for objectField in objectType["fields"]:
							if field.get("isDeprecated"):
								continue
							attr += "\n\t" + objectField["name"]
							objectField_type_name = has_object_name(objectField)
							if objectField_type_name:
								if objectField_type_name in global_overrides:
									attr += " "+global_overrides[objectField_type_name]
								elif objectField["name"] in fragment_override:
									if fragment_override[objectField["name"]] == None:
										continue
									attr += " "+fragment_override[objectField["name"]]
								else:
									attr += " { ..."+objectField_type_name+" }"
						attr += "}"
				fragment += f"\n\t{attr}"
			fragment += "\n}"
			fragments[type_name] = fragment

		return fragments

	def _callGraphQL(self, query, variables={}):

		query = self.__resolveFragments(query)

		json_request = {'query': query}
		if variables:
			serialize_dict(variables)
			json_request['variables'] = variables

		# recursive call no longer needed as -1 has been fixed in stash
		# per_page = variables.get("filter",{}).get("per_page",None)		
		# if per_page == -1:
		# 	return self._callGraphQLRecursive(query, variables)

		response = requests.post(self.url, json=json_request, headers=self.headers, cookies=self.cookies, verify=self.verify_ssl)
		
		try:
			return self._handleGQLResponse(response)
		except:
			self.log.debug(f"{rm_query_whitespace(query)}\nVariables: {variables}")
			raise

	def _handleGQLResponse(self, response):
		try:
			content = response.json()
		except ValueError:
			content = {}

		for error in content.get("errors", []):
			message = error.get("message")
			if len(message) > 2500:
				message = f"{message[:2500]}..."
			code = error.get("extensions", {}).get("code", "GRAPHQL_ERROR")
			if message == "must not be null":
				code = "DATABASE_ERROR"
				self.log.error("Database potentially malformed check your DB file")
			path = error.get("path", "")
			fmt_error = f"{code}: {message} {path}".strip()
			self.log.error(fmt_error)

		if response.status_code == 401:
			if "session" in self.cookies:
				self.log.error(f"{response.status_code} {response.reason}. Could not access endpoint {self.url} Are you running a proxy? check your proxy settings.")
			else:
				self.log.error(f"{response.status_code} {response.reason}. Could not access endpoint {self.url}. Did you provide an API key? ")
		elif content.get("data") == None:
			self.log.error(f"{response.status_code} {response.reason} GQL data response is null")
		elif response.status_code == 200:
			return content["data"]
		error_msg = f"{response.status_code} {response.reason} query failed. {self.version}"
		self.log.error(error_msg)
		raise Exception(error_msg)

	def _callGraphQLRecursive(self, query, variables, pages=-1):

		PER_PAGE = 1000 # set to max allowable

		page = variables.get("filter",{}).get("page",1)

		variables["filter"]["page"] = page
		variables["filter"]["per_page"] = PER_PAGE

		r = self._callGraphQL(query, variables)

		queryType = list(r.keys())[0]
		itemType = list(r[queryType].keys())[1]

		if pages == -1:
			pages = math.ceil(r[queryType]["count"] / PER_PAGE)

		self.log.debug(f'received page {page}/{pages} for {queryType} query, {r[queryType]["count"]} {itemType} results')

		if page < pages:
			variables["filter"]["page"] = page + 1 
			next_page = self._callGraphQLRecursive(query, variables, pages)
			r[queryType][itemType].extend(next_page[queryType][itemType])

		return r

	def callGQL(self, query, variables={}):
		return self._callGraphQL(query, variables)
	def call_gql(self, query, variables={}):
		return self._callGraphQL(query, variables)

class StashVersion:

	def __init__(self, version_in) -> None:
		if isinstance(version_in, str):
			self.parse(version_in)
		if isinstance(version_in, dict):
			self.parse(f"{version_in['version']}-{version_in['hash']}")

	def parse(self, ver_str) -> None:
		m = re.search(r'v(?P<MAJOR>\d+)\.(?P<MINOR>\d+)\.(?P<PATCH>\d+)(?:-(?P<BUILD>\d+))?(?:-(?P<HASH>[a-z0-9]{9}))?', ver_str)
		if m:
			m = m.groupdict()
		else:
			m = {}

		self.major = int(m.get("MAJOR", 0))
		self.minor = int(m.get("MINOR", 0))
		self.patch = int(m.get("PATCH", 0))
		self.build = 0
		if m.get("BUILD"):
			self.build = int(m["BUILD"])
		self.hash = ""
		if m.get("HASH"):
			self.hash = m["HASH"]

	def pad_version(self) -> str:
		return f"{self.major:04d}.{self.minor:04d}.{self.patch:04d}-{self.build:04d}"

	def __str__(self) -> str:
		ver_str = f"v{self.major}.{self.minor}.{self.patch}-{self.build}"
		if self.hash:
			ver_str = f"{ver_str}-{self.hash}"
		return ver_str
	
	def __repr__(self) -> str:
		return str(self)

	def __eq__(self, other: object) -> bool:
		return self.hash and other.hash and self.hash == other.hash
	def __gt__(self, other: object) -> bool:
		return self.pad_version() > other.pad_version()

def rm_query_whitespace(query):
	whitespace = re.search(r'([\t ]+)(query|mutation)', query)
	if whitespace:
		whitespace = whitespace.group(1)
		query_lines = []
		for line in query.split("\n"):
			query_lines.append(re.sub(whitespace, '', line, 1))
		query = "\n".join(query_lines)
	return query

def serialize_dict(input_dict):
	for key, value in input_dict.items():
		input_dict[key] = type_transformer(value)
		if isinstance(value, dict):
			serialize_dict(value)
		elif isinstance(value, list):
			for item in value:
				if isinstance(item, dict):
					serialize_dict(item)

def type_transformer(value):
	if isinstance(value, StashEnum):
		return value.serialize()
	return value
