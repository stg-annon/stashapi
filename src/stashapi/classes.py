from enum import IntEnum, StrEnum
import logging
from pathlib import Path
import re
from typing import Any, Callable, Literal, NotRequired, TypeAlias, TypedDict, cast

import requests
from requests.sessions import Session
from typing_extensions import deprecated, override

from .stash_types import CallbackReturns


JSON: TypeAlias = "JSONDict" | "JSONList" | str | int | float | bool | None
JSONDict: TypeAlias = dict[str, "JSON"]
JSONList: TypeAlias = list["JSON"]


class GQLTypeKind(StrEnum):
    # Indicates this type is a scalar.
    SCALAR = "SCALAR"

    # Indicates this type is an object. fields and interfaces are valid fields.
    OBJECT = "OBJECT"

    # Indicates this type is an interface. fields, interfaces, and possibleTypes are valid fields.
    INTERFACE = "INTERFACE"

    # Indicates this type is a union. possibleTypes is a valid field.
    UNION = "UNION"

    # Indicates this type is an enum. enumValues is a valid field.
    ENUM = "ENUM"

    # Indicates this type is an input object. inputFields is a valid field.
    INPUT_OBJECT = "INPUT_OBJECT"

    # Indicates this type is a list. ofType is a valid field.
    LIST = "LIST"

    # Indicates this type is a non-null. ofType
    NON_NULL = "NON_NULL"


class GQLTypeRef(TypedDict):
    kind: GQLTypeKind
    name: str
    ofType: NotRequired["GQLTypeRef"]


class GQLInputValue(TypedDict):
    name: NotRequired[str]
    description: NotRequired[str]
    type: GQLTypeRef
    defaultValue: NotRequired[str]


class GQLField(TypedDict):
    name: str
    description: NotRequired[str]
    args: list[GQLInputValue]
    type: GQLTypeRef
    isDeprecated: bool
    deprecationReason: NotRequired[str]


class GQLEnumValue(TypedDict):
    name: NotRequired[str]
    description: NotRequired[str]
    isDeprecated: bool
    deprecationReason: NotRequired[str]


class GQLFullType(TypedDict):
    kind: GQLTypeKind
    name: NotRequired[str]
    description: NotRequired[str]
    fields: list[GQLField]
    inputFields: list[GQLInputValue]
    interfaces: list[GQLTypeRef]
    enumValues: list[GQLEnumValue]
    possibleTypes: list[GQLTypeRef]


class GQLIntrospectionTypes(TypedDict):
    types: list[GQLFullType]


GQLIntrospectionResult = TypedDict("GQLIntrospectionResult", {"__schema": GQLIntrospectionTypes})


class GQLSqlQueryResponse(TypedDict):
    columns: list[str]
    rows: list[Any]


class GQLSqlExecResponse(TypedDict):
    rows_affected: NotRequired[int]
    last_insert_id: NotRequired[int]


class GQLJobStatus(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    STOPPING = "STOPPING"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


GQLJobStatusLiteral: TypeAlias = Literal[
    "READY",
    "RUNNING",
    "FINISHED",
    "STOPPING",
    "CANCELLED",
    "FAILED",
]

JobStatusType: TypeAlias = GQLJobStatusLiteral | GQLJobStatus


class GQLJob(TypedDict):
    id: int
    status: GQLJobStatus
    subTasks: list[str]
    description: str
    progress: NotRequired[float]
    startTime: NotRequired[str]
    endTime: NotRequired[str]
    addTime: str
    error: NotRequired[str]


class GQLWrapper:

    def __init__(self, log: logging.Logger):
        self.log: logging.Logger = log
        self.fragments: dict[str, str] = {}
        self.port: str | int = ""
        self.url: str = ""
        self.version: StashVersion | None = None

        self.s: Session = requests.session()
        self.s.headers.update(
            {
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "keep-alive",
                "DNT": "1",
            }
        )
        self.s.verify = True

    def parse_fragments(self, fragments_in: str) -> dict[str, str]:
        fragments: dict[str, str] = {}
        fragment_matches = re.finditer(r"fragment\s+([A-Za-z]+)\s+on\s+[A-Za-z]+(\s+)?{", fragments_in)
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
            fragments[fragment_match.group(1)] = fragments_in[fragment_match.start() : end + 1]
        self.fragments.update(fragments)
        return fragments

    def __resolve_fragments(self, query: str) -> str:
        fragmentReferences: list[str] = list(set(re.findall(r"(?<=\.\.\.)\w+", query)))
        fragments: list[dict[str, str | bool]] = []
        for ref in fragmentReferences:
            fragments.append({"fragment": ref, "defined": bool(re.search("fragment {}".format(ref), query))})

        if all([f["defined"] for f in fragments]):
            return query
        else:
            for fragment in [f["fragment"] for f in fragments if not f["defined"]]:
                if fragment not in self.fragments:
                    raise Exception(f'StashAPI error: fragment "{fragment}" not defined')
                query += f"\n{self.fragments[fragment]}"
            return self.__resolve_fragments(query)

    def _get_fragments_introspection(
        self,
        fragment_overrides: dict[str, str],
        attribute_overrides: dict[str, dict[str, str | None]] | None,
    ):
        """Automatically generates fragments for GQL endpoint via introspection

        Args:
            fragment_overrides (dict): mapping of objects and their fragments, any occurrence of these objects will use the defined fragment instead of a generated one
            attribute_overrides (dict, optional): mapping of objects and specific attributes to override attributes to override. Defaults to {}.

        Returns:
            dict: mapping of fragment names and values

        Examples:
        .. code-block:: python
            fragment_overrides = { "Scene": "{ id }" }
            attribute_overrides = { "ScrapedStudio": {"parent": "{ stored_id }"} }
        """

        fragment_overrides = fragment_overrides or {}
        attribute_overrides = attribute_overrides or {}
        fragments: dict[str, str] = {}

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

        # this double cast is kinda gross, idk why `dict[str, JSON]` can't
        # be directly assigned to `GQLIntrospectionResult`
        response = cast(GQLIntrospectionResult, cast(object, self._GQL(query)))

        stash_schema = response.get("__schema", {})
        assert stash_schema, "Received empty schema from GraphQL introspection query"

        stash_types = stash_schema.get("types", [])
        assert stash_types, "Received no types from GraphQL introspection query"

        def get_object_name(typ: GQLField | GQLTypeRef) -> str | None:
            if typ.get("kind") in [GQLTypeKind.OBJECT, GQLTypeKind.UNION]:
                ret = typ["name"]
                return ret

            # Field will always have `type` but TypeRef will not
            if newtype := typ.get("type"):
                return get_object_name(newtype)

            # TypeRef may have `ofType`, Field will not
            if newtype := typ.get("ofType"):
                return get_object_name(newtype)

        def handle_type_object(typ: GQLFullType) -> tuple[None, None] | tuple[str, str]:
            if not typ["fields"]:
                return None, None
            fields = typ["fields"]

            assert "name" in typ, "'name' field missing from type"
            type_name = typ["name"]
            attribute_override = attribute_overrides.get(type_name, {})

            fragment = "{"

            for field in fields:
                if field["isDeprecated"]:
                    continue

                name = field["name"]

                if (name in attribute_override) and (attribute_override[name] == None):
                    continue

                if field_type_name := get_object_name(field):
                    if field_type_name in fragment_overrides:
                        name += " " + fragment_overrides[field_type_name]
                    elif name in attribute_override and (attr_override := attribute_override[name]):
                        name += " " + attr_override
                    else:
                        name += " { ..." + field_type_name + " }"
                fragment += f"\n\t{name}"
            fragment += "\n}"
            return type_name, fragment

        def handle_type_union(typ: GQLFullType) -> tuple[None, None] | tuple[str, str]:
            if not typ["possibleTypes"]:
                return None, None
            fields = typ["possibleTypes"]

            assert "name" in typ, "'name' field missing from type"
            type_name = typ["name"]
            fragment = "{"

            for field in fields:
                # FIXME: with the TypeRef fragment used for the introspection query, `isDeprecated` will never exist here
                if field.get("isDeprecated"):
                    continue
                fragment += f'\n\t...{field["name"]}'
            fragment += "\n}"
            return type_name, fragment

        for typ in stash_types:
            kind = typ["kind"]
            type_name: str | None
            fragment: str | None

            if kind == GQLTypeKind.OBJECT:
                type_name, fragment = handle_type_object(typ)
            elif kind == GQLTypeKind.UNION:
                type_name, fragment = handle_type_union(typ)
            else:
                continue

            if type_name and fragment:
                fragments[type_name] = f"fragment {type_name} on {type_name} {fragment}"

        return fragments

    def _GQL(self, query: str, variables: dict[str, object] | None = None) -> dict[str, JSON]:

        query = self.__resolve_fragments(query)

        json_request: dict[str, object] = {"query": query}
        if variables:
            serialize_dict(variables)
            json_request["variables"] = variables

        response = self.s.post(self.url, json=json_request)

        try:
            return self._handle_GQL_response(response)
        except:
            self.log.debug(f"{rm_query_whitespace(query)}\nVariables: {variables}")
            raise

    def _handle_GQL_response(self, response: requests.Response) -> dict[str, JSON]:
        content: dict[str, JSON] = {}
        try:
            content = cast(dict[str, JSON], response.json())
        except ValueError:
            pass

        # Set database locked bit to 0 on fresh response.
        # Database locked errors send a 200 response code (normal),
        # so they are not handled correctly without special intervention.
        database_locked = 0

        errors = content.get("errors", [])
        assert isinstance(errors, list)
        for error in errors:
            assert isinstance(error, dict)

            message = error.get("message")
            assert isinstance(message, str)

            if len(message) > 2500:
                message = f"{message[:2500]}..."

            extensions = error.get("extensions", {})
            assert isinstance(extensions, dict)

            code = extensions.get("code", "GRAPHQL_ERROR")
            assert isinstance(code, str)

            if message == "must not be null":
                code = "DATABASE_ERROR"
                self.log.error("Database potentially malformed check your DB file")

            if "database is locked" in message:
                # If the database is locked, set the database_locked bit.
                code = "DATABASE_LOCKED"
                database_locked = 1

            path = error.get("path", "")
            fmt_error = f"{code}:{path} {message}".strip()
            self.log.error(fmt_error)

        if response.status_code == 401:
            self.log.error(
                f"{response.status_code} {response.reason}. Could not access endpoint {self.url}. Did you provide an API key? Are you running a proxy?"
            )
        elif content.get("data") is None:
            self.log.error(f"{response.status_code} {response.reason} GQL data response is null")
        elif database_locked == 1:
            # If the database_locked bit is set, log error and proceed to exception.
            self.log.error("Database is temporarily locked.")
        elif response.status_code == 200:
            data = content["data"]
            assert isinstance(data, dict)
            return data

        error_msg = f"{response.status_code} {response.reason} query failed. {self.version}"
        self.log.error(error_msg)
        raise Exception(error_msg)

    # shim for older plugins
    @deprecated("`callGQL()` is deprecated, use `call_GQL()` instead")
    def callGQL(self, query: str, variables: dict[str, object] | None = None):
        self.log.debug("callGQL() is deprecated use call_GQL() instead")
        return self._GQL(query, variables)

    def call_GQL(
        self,
        query: str,
        variables: dict[str, object] | None = None,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> dict[str, JSON]:
        variables = variables or {}
        if callback:
            raise NotImplementedError("Callback function not implemented")
        return self._GQL(query, variables)


class GQLStashVersion(TypedDict):
    build_time: str
    hash: str
    version: str


class StashVersion:
    major: int = 0
    minor: int = 0
    patch: int = 0
    build: int = 0
    hash: str = ""

    def __init__(self, version_in: str | GQLStashVersion):
        if isinstance(version_in, str):
            self.parse(version_in)
        else:
            assert "version" in version_in
            assert "hash" in version_in
            self.parse(f"{version_in['version']}-{version_in['hash']}")

    def parse(self, ver_str: str) -> None:
        matches = re.search(
            r"v(?P<MAJOR>\d+)\.(?P<MINOR>\d+)\.(?P<PATCH>\d+)(?:-(?P<BUILD>\d+)?(?:-(?P<HASH>[a-z0-9]{9})))?", ver_str
        )

        if matches:
            matches = matches.groupdict()
        else:
            return

        self.major = int(matches.get("MAJOR", 0))
        self.minor = int(matches.get("MINOR", 0))
        self.patch = int(matches.get("PATCH", 0))
        self.build = int(matches.get("BUILD", 0))
        self.hash = matches.get("HASH", "")

    def pad_version(self) -> str:
        return f"{self.major:04d}.{self.minor:04d}.{self.patch:04d}-{self.build:04d}"

    @override
    def __str__(self) -> str:
        ver_str = f"v{self.major}.{self.minor}.{self.patch}-{self.build}"
        if self.hash:
            ver_str = f"{ver_str}-{self.hash}"
        return ver_str

    @override
    def __repr__(self) -> str:
        return str(self)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StashVersion):
            return NotImplemented
        return ("" not in (self.hash, other.hash)) and (self.hash == other.hash)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, StashVersion):
            return NotImplemented
        return self.pad_version() > other.pad_version()


def rm_query_whitespace(query: str) -> str:
    whitespace = re.search(r"([\t ]+)(query|mutation)", query)
    if not whitespace:
        return query

    whitespace = cast(str, whitespace.group(1))

    query_lines: list[str] = []
    for line in query.split("\n"):
        query_lines.append(line.replace(whitespace, "", 1))

    return "\n".join(query_lines)


def serialize_dict(input_dict: dict[str, object]) -> None:
    """
    Deeply serializes the given dict in-place. Converts Paths into strs, StashEnums and Enums into their value (probably int or str). Leaves others untouched

    Args:
        input_dict (dict[str, object]): the dict to serialize

    Returns:
        None
    """
    for key, value in input_dict.items():
        input_dict[key] = type_transformer(value)
        if isinstance(value, dict):
            serialize_dict(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    serialize_dict(item)


def type_transformer(obj: object) -> JSON | object:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (StrEnum, IntEnum)):
        return obj.value
    return obj
