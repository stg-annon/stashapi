import inspect
import logging
import math
from pathlib import Path
import re
import time
from typing import Any, Callable, Literal, TypedDict, cast, final

from requests.structures import CaseInsensitiveDict
from typing_extensions import deprecated, override

from stashapi.classes import (
    GQLJob,
    GQLJobStatus,
    GQLSqlExecResponse,
    GQLSqlQueryResponse,
    GQLStashVersion,
    GQLWrapper,
    JSON,
    JobStatus,
    StashVersion,
)
from stashapi.gql_types import (
    GQLBulkGalleryUpdateInput,
    GQLBulkImageUpdateInput,
    GQLBulkPerformerUpdateInput,
    GQLBulkSceneUpdateInput,
    GQLCriterionModifier,
    GQLFindFilterType,
    GQLGalleryChapterCreateInput,
    GQLGalleryChapterUpdateInput,
    GQLGalleryCreateInput,
    GQLGalleryFilterType,
    GQLGalleryUpdateInput,
    GQLGroupCreateInput,
    GQLGroupFilterType,
    GQLGroupUpdateInput,
    GQLImageFilterType,
    GQLImageUpdateInput,
    GQLMoveFilesInput,
    GQLPerformerCreateInput,
    GQLPerformerFilterType,
    GQLPerformerUpdateInput,
    GQLSceneCreateInput,
    GQLSceneFilterType,
    GQLSceneHashInput,
    GQLSceneUpdateInput,
    GQLSetFingerprintsInput,
    GQLStudioCreateInput,
    GQLStudioFilterType,
    GQLTagCreateInput,
    GQLTagFilterType,
    GQLTagUpdateInput,
)
from stashapi.log import get_logger
from stashapi.stash_types import (
    CallbackReturns,
    OnMultipleMatch,
    PhashDistance,
    StashItem,
)
from stashapi.tools import str_compare

RE_ALIAS_DELIM = re.compile(r"(\/|\n|,|;)")


class SessionCookie(TypedDict):
    Value: str


class ConnectionConfig(TypedDict, total=False):
    Logger: logging.Logger
    Scheme: str
    Domain: str
    Host: str
    Port: int
    ApiKey: str
    SessionCookie: SessionCookie


@final
class StashInterface(GQLWrapper):
    def __init__(
        self,
        conn: ConnectionConfig | None = None,
        fragments: list[str] | None = None,
        verify_ssl: bool = True,
        force_api_key: bool = False,
    ):
        _conn = CaseInsensitiveDict(conn or {})
        fragments = fragments or []

        super().__init__(cast(logging.Logger, _conn.get("Logger", None)) or get_logger())
        self.s.verify = verify_ssl

        scheme = _conn.get("Scheme", "http")
        if domain := cast(str, _conn.get("Domain")):
            self.log.warning("conn['Domain'] is deprecated use conn['Host'] instead")
            host = domain
        else:
            host = _conn.get("Host", "localhost")

        if host == "0.0.0.0":
            host = "127.0.0.1"

        self.port = cast(int, _conn.get("Port", 9999))

        # Stash GraphQL endpoint
        self.url = f"{scheme}://{host}:{self.port}/graphql"

        # ApiKey authentication
        if api_key := cast(str, _conn.get("ApiKey")):
            self.s.headers.update({"ApiKey": api_key})

        # Session cookie for authentication
        if _conn.get("SessionCookie"):
            self.s.cookies.update({"session": cast(SessionCookie, _conn["SessionCookie"])["Value"]})

        try:
            # test query to ensure good connection
            self.version = self.stash_version()
        except Exception as e:
            self.log.error(f"Could not connect to Stash at {self.url}")
            self.log.error(e)
            raise

        self.log.debug(f"Using stash ({self.version}) endpoint at {self.url}")

        # grab API key to persist connection past session cookie duration
        query = """
            query getApiKey {
                configuration { general { apiKey } }
            }
        """

        if force_api_key:
            result = cast(dict[str, JSON], self.call_GQL(query)["configuration"])
            stash_api_key = cast(str, cast(dict[str, JSON], result["general"])["apiKey"])

            if stash_api_key:
                self.log.debug("Persisting Connection to Stash with ApiKey...")
                self.s.headers.update({"ApiKey": stash_api_key})
                self.s.cookies.clear()

        fragment_overrides = {
            "Scene": "{ id }",
            "Studio": "{ id }",
            "Performer": "{ id }",
            "Image": "{ id }",
            "Gallery": "{ id }",
            "Group": "{ id }",
        }
        attribute_overrides: dict[str, dict[str, str | None]] = {
            "ScrapedStudio": {"parent": "{ stored_id }"},
            "Tag": {"parents": "{ id }", "children": "{ id }"},
            "Studio": {"parent_studio": "{ id }"},
            "VideoFile": {"fingerprint": None},
            "ImageFile": {"fingerprint": None},
            "GalleryFile": {"fingerprint": None},
            "Gallery": {"image": None},
        }

        self.fragments = self._get_fragments_introspection(fragment_overrides, attribute_overrides)

        for fragment in fragments:
            self.parse_fragments(fragment)

    def _parse_obj_for_ID(
        self,
        param: int | str | dict[str, str | int],
        str_key: str = "name",
    ) -> dict[str, str | int] | int | None:
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

    def __generic_find(
        self,
        query: str,
        item: dict[str, Any] | int,
        fragment: tuple[str, str | None] | None = None,
    ) -> dict[str, JSON] | None:
        item_id = None

        if isinstance(item, dict):
            if stored_id := cast(str | int, item.get("stored_id")):
                item_id = int(stored_id)
            if id := cast(str | int, item.get("id")):
                item_id = int(id)

        if isinstance(item, int):
            item_id = item

        if not item_id:
            return

        if fragment and (substitution := fragment[1]):
            pattern = fragment[0]
            query = re.sub(pattern, substitution, query)

        result = self.call_GQL(query, {"id": item_id})
        queryType = list(result.keys())[0]

        return cast(dict[str, JSON], result[queryType])

    def __match_alias_item(self, search: str, items: list[dict[str, JSON]]) -> list[dict[str, JSON]]:
        """
        Private function to match a name against a list of dicts (each containing at least "name", "id" and "aliases"
        keys) and return all matching dicts

        Args:
            search (str): search term to try to find in the name and aliases of the given items
            items (list[dict]): list of dicts with at least "name", "id", and "aliases" keys in which to search for
                the given search term

        Returns:
            A list of the given dicts that match the given search terms in either the "name" key or in one of the "aliases"
        """
        search = re.escape(search)

        for item in items:
            if re.match(rf"{search}$", cast(str, item["name"]), re.IGNORECASE):
                self.log.debug(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using primary name')
                return [item]

        item_matches: dict[int | str, dict[str, JSON]] = {}
        for item in items:
            aliases = cast(dict[str, JSON] | None, item["aliases"])
            if not aliases:
                continue

            for alias in aliases:
                if re.match(rf"{search}$", alias.strip(), re.IGNORECASE):
                    self.log.info(f'matched "{search}" to "{item["name"]}" ({item["id"]}) using alias')
                    item_matches[cast(int | str, item["id"])] = item

        return list(item_matches.values())

    def __match_performer_alias(
        self,
        search: dict[str, str | int],
        performers: list[dict[str, JSON]],
    ) -> list[dict[str, JSON]] | None:
        """
        Private function to match a performer dict (containing at least a `name` key, and optionally a
        `disambiguation` key) against a list of dicts (each containing at least `name` key, optionally
        `disambiguation` and `alias_list` (in newer versions of stash) or `aliases` (in older versions of stash)
        and return all matching dicts

        Args:
            search (dict): performer dictionary to try to find in the given list of performers. Should contain at least
                a `name` key with value of type `str`. Optionally, include a `disambiguiation` key with value `str`.
            performers (list[dict]): list of dicts with at least a `name` key in which to search for
                the given search term. Optionally include `disambiguiation` key and/or `alias_list`/`aliases` key

        Returns:
            A list of the given dicts that match the given search terms in either the `name` and `disambiguation` keys
            or in one of the `aliases`
        """
        # attempt to match exclusively to primary name
        for p in performers:
            if "disambiguation" in p and "disambiguation" in search:
                # ignore disambiguation if it does not match search
                if cast(str, search["disambiguation"]) not in cast(str, p["disambiguation"]):
                    continue

            if str_compare(cast(str, search["name"]), cast(str, p["name"])):
                self.log.debug(f'matched performer "{search["name"]}" to "{p["name"]}" ({p["id"]}) using primary name')
                return [p]

        performer_matches: dict[int, dict[str, JSON]] = {}
        # no match on primary name attempt aliases
        for p in performers:
            aliases: list[str] = []

            # new versions of stash NOTE: wont be needed after performer alias matching
            if p.get("alias_list"):
                aliases = cast(list[str], p["alias_list"])
            # old versions of stash
            elif p.get("aliases"):
                if not isinstance(p["aliases"], str):
                    # FIXME: Should this just be an exception?? It would save having to handle `None` in the callers
                    self.log.warning(f'Expecting type str for performer aliases not {type(p["aliases"])}')
                    return None

                alias_delim = re.search(RE_ALIAS_DELIM, p["aliases"])
                if alias_delim:
                    aliases = p["aliases"].split(alias_delim.group(1))
                elif len(p["aliases"]) > 0:
                    # assume aliases is not a list, but a single alias
                    aliases = [p["aliases"]]
                else:
                    self.log.warning(f'Could not determine delim for aliases "{p["aliases"]}"')

            if not aliases:
                continue
            for alias in aliases:
                alias_search = cast(str, search["name"])

                if disambiguation := cast(str, search.get("disambiguation")):
                    # FIXME: why? where is stash ever returning the string "<performer name> <performer disambiguation>"?
                    alias_search += f" ({disambiguation})"

                parsed_alias = alias.strip()

                if str_compare(alias_search, parsed_alias):
                    self.log.info(f'matched performer "{alias_search}" to "{p["name"]}" ({p["id"]}) using alias')
                    performer_matches[cast(int, p["id"])] = p

        return list(performer_matches.values())

    def paginate_GQL(
        self,
        query: str,
        variables: dict[str, object] | None = None,
        pages: int = -1,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> dict[str, JSON] | None:
        """
        auto paginate graphql query with an optional callback to process items in each page

        Args:
            query (str): graphql query string
            variables (dict): graphql query variables
            pages (int, optional): number of pages to get results for, -1 for all pages. Defaults to -1.
            callback (_function_, optional): callback function to run results against between page calls. Defaults to None.
                If the given callback has parameters named "count" and/or "page_number", those values will be passed to
                the callback function when it is called.

        Returns:
            dict: all results from query up to specified page
        """
        variables = variables or {}
        if not "filter" in variables:
            variables["filter"] = {}
        assert isinstance(variables["filter"], dict)

        if not "page" in variables["filter"]:
            variables["filter"]["page"] = 1
        assert isinstance(variables["filter"]["page"], int)

        result = self._GQL(query, variables)

        query_type = list(result.keys())[0]
        result = result[query_type]
        assert isinstance(result, dict)

        itemType = list(result.keys())[1]
        items = result[itemType]
        assert isinstance(items, list)

        if callback:
            callback_response = None
            callback_sig = inspect.signature(callback)
            callback_kwargs = {}

            if "count" in callback_sig.parameters:
                callback_kwargs["count"] = result["count"]
            if "page_number" in callback_sig.parameters:
                callback_kwargs["page_number"] = variables["filter"]["page"]

            if callback_kwargs:
                callback_response = callback(items, **callback_kwargs)
            else:
                callback_response = callback(items)

            if callback_response == CallbackReturns.STOP_ITERATION:
                return

        if pages == -1:  # set to all pages if -1
            count = result["count"]
            assert isinstance(count, int)

            per_page = cast(int, variables["filter"]["per_page"])
            assert isinstance(per_page, int)

            pages = math.ceil(count / per_page)

        if variables["filter"]["page"] < pages:
            variables["filter"]["page"] += 1
            next_page = self.paginate_GQL(query, variables, pages, callback)
            if callback is None and next_page is not None:
                items.extend(next_page)

        if callback == None:
            return {query_type: {"count": len(items), itemType: items}}

        # FIXME: CallbackReturns only has one entry for STOP_ITERATION, meaning that if a callback function is
        # used, we should already have returned from this function by now
        return {query_type: {"count": 0, itemType: []}}

    @override
    def call_GQL(
        self,
        query: str,
        variables: dict[str, object] | None = None,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> dict[str, JSON]:
        if callback:
            # note: if `paginate_GQL` returns None, we return an empty dict so that we match the function signature
            # of the function we are overriding in the base class
            return self.paginate_GQL(query, variables, callback=callback) or {}
        else:
            return self._GQL(query, variables)

    def stash_version(self):
        result = self.call_GQL("query StashVersion{ version { build_time hash version } }")
        if result:
            version = cast(GQLStashVersion, cast(object, result["version"]))
            return StashVersion(version)

    @deprecated("Deprecated, use API SQL mutations")
    def get_sql_interface(self):
        self.log.warning("Deprecated use api SQL mutations (sql_query, sql_commit)")

    def sql_query(self, sql: str, args: list[Any] | None = None) -> GQLSqlQueryResponse:
        """
        Run an arbitrary SQL query against the Stash database

        Args:
            sql (str): The SQL query to run
            args (list, optional): Optional list of arguments to replace in the SQL query

        Returns:
            The result of the SQL query
        """
        args = args or []
        query = "mutation SQLquery($sql_query:String!, $sql_args:[Any]) { querySQL(sql: $sql_query, args: $sql_args){ ...SQLQueryResult } }"

        result = self.call_GQL(query, {"sql_query": sql, "sql_args": args})
        assert "querySQL" in result, f"Got malformed result when running a SQL query: {result}"

        return cast(GQLSqlQueryResponse, cast(object, result["querySQL"]))

    @deprecated("`sql_commit` is deprecated, use `sql_exec` instead")
    def sql_commit(self, sql: str, args: list[Any] | None = None) -> GQLSqlExecResponse:
        self.log.warning("`sql_commit` is deprecated, use `sql_exec` instead")
        return self.sql_exec(sql, args)

    def sql_exec(self, sql: str, args: list[Any] | None = None) -> GQLSqlExecResponse:
        """
        Execute an arbitrary SQL query against the Stash database

        Args:
            sql (str): The SQL query to execute
            args (list, optional): Optional list of arguments to replace in the SQL query

        Returns:
            A dictionary which may contain the following keys:
                rows_affected (int)
                last_insert_id (int)
        """
        args = args or []
        query = "mutation SQLcommit($sql_query:String!, $sql_args:[Any]) { execSQL(sql: $sql_query, args: $sql_args){ ...SQLExecResult } }"
        result = self.call_GQL(query, {"sql_query": sql, "sql_args": args})
        assert "execSQL" in result, f"Got malformed result when running a SQL query: {result}"

        return cast(GQLSqlExecResponse, cast(object, result["execSQL"]))

    def graphql_configuration(self) -> dict[str, JSON]:
        self.log.warning("Deprecated graphql_configuration() use get_configuration()")
        return self.get_configuration()

    def get_configuration(self, fragment: str | None = None) -> dict[str, JSON]:
        query = """
            query Configuration {
                configuration {
                    ...ConfigResult
                }
            }
        """
        if fragment:
            query = re.sub(r"\.\.\.ConfigResult", fragment, query)

        result = self.call_GQL(query)["configuration"]
        return cast(dict[str, JSON], result)

    def job_queue(self) -> GQLJob:
        result = self.call_GQL("query JobQueue { jobQueue{ ...Job } }")["jobQueue"]
        return cast(GQLJob, cast(object, result))

    def stop_job(self, job_id: int) -> bool:
        query = """
            mutation StopJob($job_id: ID!) {
                stopJob(job_id: $job_id)
            }
        """
        result = self.call_GQL(query, {"job_id": job_id})
        return cast(bool, result["stopJob"])

    def find_job(self, job_id: int) -> GQLJob:
        query = "query FindJob($input:FindJobInput!) { findJob(input: $input){ ...Job } }"
        result = self.call_GQL(query, {"input": {"id": job_id}})
        return cast(GQLJob, cast(object, result["findJob"]))

    def wait_for_job(
        self,
        job_id: int,
        status: JobStatus = GQLJobStatus.FINISHED,
        period: float = 1.5,
        timeout: int = 120,
    ) -> bool | None:
        """
        Waits for stash job to match the given status

        Args:
                job_id (int): the integer ID of the job to wait for
                status (str, optional): Desired status to wait for. Defaults to "FINISHED".
                period (float, optional): Interval between checks for job status. Defaults to 1.5.
                timeout (int, optional): time in seconds that if exceeded raises Exception. Defaults to 120.

        Raises:
                Exception: timeout raised if wait task takes longer than timeout

        Returns:
            None if the job could not be found, otherwise True if the job matches the specified status, or False if the
            job is finished or cancelled
        """
        timeout_value = time.time() + timeout
        while time.time() < timeout_value:
            job = self.find_job(job_id)
            if not job:
                return None

            self.log.debug(f'Waiting for Job:{job_id} Status:{job["status"]} Progress:{job.get("progress")}')

            if job["status"] == str(status):
                return True
            if job["status"] in [GQLJobStatus.FINISHED, GQLJobStatus.CANCELLED]:
                return False
            time.sleep(period)
        raise Exception(f"Hit timeout waiting for Job with ID '{job_id}' to complete")

    def get_configuration_defaults(self, default_field: str) -> dict[str, JSON]:
        query = f"""
            query ConfigurationDefaults {{
                configuration {{
                    defaults { default_field }
                }}
            }}
        """
        result = cast(dict[str, JSON], self.call_GQL(query)["configuration"])
        return cast(dict[str, JSON], result["defaults"])

    def metadata_scan(
        self,
        paths: list[str | Path] | None = None,
        flags: dict[str, Any] | None = None,
    ) -> int:
        """
        Trigger the metadataScan mutation on the given paths. Flags are used if provided, otherwise the default
        configuration is first fetched from Stash

        Args:
            paths (list[str | Path]): Paths to scan
            flags (dict[str, Any]): Configuration to use for the scan. If not provided, current configuration is
                fetched from Stash

        Returns:
            The integer ID of the triggered scan job
        """
        paths = paths or []
        flags = flags or {}

        query = """
            mutation MetadataScan($input:ScanMetadataInput!) {
                metadataScan(input: $input)
            }
        """
        scan_metadata_input: dict[str, object] = {"paths": paths}
        if flags:
            scan_metadata_input.update(flags)
        elif scan_config := self.get_configuration_defaults("scan { ...ScanMetadataOptions }").get("scan"):
            scan_metadata_input.update(cast(dict[str, JSON], scan_config))

        result = self.call_GQL(query, {"input": scan_metadata_input})["metadataScan"]
        return cast(int, result)

    def metadata_generate(self, flags: dict[str, Any] | None = None) -> int:
        """
        Trigger the metadataGenerate mutation. Flags are used if provided, otherwise the default configuration is first
        fetched from Stash

        Args:
            flags (dict[str, Any]): Configuration to use for the generate job. If not provided, current configuration
                is fetched from Stash

        Returns:
            The integer ID of the triggered scan job
        """
        flags = flags or {}

        query = """
            mutation MetadataGenerate($input:GenerateMetadataInput!) {
                metadataGenerate(input: $input)
            }
        """
        if flags:
            generate_metadata_input = flags
        else:
            generate_metadata_input = self.get_configuration_defaults("generate { ...GenerateMetadataOptions }")[
                "generate"
            ]
        result = self.call_GQL(query, {"input": generate_metadata_input})["metadataGenerate"]
        return cast(int, result)

    def metadata_clean(self, paths: list[Path | str] | None = None, dry_run: bool = False) -> int:
        """
        Trigger the metadataClean mutation on the given paths. Optionally, trigger a dry_run.

        Args:
            paths (list[str | Path]): Paths to clean
            dry_run (bool, optional): Set to True to trigger a dry-run (default: False)

        Returns:
            The integer ID of the triggered clean job
        """
        paths = paths or []
        query = """
            mutation MetadataClean($input:CleanMetadataInput!) {
                metadataClean(input: $input)
            }
        """

        clean_metadata_input = {"paths": paths, "dryRun": dry_run}
        result = self.call_GQL(query, {"input": clean_metadata_input})["metadataClean"]
        return cast(int, result)

    def metadata_autotag(
        self,
        paths: list[Path | str] | None = None,
        performers: list[int | Literal["*"]] | None = None,
        studios: list[int | Literal["*"]] | None = None,
        tags: list[int | Literal["*"]] | None = None,
    ) -> int:
        """
        Trigger the metadataAutotag mutation on the given paths, performers, studios, and/or tags.

        Args:
            paths (list[str | Path]): Paths to clean
            performers (list[int | Literal["*"]]): List of integer performer IDs to scan, or simply the string "*" to scan all
            studios (list[int | Literal["*"]]): List of integer studio IDs to scan, or simply the string "*" to scan all
            tags (list[int | Literal["*"]]): List of integer tag IDs to scan, or simply the string "*" to scan all

        Returns:
            The integer ID of the triggered autotag job
        """
        query = """
            mutation MetadataAutoTag($input:AutoTagMetadataInput!) {
                metadataAutoTag(input: $input)
            }
        """
        metadata_autotag_input = {
            "paths": paths or [],
            "performers": performers or [],
            "studios": studios or [],
            "tags": tags or [],
        }
        result = self.call_GQL(query, {"input": metadata_autotag_input})["metadataAutotag"]
        return cast(int, result)

    def metadata_clean_generated(
        self,
        blobFiles: bool = True,
        dryRun: bool = False,
        imageThumbnails: bool = True,
        markers: bool = True,
        screenshots: bool = True,
        sprites: bool = True,
        transcodes: bool = True,
    ) -> int:
        """
        Trigger the metadataCleanGenerated mutation. Use the parameters to select which clean steps should be performed

        Args:
            blobFiles (bool, optional): Whether or not to generated clean blob files (default: True)
            dryRun (bool, optional): Whether or not to perform a dry-run (default: False)
            imageThumbnails (bool, optional): Whether or not to clean generated image thumbnails (default: True)
            markers (bool, optional): Whether or not to clean genereated markers (default: True)
            screenshots (bool, optional): Whether or not to clean screenshots markers (default: True)
            sprites (bool, optional): Whether or not to clean genereated sprites (default: True)
            transcodes (bool, optional): Whether or not to clean genereated transcodes (default: True)

        Returns:
            The integer ID of the triggered generated clean job
        """
        query = """
            mutation MetadataCleanGenerated($input: CleanGeneratedInput!) {
                metadataCleanGenerated(input: $input)
            }
        """
        clean_metadata_input = {
            "blobFiles": blobFiles,
            "dryRun": dryRun,
            "imageThumbnails": imageThumbnails,
            "markers": markers,
            "screenshots": screenshots,
            "sprites": sprites,
            "transcodes": transcodes,
        }
        result = self.call_GQL(query, {"input": clean_metadata_input})["metadataCleanGenerated"]
        return cast(int, result)

    def backup_database(self):
        """
        Trigger the backupDatabase mutation.

        Returns:
            The integer ID of the triggered backup job
        """
        query = """
            mutation BackupDatabase {
                backupDatabase(input: { download: false })
            }
        """
        result = self.call_GQL(query)["backupDatabase"]
        return cast(int, result)

    def optimise_database(self) -> int:
        """
        Trigger the optimizeDatabase mutation.

        Returns:
            The integer ID of the triggered optimize job
        """
        query = """
            mutation OptimiseDatabase {
                optimiseDatabase
            }
        """
        result = self.call_GQL(query)["optimiseDatabase"]
        return cast(int, result)

    def file_set_fingerprints(self, file_id: int, fingerprints: list[GQLSetFingerprintsInput]) -> bool:
        """
        Trigger the fileSetFingerprints mutation in order to assign the given fingerprints to the file with the
        given integer ID

        Args:
            file_id (int): Integer ID of the file to modify
            fingerprints (int): List of dictionaries of fingerprint information.
                Each dictionary is expected to have "type" and "value" entries which describe the fingerprint

        Returns:
            True if the mutation was successful, False otherwise
        """
        # FIXME: feels like this check should not be necessary since the file_id parameter is mandatory?
        if not file_id:
            return False

        query = """
            mutation FileSetFingerprints($input: FileSetFingerprintsInput!) {
                fileSetFingerprints(input: $input)
            }
        """

        variables: dict[str, object] = {"input": {"id": file_id, "fingerprints": fingerprints}}
        result = self.call_GQL(query, variables)["fileSetFingerprints"]
        return cast(bool, result)

    def destroy_files(self, file_ids: list[int]) -> bool:
        """
        Trigger the deleteFiles mutation in order to delete the files with the given integer IDs

        Args:
            file_id (int): Integer ID of the file to delete

        Returns:
            True if the mutation was successful, False otherwise
        """
        if not file_ids:
            return False

        query = """
            mutation DeleteFiles($ids: [ID!]!) {
                deleteFiles(ids: $ids)
            }
        """
        variables: dict[str, object] = {"ids": file_ids}
        result = self.call_GQL(query, variables)["deleteFiles"]
        return cast(bool, result)

    # FILES
    def move_files(self, move_files_input: GQLMoveFilesInput) -> bool:
        """
        Trigger the moveFiles mutation in order to move the files with the given integer IDs to the target directory.

        Args:
            move_files_input (GQLMoveFilesInput): A dictionary containing the following keys:
                ids: list of integer IDs of files to move
                one of the following two keys specifying the target folder:
                    destination_folder: string path to destination folder
                    destination_folder_id: integer ID of a destination folder known to Stash
                destination_basename: optional string basename of the file in the destination

        Returns:
            True if the mutation was successful, False otherwise
        """
        query = """
            mutation MoveFiles($input: MoveFilesInput!) {
                moveFiles(input: $input)
            }
        """
        result = self.call_GQL(query, {"input": move_files_input})["moveFiles"]
        return cast(bool, result)

    # PLUGINS
    def configure_plugin(self, plugin_id: str, values: dict[str, Any], init_defaults: bool = False) -> dict[str, JSON]:
        """
        Set configuration values for the plugin with the given plugin id

        Args:
            plugin_id (str): the name of the config.yml file
            values (dict): plugin configuration values to set
            init_defaults (bool, optional): use values to initialize configuration values, existing configuration will override passed values. Defaults to False.

        Returns:
            dict: current plugin configuration values
        """
        query = """
            mutation ConfigurePlugin($plugin_id: ID!, $input: Map!) {
                configurePlugin(plugin_id: $plugin_id, input: $input)
            }
        """
        plugin_values = self.find_plugin_config(plugin_id)
        if init_defaults:
            values.update(plugin_values)
        plugin_values.update(values)

        result = self.call_GQL(query, {"plugin_id": plugin_id, "input": plugin_values})["configurePlugin"]
        return cast(dict[str, JSON], result)

    def find_plugin_config(self, plugin_id: str, defaults: dict[str, Any] | None = None) -> dict[str, JSON]:
        """
        Finds the current configuration for the plugin with the given plugin id, optionally setting the plugin
        configuration to the given defaults if no configuration is found.

        Args:
            plugin_id (str): the name of the config.yml file
            defaults (dict[str, Any], optional): default values to configure the plugin with if no configuration
                is found. (default: empty dict).

        Returns:
            dict[str, Any]: current plugin configuration values
        """
        if defaults:
            return self.configure_plugin(plugin_id, defaults, init_defaults=True)

        return self.find_plugins_config(plugin_id)

    def find_plugins_config(self, plugin_ids: list[str] | str | None) -> dict[str, JSON]:
        """
        Finds the configuration information for one or more plugins

        Args:
            plugin_ids (list[str], str, optional): List of string plugin ids or string of plugin id to retrieve.
                If omitted or set to an empty list, values for all plugins is returned.
                (default: None, returns info on all plugins).

        Returns:
            If no plugins are found, returns an empty dictionary. Otherwise:
                If called with a string or a list containing only a single plugin id, returns the configuration
                dictionary for the given plugin.
                If called with a list containing multiple plugins, returns a dictionary of plugin configurations,
                where the keys are the plugin ids
        """
        query = """
            query FindPluginConfig($input: [ID!]){
                configuration {
                    plugins (include: $input)
                }
            }
        """

        plugin_ids = plugin_ids or []
        if isinstance(plugin_ids, str):
            plugin_ids = [plugin_ids]

        result = cast(dict[str, JSON], self.call_GQL(query, {"input": plugin_ids})["configuration"])
        config = cast(dict[str, JSON], result["plugins"])

        if len(plugin_ids) == 1:
            config = config.get(plugin_ids[0])

        if config:
            return cast(dict[str, JSON], config)
        else:
            self.log.debug(f"no plugin configs found with any of the following IDs: {plugin_ids}")
            return {}

    def run_plugin_task(
        self,
        plugin_id: int,
        task_name: str,
        args: dict[str, str | int | bool | float | Any] | None = None,
    ):
        """
        Queues a plugin task to run

        Args:
            plugin_id (int): Integer plugin ID
            task_name (str): plugin task to perform, task must exist in plugin config
            args (dict, optional): arguments to pass to plugin. Note that only str, int, float and bool arguments will
                be passed to the config. Other types are silently dropped. (default: empty dict)

        Returns:
            The integer ID of the triggered backup job
        """
        args = args or {}
        query = """
            mutation RunPluginTask($plugin_id: ID!, $task_name: String!, $args: [PluginArgInput!]) {
                runPluginTask(plugin_id: $plugin_id, task_name: $task_name, args: $args)
            }
        """

        args_list: list[dict[str, Any]] = []
        for k, v in args.items():
            if isinstance(v, str):
                value = {"str": v}
            elif isinstance(v, int):
                value = {"i": v}
            elif isinstance(v, bool):
                value = {"b": v}
            elif isinstance(v, float):
                value = {"f": v}
            else:
                continue
            args_list.append({"key": k, "value": value})

        variables: dict[str, object] = {
            "plugin_id": plugin_id,
            "task_name": task_name,
            "args": args_list,
        }

        result = self.call_GQL(query, variables)["runPluginTask"]
        return cast(dict[str, JSON], result)

    # TAG
    def create_tag(self, tag_in: GQLTagCreateInput) -> dict[str, JSON]:
        """
        Creates a tag with the given details

        Args:
            tag_in (GQLTagCreateInput): Parameters which will be used to create the tag

        Returns:
            The dictionary representing the tag as created by Stash
        """

        query = """
            mutation tagCreate($input:TagCreateInput!) {
                tagCreate(input: $input){
                    ...Tag
                }
            }
        """
        variables: dict[str, object] = {"input": tag_in}

        result = self.call_GQL(query, variables)["tagCreate"]
        return cast(dict[str, JSON], result)

    def find_tag(
        self,
        tag_in: int | str | dict[str, str | int],
        create: bool = False,
        fragment: str | None = None,
        on_multiple: OnMultipleMatch = OnMultipleMatch.RETURN_FIRST,
    ) -> list[dict[str, JSON]] | dict[str, JSON] | None:
        """
        Looks for a tag matching the given integer ID, name, or alias(es)

        Args:
            tag_in (int, str, dict): Tag ID, name, or dict to find.
            create (bool, optional): Creates the tag if it does not exist. Defaults to False.
            fragment (str, optional): override for gqlFragment. Defaults to "...Tag". example override 'fragment="id name"'
            on_multiple (OnMultipleMatch): behavior if multiple matching tags are found. Default: RETURN_FIRST

        Returns:
            dict: stash Tag dict
        """

        # assume input is an ID if int
        if isinstance(tag_in, int):
            query = """
                query FindTag($id: ID!) {
                    findTag(id: $id) { ...Tag }
                }
            """
            return self.__generic_find(query, tag_in, (r"\.\.\.Tag", fragment))

        name = None

        if isinstance(tag_in, dict):
            if tag_in.get("stored_id"):
                try:
                    stored_id = int(tag_in["stored_id"])
                    return self.find_tag(stored_id, fragment=fragment)
                except:
                    del tag_in["stored_id"]
            if tag_in.get("name"):
                name = cast(str, tag_in["name"])

        if isinstance(tag_in, str):
            name = tag_in.strip()
            tag_in = {"name": name}

        if not name:
            self.log.warning(f'find_tag expects int, str, or dict not {type(tag_in)} "{tag_in}"')
            return

        matches: set[int] | list[int] = set()
        tags = cast(list[dict[str, JSON]], self.find_tags(q=name, fragment="id name aliases"))
        for tag in tags:
            if str_compare(cast(str, tag["name"]), name):
                matches.add(cast(int, tag["id"]))

            if any(str_compare(alias, name) for alias in cast(list[str], tag["aliases"])):
                matches.add(cast(int, tag["id"]))

        matches = list(matches)
        if len(matches) > 1:
            msg = f"Matched multiple tags with {name=} {matches}"
            match on_multiple:
                case OnMultipleMatch.RETURN_NONE:
                    self.log.debug(f"{msg} returning None")
                    return None
                case OnMultipleMatch.RETURN_LIST:
                    self.log.debug(f"{msg} returning all matches")
                    found = [self.find_tag(int(tag_id), fragment=fragment) for tag_id in matches]
                    return cast(list[dict[str, JSON]], list(filter(None, found)))
                case OnMultipleMatch.RETURN_FIRST:
                    self.log.debug(f"{msg} returning first match")
                    # singular match returned from next if-statement

        if matches:
            return self.find_tag(int(matches[0]), fragment=fragment)

        if create:
            self.log.info(f"Could not find tag with {name=} creating")
            # at this point we know that tag_in contains at least a key `name` with str value, which is all that is
            # required to createa a new tag. Any unrecognized keys will just be ignored
            creation_options = cast(GQLTagCreateInput, cast(object, tag_in))

            return self.create_tag(creation_options)

    def update_tag(self, tag_update: GQLTagUpdateInput) -> dict[str, JSON]:
        """
        Update the tag per the given inputs

        Args:
            tag_update (GQLTagUpdateInput): see type def or playground for details

        Returns:
            A dictionary containing information on the updated tag from Stash
        """
        query = """
            mutation TagUpdate($input: TagUpdateInput!) {
                tagUpdate(input: $input) {
                    id
                }
            }
        """

        variables: dict[str, object] = {"input": tag_update}

        result = self.call_GQL(query, variables)["tagUpdate"]
        return cast(dict[str, JSON], result)

    def destroy_tag(self, tag_id: int) -> bool:
        """
        Deletes tag from stash

        Args:
            tag_id (int): tag ID from stash

        Returns:
            True if the operation was successful, False otherwise
        """

        query = """
            mutation tagDestroy($input: TagDestroyInput!) {
                tagDestroy(input: $input)
            }
        """
        variables: dict[str, object] = {"input": {"id": tag_id}}

        result = self.call_GQL(query, variables)["tagDestroy"]
        return cast(bool, result)

    # TAGS
    def find_tags(
        self,
        f: GQLTagFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Gets tags matching filter/query

        Args:
            f (GQLTagFilterType, optional): See playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional): override for gqlFragment. Defaults to "...Tag". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [tags]) where count is the number of results from the query, useful when paging. Defaults to False.

        Returns:
            _type_: list of tags, or tuple of (count, [tags])
        """

        f = f or {}
        filter = filter or {"per_page": -1}

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
            query = re.sub(r"\.\.\.Tag", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "tag_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables)["findTags"])
        count = cast(int, result["count"])
        tags = cast(list[dict[str, JSON]], result["tags"])
        if get_count:
            return count, tags
        else:
            return tags

    def merge_tags(self, source_ids: list[int], destination_id: int) -> bool:
        """
        Merges tag ids in source_ids into tag with destination_id

        Args:
            source_ids (list[int]): List of tags IDs to be merged
            destination_id (int): ID of tag in which to merge the source tags

        Returns:
            True if the operation was a success, False otherwise
        """
        query = """
            mutation($source: [ID!]!, $destination: ID!) {
                tagsMerge(input: {source: $source, destination: $destination}) {
                    ...Tag
                }
            }
        """

        variables: dict[str, object] = {"source": source_ids, "destination": destination_id}
        result = self.call_GQL(query, variables)["tagsMerge"]
        return cast(bool, result)

    def map_tag_ids(self, tags_input: list[str | int | dict[str, str | int]], create: bool = False) -> list[int]:
        """
        Searches for tags matching the given criteria, optionally creating them if the `create` parameter is True.

        Args:
            tags_input (): the tags to search for and optionally create
            create (bool): whether or not to create tags that are not found

        Returns:
            A list of tag IDs which were either found or created based on the given inputs
        """
        tag_ids: list[int] = []
        for tag_input in tags_input:
            if tag := cast(
                dict[str, JSON], self.find_tag(tag_input, create=create, on_multiple=OnMultipleMatch.RETURN_NONE)
            ):
                tag_ids.append(cast(int, tag["id"]))

        return tag_ids

    def destroy_tags(self, tag_ids: list[int]):
        """deletes tags from stash

        Args:
                 tag_ids ([int]): tag IDs from stash to delete
        """

        query = """
            mutation tagsDestroy($ids: [ID!]!) {
                tagsDestroy(ids: $ids)
            }
        """

        self.call_GQL(query, {"ids": tag_ids})

    # PERFORMER
    def create_performer(self, performer_in: GQLPerformerCreateInput) -> dict[str, JSON]:
        """
        Creates performer in Stash

        Args:
            performer_in (GQLPerformerCreateInput): see type def or playground for details

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

        variables: dict[str, object] = {"input": performer_in}

        result = self.call_GQL(query, variables)["performerCreate"]
        return cast(dict[str, JSON], result)

    def find_performer(
        self,
        performer: int | str | dict[str, str | int],
        create: bool = False,
        fragment: str | None = None,
        on_multiple: OnMultipleMatch = OnMultipleMatch.RETURN_FIRST,
    ) -> list[dict[str, JSON]] | dict[str, JSON] | None:
        """
        Looks for performer from stash, matching on name or aliases

        Args:
            performer (int, str, dict): int of performer id, str of performer name/alias, dict of performer object
            create (bool, optional): create performer if not found. Defaults to False.

        Returns:
            dict: stash performer object
        """
        _performer = self._parse_obj_for_ID(performer)

        if not _performer:
            self.log.warning(f'find_performer() expects int, str, or dict not {type(performer)} "{performer}"')
            return

        # assume input is an ID if int
        if isinstance(_performer, int):
            query = """
                query FindPerformer($id: ID!) {
                    findPerformer(id: $id) { ...Performer }
                }
            """
            return self.__generic_find(query, _performer, (r"\.\.\.Performer", fragment))

        performer_filter: GQLPerformerFilterType = {}
        if disambiguation := cast(str, _performer.get("disambiguation")):
            performer_filter = {
                "disambiguation": {"value": disambiguation, "modifier": "INCLUDES"},
                "OR": {"aliases": {"value": disambiguation, "modifier": "INCLUDES"}},
            }

        name = cast(str, _performer["name"])
        performer_search = cast(
            list[dict[str, JSON]],
            self.find_performers(q=name, f=performer_filter, fragment="id name disambiguation alias_list"),
        )
        performer_matches = self.__match_performer_alias(_performer, performer_search)

        if performer_matches and len(performer_matches) > 1:
            warn_msg = f"Matched multiple Performers to '{_performer['name']}'"
            match on_multiple:
                case OnMultipleMatch.RETURN_NONE:
                    self.log.warning(f"{warn_msg} returning None")
                    return None
                case OnMultipleMatch.RETURN_LIST:
                    self.log.warning(f"{warn_msg} returning all matches")
                    found = [
                        self.find_performer(int(cast(int | str, p["id"])), fragment=fragment) for p in performer_matches
                    ]
                    return cast(list[dict[str, JSON]], list(filter(None, found)))
                case OnMultipleMatch.RETURN_FIRST:
                    self.log.warning(f"{warn_msg} returning first match")
                    # singular match returned from next if-statement

        if performer_matches:
            return self.find_performer(int(cast(str | int, performer_matches[0]["id"])), fragment=fragment)

        if create:
            self.log.info(f'Create missing performer: "{_performer["name"]}"')

            # at this point we know that _performer contains at least a key `name` with str value, which is all that is
            # required to createa a new performer. Any unrecognized keys will just be ignored
            creation_options = cast(GQLPerformerCreateInput, cast(object, _performer))
            return self.create_performer(creation_options)

    def update_performer(self, performer_in: GQLPerformerUpdateInput) -> dict[str, JSON]:
        """
        Updates an existing performer

        Args:
            performer_in (GQLPerformerUpdateInput): see type def or playground for details

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
        variables: dict[str, object] = {"input": performer_in}

        result = self.call_GQL(query, variables)["performerUpdate"]
        return cast(dict[str, JSON], result)

    def destroy_performer(self, performer_ids: int | list[int]) -> bool:
        """
        Deletes the given performer(s)

        Args:
            performer_ids (int | list[int]): Performer id(s) to delete

        Returns:
            True if the operation was successful, False otherwise
        """
        if not isinstance(performer_ids, (int, list)):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise Exception("destroy_gallery only accepts an int or list of ints")  # pyright: ignore[reportUnreachable]

        if isinstance(performer_ids, int):
            performer_ids = [performer_ids]

        query = """
            mutation performersDestroy($performer_ids:[ID!]!) {
                performersDestroy(ids: $performer_ids)
            }
        """
        result = self.call_GQL(query, {"performer_ids": performer_ids})["performersDestroy"]
        return cast(bool, result)

    def merge_performers(self, source: list, destination, values={}):

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

        ignore_attrs = ["id", "name"]
        use_longest_string = [
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
                    performer_update["stash_ids"].extend(
                        [id for id in source["stash_ids"] if id["stash_id"] not in existing_ids]
                    )
                    continue
                if d_attr == "tags":
                    performer_update["tag_ids"].extend([t["id"] for t in source["tags"]])
                    performer_update["tag_ids"] = list(set(performer_update["tag_ids"]))
                    continue
                if d_attr == "alias_list":
                    source_name = source["name"]
                    if source.get("disambiguation"):
                        source_name = f'{source_name} ({source["disambiguation"]})'
                    performer_update["alias_list"].append(source_name)
                    performer_update["alias_list"].extend(source["alias_list"])
                    performer_update["alias_list"] = list(set(performer_update["alias_list"]))
                    continue
                if not performer_update[d_attr] and d_attr in source and source[d_attr]:
                    performer_update[d_attr] = source[d_attr]

        # merge all values of disambiguation
        disambiguation_list = [performer_update["disambiguation"]]
        disambiguation_list.extend([s["disambiguation"] for s in sources])
        performer_update["disambiguation"] = ", ".join([d for d in disambiguation_list if d])

        # remove 'name' from alias_list to avoid GQL error on update
        performer_update["alias_list"] = [a for a in performer_update["alias_list"] if a != performer_update["name"]]

        # Fix for case-insensitive alias conflict
        alias_map_lowercase = {}
        for alias in performer_update["alias_list"]:
            if alias.lower() in alias_map_lowercase:
                continue
            alias_map_lowercase[alias.lower()] = alias
        performer_update["alias_list"] = list(alias_map_lowercase.values())

        self.update_performer(performer_update)

        source_ids = [p["id"] for p in sources]
        # reassign items with performers
        scenes = self.find_scenes(f={"performers": {"value": source_ids, "modifier": "INCLUDES"}}, fragment="id")
        if scenes:
            self.update_scenes(
                {"ids": [s["id"] for s in scenes], "performer_ids": {"ids": [destination["id"]], "mode": "ADD"}}
            )
        galleries = self.find_galleries(f={"performers": {"value": source_ids, "modifier": "INCLUDES"}}, fragment="id")
        if galleries:
            self.update_galleries(
                {"ids": [g["id"] for g in galleries], "performer_ids": {"ids": [destination["id"]], "mode": "ADD"}}
            )
        images = self.find_images(f={"performers": {"value": source_ids, "modifier": "INCLUDES"}}, fragment="id")
        if images:
            self.update_images(
                {"ids": [i["id"] for i in images], "performer_ids": {"ids": [destination["id"]], "mode": "ADD"}}
            )

        self.destroy_performer(source_ids)

    # PERFORMERS
    def find_performers(
        self,
        f: GQLPerformerFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Get performers matching filter/query

        Args:
            f (PerformerFilterType, optional): See playground for details. Defaults to {}.
            filter (FindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional):  override for gqlFragment. Defaults to "...Performer". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [performers]) where count is the number of results from the query, useful when paging. Defaults to False.

        Returns:
            _type_: list of performer objects or tuple with count and list (count, [performers])
        """
        f = f or {}
        filter = filter or {"per_page": -1}

        query = """
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
            query = re.sub(r"\.\.\.Performer", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "performer_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables, callback=callback)["findPerformers"])
        count = cast(int, result["count"])
        performers = cast(list[dict[str, JSON]], result["performers"])

        if get_count:
            return count, performers
        else:
            return performers

    def update_performers(self, bulk_performer_update_input: GQLBulkPerformerUpdateInput) -> list[dict[str, JSON]]:
        """
        Update multiple existing performers

        Args:
            bulk_performer_update_input (GQLBulkPerformerUpdateInput):  see type def or playground for details

        Returns:
            list of stash performer objects
        """
        query = """
            mutation BulkPerformerUpdate($input:BulkPerformerUpdateInput!) {
                bulkPerformerUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": bulk_performer_update_input}

        result = cast(list[dict[str, JSON]], self.call_GQL(query, variables)["bulkPerformerUpdate"])
        return result

    def map_performer_ids(
        self,
        performers_input: list[str | int | dict[str, str | int]],
        create: bool = False,
    ) -> list[int]:
        performer_ids: list[int] = []
        for performer_input in performers_input:
            if performer := cast(
                dict[str, JSON],
                self.find_performer(
                    performer_input, create=create, fragment="id", on_multiple=OnMultipleMatch.RETURN_NONE
                ),
            ):
                performer_ids.append(cast(int, performer["id"]))

        return performer_ids

    # Studio CRUD
    def create_studio(self, studio_create_input: GQLStudioCreateInput) -> dict[str, JSON]:
        """
        Create a studio in Stash

        Args:
            studio (GQLStudioCreateInput): see type def or playground for details

        Returns:
            dict: Information on the created studio from Stash
        """
        query = """
            mutation StudioCreate($input: StudioCreateInput!) {
                studioCreate(input: $input) {
                    ...Studio
                }
            }
        """
        variables: dict[str, object] = {"input": studio_create_input}

        result = cast(dict[str, JSON], self.call_GQL(query, variables)["studioCreate"])
        return result

    def find_studio(
        self, studio: int | str | dict[str, Any], fragment: str | None = None, create: bool = False
    ) -> dict[str, JSON] | None:
        """
        Looks for a studio by matching against the given studio information, optionally creating the studio if a
        match is not found.
        If `studio` is an integer, search for studios with a matching ID.
        If `studio` is a string, check it against studio names and aliases.
        If `studio` is a dict containing a `url` key, look for a *single* studio with a matching URL. If multiple
        studios with a matching URL are found, all of them will be ignored.

        Args:
            studio (int, str, dict): int, str, dict of studio to search for
            create (bool, optional): create studio if not found. Defaults to False.

        Returns:
            dict: Studio information according to the provided fragment, or if omitted, all of the infmormation
                for the studio
        """
        _studio = self._parse_obj_for_ID(studio)

        if not _studio:
            self.log.warning(f'find_studio() expects int, str, or dict not {type(studio)} "{studio}"')
            return None

        if isinstance(_studio, int):
            query = """
                query FindStudio($id: ID!) {
                    findStudio(id: $id) { ...Studio }
                }
            """
            return self.__generic_find(query, _studio, (r"\.\.\.Studio", fragment))

        studio_matches: list[dict[str, JSON]] = []

        if url := cast(str, _studio.get("url")):
            url_search = cast(
                list[dict[str, JSON]],
                self.find_studios(
                    f={"url": {"value": url, "modifier": GQLCriterionModifier.INCLUDES}}, fragment="id name"
                ),
            )
            if len(url_search) == 1:
                studio_matches.extend(url_search)

        if name := cast(str, _studio.get("name")):
            _studio["name"] = name.strip()
            name_results = cast(list[dict[str, JSON]], self.find_studios(q=name, fragment="id name aliases"))
            studio_matches.extend(self.__match_alias_item(name, name_results))

        # FIXME: what's going on here?? Is matching against multiple studio names separated by spaces meant to be
        # supported? If so, does the regex in __match_alias_item actually work to do that?
        if len(studio_matches) > 1 and name.count(" ") == 0:
            return None
        elif studio_matches:
            return self.find_studio(cast(int | str, studio_matches[0]["id"]), fragment=fragment)

        if create and name:
            self.log.info(f'Create missing studio: "{name}"')

            # at this point, we know `_studio` contains a "name" key that is a string, which is the minimum requirement
            # to create a studio. Any unrecognized keys will just be ignored
            creation_options = cast(GQLStudioCreateInput, cast(object, _studio))
            return self.create_studio(creation_options)

    def update_studio(self, studio: GQLStudioCreateInput) -> dict[str, JSON]:
        """
        Update existing studio on Stash

        Args:
            studio (GQLStudioUpdateInput): see type def or playground for details

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
        variables: dict[str, object] = {"input": studio}

        result = cast(dict[str, JSON], self.call_GQL(query, variables)["studioUpdate"])
        return result

    # TODO destroy_studio()

    # Studio Utils
    def find_studio_hierarchy(
        self,
        studio: int | str | dict[str, Any],
        fragment: str | None = None,
        hierarchy: list[dict[str, JSON]] | None = None,
    ) -> list[dict[str, JSON]]:
        """
        Find all parents of the given studio.

        Args:
            studio (int, str, dict): the studio for which parents will be found
            fragment (str, optional): fragment specifying the data to retrieve for each studio
            hierarchy: you almost certainly don't want to use this

        Returns:
            A list of studios, with the first entry being the root (topmost) studio
        """
        hierarchy = hierarchy or []

        if found := self.find_studio(studio, fragment):
            hierarchy.append(found)

        s = self.find_studio(studio, "id parent_studio { id }")
        if not (s and s.get("parent_studio")):
            return hierarchy[::-1]  # invert hierarchy so root is at idx 0

        return self.find_studio_hierarchy(cast(dict[str, JSON], s["parent_studio"]), fragment, hierarchy)

    def find_studio_root(
        self,
        studio: int | str | dict[str, Any],
        fragment: str | None = None,
    ) -> dict[str, JSON] | None:
        """
        Find the root studio (i.e. topmost studio) for the given studio

        Args:
            studio (int | str | dict): The studio for which the root studio will be found

        Returns:
            The root studio if found, None otherwise
        """
        s = self.find_studio(studio, "id parent_studio { id }")

        if s:
            if parent_studio := s.get("parent_studio"):
                return self.find_studio_root(cast(dict[str, JSON], parent_studio))

            return self.find_studio(s, fragment)

        # FIXME: should this really return None if no root studio is found? Technically, the studio that is passed
        # in as a parameter would be the root studio if it has no parent, right?
        return None

    # BULK Studios
    def find_studios(
        self,
        f: GQLStudioFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Get studios matching filter/query

        Args:
            f (GQLStudioFilterType, optional): See playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (_type_, optional): override for gqlFragment. Defaults to "...Studio". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [studios]) where count is the number of results from the query, useful when paging. Defaults to False.

        Returns:
            _type_: list of studio objects from stash, or tuple (count, [studios])
        """
        f = f or {}
        filter = filter or {"per_page": -1}

        query = """
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
            query = re.sub(r"\.\.\.Studio", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "studio_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables)["findStudios"])
        studios = cast(list[dict[str, JSON]], result["studios"])
        count = cast(int, result["count"])

        if get_count:
            return count, studios
        else:
            return studios

    # GROUP
    def create_group(self, group_in: str | GQLGroupCreateInput) -> dict[str, JSON]:
        """
        Creates a group in Stash

        Args:
            group_in (GQLPerformerCreateInput | str): str will be treated as the group name, see type def or
                playground for details on GQLPerformerCreateInput

        Returns:
            Information on the created group from Stash
        """
        if isinstance(group_in, str):
            group_in = {"name": group_in}

        if not isinstance(group_in, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            # FIXME: this should probably just raise an exception
            self.log.warning(f"could not create Group from {group_in}")  # pyright: ignore[reportUnreachable]
            return False

        query = """
            mutation($input: GroupCreateInput!) {
                groupCreate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": group_in}
        result = self.call_GQL(query, variables)["groupCreate"]
        return cast(dict[str, JSON], result)

    def find_group(
        self,
        group_in: int | str | dict[str, str | int],
        fragment: str | None = None,
        create: bool = False,
    ) -> dict[str, JSON] | None:
        # assume input is an ID if int
        if isinstance(group_in, int):
            return self.__generic_find(
                "query FindGroup($id: ID!) { findGroup(id: $id) { ...Group } }", group_in, (r"\.\.\.Group", fragment)
            )

        name: str | None = None
        if isinstance(group_in, dict):
            if group_in.get("stored_id"):
                return self.find_group(int(group_in["stored_id"]))
            if group_in.get("id"):
                return self.find_group(int(group_in["id"]))
            if group_in.get("name"):
                name = cast(str, group_in["name"])

        if isinstance(group_in, str):
            name = group_in

        if not name:
            raise Exception(f"Could not find group with the given information: {group_in}")

        groups = cast(list[dict[str, JSON]], self.find_groups(q=name))
        group_matches = self.__match_alias_item(name, groups)

        if group_matches:
            if len(group_matches) == 1:
                return group_matches[0]
            else:
                self.log.warning(f'Too many matches for Group "{name}"')
                return None

        if create:
            self.log.info(f'Creating missing Group "{name}"')

            # at this point we know that group_in contains at least a key `name` with str value, which is all that is
            # required to createa a new group. Any unrecognized keys will just be ignored
            creation_options = cast(GQLGroupCreateInput, cast(object, group_in))
            return self.create_group(creation_options)

    def update_group(self, group_in: GQLGroupUpdateInput) -> dict[str, JSON]:
        """
        Update the group per the given inputs

        Args:
            group_in (GQLGroupUpdateInput): see type def or playground for details

        Returns:
            A dictionary containing information on the updated group from Stash
        """
        query = """
            mutation GroupUpdate($input:GroupUpdateInput!) {
                groupUpdate(input: $input) {
                    ...Group
                }
            }
        """
        variables: dict[str, object] = {"input": group_in}

        result = self.call_GQL(query, variables)["groupUpdate"]
        return cast(dict[str, JSON], result)

    def destroy_group(self, group_id: int) -> bool:
        """
        Deletes the given group

        Args:
            group_id (int): Group id to delete

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
            mutation DestroyGroup($input:GroupDestroyInput!) {
                groupDestroy(input: $input) {
                    ...Group
                }
            }
        """
        variables: dict[str, object] = {"input": {"id": group_id}}
        result = self.call_GQL(query, variables)["groupDestroy"]
        return cast(bool, result)

    # GROUPS
    def find_groups(
        self,
        f: GQLGroupFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Gets groups matching filter/query

        Args:
            f (GQLGroupFilterType, optional): See type def or playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See type def playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional): override for gqlFragment. Defaults to "...Group". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [tags]) where count is the number of results from the query, useful when paging. Defaults to False.
            callback (_function_, optional): callback function to run results against between page calls. Defaults to None.
                If the given callback has parameters named "count" and/or "page_number", those values will be passed to
                the callback function when it is called.

        Returns:
            _type_: list of tags, or tuple of (count, [tags])
        """
        query = """
            query FindGroups($filter: FindFilterType, $group_filter: GroupFilterType) {
                findGroups(filter: $filter, group_filter: $group_filter) {
                    count
                    groups {
                        ...Group
                    }
                }
            }
        """
        filter = filter or {"per_page": -1}

        if fragment:
            query = re.sub(r"\.\.\.Group", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "group_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables, callback=callback)["findGroups"])
        count = cast(int, result["count"])
        groups = cast(list[dict[str, JSON]], result["groups"])

        if get_count:
            return count, groups
        else:
            return groups

    # MOVIE Shims
    @deprecated("`create_movie()` is depracated use `create_group()`")
    def create_movie(self, *args: Any, **kwargs: Any):
        self.log.warning("`create_movie()` is depracated use `create_group()`")
        return self.create_group(*args, **kwargs)

    @deprecated("`find_movie()` is depracated use `find_group()`")
    def find_movie(self, *args: Any, **kwargs: Any):
        self.log.warning("`find_movie()` is depracated use `find_group()`")
        return self.find_group(*args, **kwargs)

    @deprecated("`update_movie()` is depracated use `update_group()`")
    def update_movie(self, *args: Any, **kwargs: Any):
        self.log.warning("`update_movie()` is depracated use `update_group()`")
        return self.update_group(*args, **kwargs)

    @deprecated("`find_movies()` is depracated use `find_groups()`")
    def find_movies(self, *args: Any, **kwargs: Any):
        self.log.warning("`find_movies()` is depracated use `find_groups()`")
        return self.find_groups(*args, **kwargs)

    # Gallery CRUD
    def create_gallery(self, gallery_create_input: GQLGalleryCreateInput) -> int:
        query = """
            mutation GalleryCreate($input: GalleryCreateInput!) {
                galleryCreate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": gallery_create_input}

        # FIXME: Why do we return an int here when every other create_xxx method returns the created object?
        result = cast(dict[str, object], self.call_GQL(query, variables)["galleryCreate"])
        return cast(int, result["id"])

    def find_gallery(
        self,
        gallery_in: int | str | dict[str, int],
        fragment: str | None = None,
    ) -> dict[str, JSON] | None:
        """
        Gets galleries matching filter/query

        Args:
            f (GQLGalleryFilterType, optional): See type def or playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See type def playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional): override for gqlFragment. Defaults to "...Gallery". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [tags]) where count is the number of results from the query, useful when paging. Defaults to False.
            callback (_function_, optional): callback function to run results against between page calls. Defaults to None.
                If the given callback has parameters named "count" and/or "page_number", those values will be passed to
                the callback function when it is called.

        Returns:
            _type_: list of tags, or tuple of (count, [tags])
        """
        if isinstance(gallery_in, int):
            query = """
                query FindGallery($id: ID!) {
                    findGallery(id: $id) {
                        ...Gallery
                    }
                }
            """
            return self.__generic_find(
                query,
                gallery_in,
                (r"\.\.\.Gallery", fragment),
            )

        if isinstance(gallery_in, dict):
            if gallery_in.get("id"):
                return self.find_gallery(int(gallery_in["id"]), fragment)

        if isinstance(gallery_in, str):
            try:
                return self.find_gallery(int(gallery_in), fragment)
            except:
                self.log.warning(f"could not parse {gallery_in} into an integer Gallery ID")

    def update_gallery(self, gallery_data: GQLGalleryUpdateInput) -> int:
        """
        Update the gallery per the given inputs

        Args:
            group_in (GQLGalleryUpdateInput): see type def or playground for details

        Returns:
            The integer ID of the updated gallery
        """
        query = """
            mutation GalleryUpdate($input:GalleryUpdateInput!) {
                galleryUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": gallery_data}

        # FIXME: why are we returning an int here when all the other update_xxx methods return the updated object?
        result = cast(dict[str, JSON], self.call_GQL(query, variables)["galleryUpdate"])
        return cast(int, result["id"])

    def destroy_gallery(
        self,
        gallery_ids: int | list[int],
        delete_file: bool = False,
        delete_generated: bool = True,
    ) -> dict[str, JSON]:
        """
        Deletes the given galler(y/ies)

        Args:
            gallery_in (int, list[int]): Gallery id or list of ids to delete

        Raises:
            Exception if `gallery_ida` is not an int or list of ints

        Returns:
            True if the operation was successful, False otherwise
        """
        if isinstance(gallery_ids, int):
            gallery_ids = [gallery_ids]

        if not isinstance(gallery_ids, list):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise Exception("destroy_gallery only accepts an int or list of ints")  # pyright: ignore[reportUnreachable]

        query = """
            mutation galleryDestroy($input:GalleryDestroyInput!) {
                galleryDestroy(input: $input)
            }
        """
        variables: dict[str, object] = {
            "input": {"delete_file": delete_file, "delete_generated": delete_generated, "ids": gallery_ids}
        }
        result = self.call_GQL(query, variables)["galleryDestroy"]
        return cast(dict[str, JSON], result)

    # Gallery Images
    def find_gallery_images(self, gallery_id: int, fragment: str | None = None) -> list[dict[str, JSON]]:
        """
        Gets gallery images matching gallery filter/query

        Args:
            gallery_id (int): integer gallery ID from which to find images
            fragment (str, optional): override for gqlFragment. Defaults to None

        Returns:
            _type_: list of tags, or tuple of (count, [tags])
        """
        # TODO: finish updating this
        return cast(
            list[dict[str, JSON]],
            self.find_images(f={"galleries": {"value": [gallery_id], "modifier": "INCLUDES_ALL"}}, fragment=fragment),
        )

    def update_gallery_images(self, gallery_images_input):
        # TODO: finish updating this
        mode = gallery_images_input.get("mode")
        if not mode:
            raise Exception("update_gallery_images() expects mode argument")
        mode = mode.strip().upper()
        if mode == "ADD":
            return self.add_gallery_images(gallery_images_input["id"], gallery_images_input["image_ids"])
        if mode == "REMOVE":
            return self.remove_gallery_images(gallery_images_input["id"], gallery_images_input["image_ids"])
        if mode == "SET":
            gallery_images = self.find_images(
                {"galleries": {"value": gallery_images_input["id"], "modifier": "INCLUDES_ALL"}}, fragment="id"
            )
            # remove all existing images
            self.remove_gallery_images(gallery_images_input["id"], [f["id"] for f in gallery_images])
            # set gallery images to input or return if no value provided
            if not gallery_images_input.get("image_ids"):
                return
            return self.add_gallery_images(gallery_images_input["id"], gallery_images_input["image_ids"])

    def remove_gallery_images(self, gallery_id: int, image_ids: list[int]) -> bool:
        """
        Remove the given images from the given gallery

        Args:
            gallery_id (int): integer ID of the gallery from which to remove images
            image_ids (list[int]): list of integer image IDs to remove from the gallery

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
            mutation RemoveGalleryImages($gallery_id: ID!, $image_ids: [ID!]!) {
                removeGalleryImages(input: {
                    gallery_id: $gallery_id,
                    image_ids: $image_ids
                })
            }
        """
        variables: dict[str, object] = {"gallery_id": gallery_id, "image_ids": image_ids}
        result = self.call_GQL(query, variables)["removeGalleryImages"]
        return cast(bool, result)

    def add_gallery_images(self, gallery_id: int, image_ids: list[int]) -> bool:
        """
        Add the given images to the given gallery

        Args:
            gallery_id (int): integer ID of the gallery into which to the images will be added
            image_ids (list[int]): list of integer image IDs to add to the gallery

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
            mutation AddGalleryImages($gallery_id: ID!, $image_ids: [ID!]!) {
                addGalleryImages(input: { gallery_id: $gallery_id, image_ids: $image_ids })
            }
        """
        variables: dict[str, object] = {"gallery_id": gallery_id, "image_ids": image_ids}
        result = self.call_GQL(query, variables)["addGalleryImages"]
        return cast(bool, result)

    # Gallery Chapters
    def create_gallery_chapter(self, chapter_data: GQLGalleryChapterCreateInput) -> int:
        """
        Create a gallery chapter from the given chapter data

        Args:
            chapter_data (GQLGalleryChapterCreateInput): see type def or playground for details

        Returns:
            The integer ID of the created gallery chapter
        """
        query = """
            mutation GalleryChapterCreate($input:GalleryChapterCreateInput!) {
                galleryChapterCreate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": chapter_data}
        result = cast(dict[str, JSON], self.call_GQL(query, variables)["galleryChapterCreate"])
        # FIXME: why are we returning an int here when all the other create_xxx methods return the created object?
        return cast(int, result["id"])

    def update_gallery_chapter(self, chapter_data: GQLGalleryChapterUpdateInput) -> int:
        """
        Update a gallery chapter with the given chapter data

        Args:
            chapter_data (GQLGalleryChapterUpdateInput): see type def or playground for details

        Returns:
            The integer ID of the updated gallery chapter
        """
        query = """
            mutation GalleryChapterUpdate($input:GalleryChapterUpdateInput!) {
                galleryChapterUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": chapter_data}
        result = cast(dict[str, JSON], self.call_GQL(query, variables)["galleryChapterUpdate"])
        # FIXME: why are we returning an int here when all the other update_xxx methods return the updated object?
        return cast(int, result["id"])

    def destroy_gallery_chapter(self, chapter_id: int) -> bool:
        """
        Deletes the gallery chapter with the given integer ID

        Args:
            chapter_id (int): The gallery chapter ID to delete

        Returns:
            True if the oepration was successful, False otherwise
        """
        query = """
            mutation GalleryChapterDestroy($chapter_id:ID!) {
                galleryChapterDestroy(id: $chapter_id) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"chapter_id": chapter_id}
        result = self.call_GQL(query, variables)["galleryChapterDestroy"]
        return cast(bool, result)

    # BULK Gallery
    def find_galleries(
        self,
        f: GQLGalleryFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Gets galleries matching filter/query

        Args:
            f (GQLGalleryFilterType, optional): See type def or playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See type def playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional): override for gqlFragment. Defaults to "...Gallery". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [tags]) where count is the number of results from the query, useful when paging. Defaults to False.
            callback (_function_, optional): callback function to run results against between page calls. Defaults to None.
                If the given callback has parameters named "count" and/or "page_number", those values will be passed to
                the callback function when it is called.

        Returns:
            _type_: list of galleries, or tuple of (count, [galleries])
        """
        f = f or {}
        filter = filter or {"per_page": -1}
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
            query = re.sub(r"\.\.\.Gallery", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "gallery_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables, callback=callback)["findGalleries"])
        count = cast(int, result["count"])
        galleries = cast(list[dict[str, JSON]], result["galleries"])
        if get_count:
            return count, galleries
        else:
            return galleries

    def update_galleries(self, galleries_input: GQLBulkGalleryUpdateInput) -> list[dict[str, JSON]]:
        """
        Bulk update galleries with the given input

        Args:
            galleries_input (GQLBulkGalleryUpdateInput): see type def or playground for details

        Returns:
            List of dicts containing gallery information from Stash for the updated galleries
        """
        query = """
            mutation BulkGalleryUpdate($input:BulkGalleryUpdateInput!) {
                bulkGalleryUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": galleries_input}

        result = self.call_GQL(query, variables)["bulkGalleryUpdate"]
        return cast(list[dict[str, JSON]], result)

    # Image CRUD
    def create_image(self, path: str | Path) -> int:
        """
        Trigger a scan of the given path, which will create the image in Stash

        Args:
            path (str, Path): path to scan

        Returns:
            The integer ID of the triggered scan job
        """
        return self.metadata_scan([path])

    def find_image(
        self,
        image_in: int | str | dict[str, str | int],
        fragment: str | None = None,
    ) -> dict[str, JSON] | None:
        """
        Gets image matching filter/query

        Args:
            image_in (int, str, dict): image id or dict containing either `stored_id` or `id` keys
            fragment (str, optional): override for gqlFragment. Defaults to "...Gallery". example override 'fragment="id name"'

        Returns:
            A dictionary containing information on the image from Stash if found, otherwise None
        """
        if isinstance(image_in, int):
            query = """
                query FindImage($id: ID!) {
                    findImage(id: $id) {
                        ...Image
                    }
                }
            """
            return self.__generic_find(query, image_in, (r"\.\.\.Image", fragment))

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

    def update_image(self, update_input: GQLImageUpdateInput) -> dict[str, JSON]:
        """
        Update the image per the given inputs

        Args:
            update_input (GQLImageUpdateInput): see type def or playground for details

        Returns:
            A dictionary containing information on the updated image from Stash
        """
        query = """
            mutation ImageUpdate($input:ImageUpdateInput!) {
                imageUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": update_input}

        result = self.call_GQL(query, variables)["imageUpdate"]
        return cast(dict[str, JSON], result)

    def destroy_image(self, image_id: int, delete_file: bool = False) -> bool:
        """
        Deletes an image from stash

        Args:
            image_id (int): integer image ID from stash
            delete_file (bool): whether or not to delete the file while deleting the image in Stash

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
        mutation ImageDestroy($input:ImageDestroyInput!) {
            imageDestroy(input: $input)
        }
        """
        variables: dict[str, object] = {"input": {"delete_file": delete_file, "delete_generated": True, "id": image_id}}

        result = self.call_GQL(query, variables)["imageDestroy"]
        return cast(bool, result)

    # BULK Images
    def find_images(
        self,
        f: GQLImageFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Gets images matching filter/query

        Args:
            f (GQLImageFilterType, optional): See playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional): override for gqlFragment. Defaults to "...Image". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [image]) where count is the number of results from the query, useful when paging. Defaults to False.
            callback (_function_, optional): callback function to run results against between page calls. Defaults to None.
                If the given callback has parameters named "count" and/or "page_number", those values will be passed to
                the callback function when it is called.

        Returns:
            _type_: list of images, or tuple of (count, [image])
        """
        f = f or {}
        filter = filter or {"per_page": -1}
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
            query = re.sub(r"\.\.\.Image", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "image_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables, callback=callback)["findImages"])
        count = cast(int, result["count"])
        images = cast(list[dict[str, JSON]], result["images"])
        if get_count:
            return count, images
        else:
            return images

    def update_images(self, updates_input: GQLBulkImageUpdateInput) -> dict[str, JSON]:
        """
        Update multiple existing images

        Args:
            updates_input (GQLBulkImageUpdateInput):  see type def or playground for details

        Returns:
            list of stash image objects
        """
        query = """
            mutation BulkImageUpdate($input:BulkImageUpdateInput!) {
                bulkImageUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": updates_input}

        result = self.call_GQL(query, variables)["bulkImageUpdate"]
        return cast(dict[str, JSON], result)

    def destroy_images(self, image_ids: list[int], delete_file: bool = False) -> bool:
        """
        Deletes the given images

        Args:
            group_id (list[int)]: List of integer image IDs to delete
            delete_file (bool): whether or not to delete the files while deleting the images in Stash

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
            mutation ImagesDestroy($input:ImagesDestroyInput!) {
                imagesDestroy(input: $input)
            }
        """
        variables: dict[str, object] = {
            "input": {"delete_file": delete_file, "delete_generated": True, "ids": image_ids}
        }

        result = self.call_GQL(query, variables)["imagesDestroy"]
        return cast(bool, result)

    # Scene CRUD
    def create_scene(self, scene_create_input: GQLSceneCreateInput) -> dict[str, JSON]:
        """
        Creates a scene with the given details

        Args:
            scene_create_input (GQLSceneCreateInput): Parameters which will be used to create the scene

        Returns:
            The dictionary representing the scene as created by Stash
        """
        query = """
        mutation SceneCrate($input: SceneCreateInput!) {
            sceneCreate(input: $input) {
                id
            }
        }
        """

        variables: dict[str, object] = {"input": scene_create_input}

        result = self.call_GQL(query, variables)["sceneCreate"]
        return cast(dict[str, JSON], result)

    def find_scene(self, id: int, fragment: str | None = None) -> dict[str, JSON] | None:
        """
        Looks for a scene matching the given integer ID

        Args:
            id (int): Tag ID, name, or dict to find.
            fragment (str, optional): override for gqlFragment. Defaults to "...Scene". example override 'fragment="id name"'

        Returns:
            The dictionary representing the scene from Stash
        """
        query = """
            query FindScene($scene_id: ID) {
                findScene(id: $scene_id) {
                    ...Scene
                }
            }
        """
        if fragment:
            query = re.sub(r"\.\.\.Scene", fragment, query)

        variables: dict[str, object] = {"scene_id": id}

        result = self.call_GQL(query, variables)["findScene"]
        return cast(dict[str, JSON] | None, result)

    def find_scene_by_hash(self, hash_input: GQLSceneHashInput, fragment: str | None = None) -> dict[str, JSON]:
        """
        Looks for a scene matching the given hash

        Args:
            hash_input (GQLSceneHashInput):  see type def or playground for details
            fragment (str, optional): override for gqlFragment. Defaults to "...Scene". example override 'fragment="id name"'

        Returns:
            The dictionary representing the scene from Stash
        """
        query = """
            query FindSceneByHash($hash_input: SceneHashInput!) {
                findSceneByHash(input: $hash_input) {
                    ...Scene
                }
            }
        """
        if fragment:
            query = re.sub(r"\.\.\.Scene", fragment, query)

        variables: dict[str, object] = {"hash_input": hash_input}

        result = self.call_GQL(query, variables)["findSceneByHash"]
        return cast(dict[str, JSON], result)

    def find_scenes_by_hash(
        self,
        hash_type: str,
        value: str | None = None,
        fragment: str | None = None,
        ids_only: bool = False,
    ) -> list[dict[str, JSON]]:
        """
        Returns a list of Scenes that have a file matching the given hash

        Args:
                hash_type (str): type of hash (md5, oshash, phash, ...)
                value (str, optional): hash value, if not provided returns all scenes with provided hash_type
                fragment (str, optional): desired GQL Scene fragment to be returned for each scene. Defaults to None.

        Returns:
                list: list of scene objects matching given hash
        """

        query = """
            SELECT 
                scene_id
            FROM 
                files_fingerprints
            INNER JOIN scenes_files USING(file_id)
            WHERE type = ?
        """

        if value != None:
            if hash_type == "phash":
                query += " AND printf('%x', fingerprint) = ?;"
            else:
                query += " AND fingerprint = ?;"

        scene_ids = self.sql_query(query, [hash_type, value]).get("rows")
        if len(scene_ids) > 0:
            scene_ids = scene_ids[0]

        if ids_only:
            return scene_ids

        found = [self.find_scene(sid, fragment=fragment) for sid in scene_ids]
        return list(filter(None, found))

    def update_scene(self, update_input: GQLSceneUpdateInput, create: bool = False) -> int:
        """
        Update the scene per the given inputs

        Args:
            update_input (GQLSceneUpdateInput): see type def or playground for details

        Returns:
            The integer ID of the updated scene
        """
        query = """
            mutation sceneUpdate($input:SceneUpdateInput!) {
                sceneUpdate(input: $input) {
                    id
                }
            }
        """
        if tags := update_input.get("tags"):
            self.log.debug("sceneUpdate expects 'tag_ids' not 'tags', automatically mapping...")
            update_input["tag_ids"] = self.map_tag_ids(tags, create=create)
            del update_input[
                "tags"
            ]  # pyright: ignore[reportGeneralTypeIssues] we know this key shouldn't exist, that's why we're doing this

        if performers := update_input.get("performers"):
            self.log.debug("sceneUpdate expects 'performer_ids' not 'performers', automatically mapping...")
            update_input["performer_ids"] = self.map_performer_ids(performers, create=create)
            del update_input[
                "performers"
            ]  # pyright: ignore[reportGeneralTypeIssues] we know this key shouldn't exist, that's why we're doing this

        variables: dict[str, object] = {"input": update_input}

        # FIXME: why are we returning an int here when all the other update_xxx methods return the updated object?
        result = cast(dict[str, JSON], self.call_GQL(query, variables)["sceneUpdate"])
        return cast(int, result["id"])

    def destroy_scene(self, scene_id: int, delete_file: bool = False) -> bool:
        """
        Deletes a scene from stash

        Args:
            scene_id (int): integer scene ID from stash to delete
            delete_file (bool): whether or not to delete the files while deleting the scene in Stash

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
            mutation SceneDestroy($input:SceneDestroyInput!) {
                sceneDestroy(input: $input)
            }
        """
        variables: dict[str, object] = {"input": {"delete_file": delete_file, "delete_generated": True, "id": scene_id}}

        result = self.call_GQL(query, variables)["sceneDestroy"]
        return cast(bool, result)

    # BULK Scenes
    def create_scenes(self, scene_create_inputs: list[GQLSceneCreateInput]) -> list[dict[str, JSON]]:
        """
        Creates scenes with the given details

        Args:
            scene_create_inputs (list[GQLSceneCreateInput]): Parameters which will be used to create the scenes

        Returns:
            A list of dictionaries representing the scenes as created by Stash
        """
        responses: list[dict[str, JSON]] = []
        for input in scene_create_inputs:
            responses.append(self.create_scene(input))

        return responses

    def find_scenes(
        self,
        f: GQLSceneFilterType | None = None,
        filter: GQLFindFilterType | None = None,
        q: str = "",
        fragment: str | None = None,
        get_count: bool = False,
        callback: Callable[..., CallbackReturns] | None = None,
    ) -> tuple[int, list[dict[str, JSON]]] | list[dict[str, JSON]]:
        """
        Gets tags matching filter/query

        Args:
            f (GQLSceneFilterType, optional): See playground for details. Defaults to {}.
            filter (GQLFindFilterType, optional): See playground for details. Defaults to {"per_page": -1}.
            q (str, optional): query string, same search bar in stash. Defaults to "".
            fragment (str, optional): override for gqlFragment. Defaults to "...Scene". example override 'fragment="id name"'
            get_count (bool, optional): returns tuple (count, [scene]) where count is the number of results from the query, useful when paging. Defaults to False.
            callback (_function_, optional): callback function to run results against between page calls. Defaults to None.
                If the given callback has parameters named "count" and/or "page_number", those values will be passed to
                the callback function when it is called.

        Returns:
            _type_: list of scenes, or tuple of (count, [scene])
        """
        f = f or {}
        filter = filter or {"per_page": -1}

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
            query = re.sub(r"\.\.\.Scene", fragment, query)

        filter["q"] = q
        variables: dict[str, object] = {"filter": filter, "scene_filter": f}

        result = cast(dict[str, JSON], self.call_GQL(query, variables, callback=callback)["findScenes"])
        count = cast(int, result["count"])
        scenes = cast(list[dict[str, JSON]], result["scenes"])
        if get_count:
            return count, scenes
        else:
            return scenes

    def update_scenes(self, updates_input: GQLBulkSceneUpdateInput) -> dict[str, JSON]:
        """
        Update multiple existing scenes

        Args:
            updates_input (GQLBulkSceneUpdateInput):  see type def or playground for details

        Returns:
            list of stash scene objects
        """
        query = """
            mutation BulkSceneUpdate($input:BulkSceneUpdateInput!) {
                bulkSceneUpdate(input: $input) {
                    id
                }
            }
        """
        variables: dict[str, object] = {"input": updates_input}

        result = self.call_GQL(query, variables)["bulkSceneUpdate"]
        return cast(dict[str, JSON], result)

    def destroy_scenes(self, scene_ids: list[int], delete_file: bool = False) -> bool:
        """
        Deletes scenes from stash

        Args:
            scene_ids (list[int]): scene IDs from stash

        Returns:
            True if the operation was successful, False otherwise
        """
        query = """
            mutation ScenesDestroy($input:ScenesDestroyInput!) {
                scenesDestroy(input: $input)
            }
        """
        variables: dict[str, object] = {
            "input": {"delete_file": delete_file, "delete_generated": True, "ids": scene_ids}
        }

        result = self.call_GQL(query, variables)["scenesDestroy"]
        return cast(bool, result)

    def merge_scenes(
        self,
        source: int | str | list[int],
        destination: int,
        values: GQLSceneUpdateInput | None = None,
        play_history: bool = False,
        o_history: bool = False,
    ) -> dict[str, JSON]:
        """
        Merges the scene with the given id into the scene with given destination id

        Args:
            source (int | str): Scene ID to be merged
            destination (int): ID of scene in which to merge the source
            play_history (bool): whether or not to merge the play-history from the source into the destination. Default: False
            o_history (bool): whether or not to merge the o-history from the source into the destination. Default: False
            values (GQLSceneUpdateInput): the values from the source scene to merge into the destination. By default,
                nothing will be merged

        Returns:
            A dictionary containing information on the merged scene from Stash
        """
        if isinstance(source, str):
            # FIXME: we should probably handle the exception here like we do elsewhere
            source = int(source)

        if isinstance(destination, str):
            # FIXME: we should probably handle the exception here like we do elsewhere
            destination = int(destination)

        if isinstance(source, int):
            source = [source]

        if not isinstance(source, list):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise Exception(
                f"merge_scenes() source attribute must be resolveable into a list of ints, got: {source}"
            )  # pyright: ignore[reportUnreachable]

        if not isinstance(destination, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise Exception(
                f"merge_scenes() destination attribute must be resolveable into an int, got: {destination}"
            )  # pyright: ignore[reportUnreachable]

        query = """
            mutation SceneMerge($input: SceneMergeInput!) {
                sceneMerge(input: $input) {
                    id
                }
            }
        """

        if values and "id" not in values:
            values["id"] = (
                destination  # pyright: ignore[reportUnreachable] we know the "id" key should exist but we need to make sure
            )
        elif not values:
            values = {"id": destination}

        variables: dict[str, object] = {
            "input": {
                "source": source,
                "destination": destination,
                "play_history": play_history,
                "o_history": o_history,
                "values": values,
            }
        }

        result = self.call_GQL(query, variables)["sceneMerge"]
        return cast(dict[str, JSON], result)

    # Markers CRUD
    # TODO: remove deprecated function
    def get_scene_markers(self, scene_id, fragment=None) -> list:
        """returns a list of markers for a particular Scene given the scene_id

        Args:
                scene_id: the stash ID of the scene to get markers for

        Returns:
                list: list of marker objects from stash
        """
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
            query = re.sub(r"\.\.\.SceneMarker", fragment, query)

        variables = {"scene_id": scene_id}
        return self.call_GQL(query, variables)["findScene"]["scene_markers"]

    def find_scene_markers(self, scene_marker_filter, filter: dict = {"per_page": -1}, fragment=None) -> list:
        """Finds markers matching a SceneMarkerFilterType dict, as get_scene_markers() only takes a scene_id.
        This is useful for finding a list of markers that use a specific tag.

        Args:
                 scene_marker_filter (SceneMarkerFilterType, optional)
                        See https://github.com/stashapp/stash/blob/develop/pkg/models/scene_marker.go for details on SceneMarkerFilterType

        Returns:
                dict: containing markers matching the filter
        """

        # Catch legacy find_scene_markers() calls and redirect to get_scene_markers().
        if not isinstance(scene_marker_filter, dict):
            self.log.warning("find_scene_markers() no longer accepts scene_id, use get_scene_markers() instead")
            return self.get_scene_markers(scene_marker_filter)

        query = """
            query findSceneMarkers($scene_marker_filter: SceneMarkerFilterType, $filter: FindFilterType) {
                findSceneMarkers(scene_marker_filter: $scene_marker_filter, filter: $filter) {
                    scene_markers {
                        ...SceneMarker
                    }
                }
            }
        """
        if fragment:
            query = re.sub(r"\.\.\.SceneMarker", fragment, query)

        variables = {"scene_marker_filter": scene_marker_filter, "filter": filter}
        return self.call_GQL(query, variables)["findSceneMarkers"]["scene_markers"]

    def create_scene_marker(self, marker_create_input: dict, fragment=None):
        query = """
            mutation SceneMarkerCreate($marker_input: SceneMarkerCreateInput!) {
                sceneMarkerCreate(input: $marker_input) {
                    ...SceneMarker
                }
            }
        """
        if fragment:
            query = re.sub(r"\.\.\.SceneMarker", fragment, query)

        variables = {"marker_input": marker_create_input}
        return self.call_GQL(query, variables)["sceneMarkerCreate"]

    def update_scene_marker(self, scene_marker_update: dict):
        query = """
            mutation SceneMarkerUpdate($input: SceneMarkerUpdateInput!) {
                sceneMarkerUpdate(input: $input) {
                    id
                }
            }
        """
        self.call_GQL(query, {"input": scene_marker_update})

    def destroy_scene_marker(self, marker_id: int):
        query = """
            mutation DestroySceneMarkers($marker_id: ID!) {
                sceneMarkerDestroy(id: $marker_id)
            }
        """
        self.call_GQL(query, {"marker_id": marker_id})

    # BULK Markers
    def destroy_scene_markers(self, scene_id: int):
        scene_markers = self.get_scene_markers(scene_id, fragment="id")
        for marker in scene_markers:
            self.destroy_scene_marker(marker["id"])

    def merge_scene_markers(self, target_scene_id: int, source_scene_ids: list):
        existing_marker_timestamps = [marker["seconds"] for marker in self.get_scene_markers(target_scene_id)]

        markers_to_merge = []
        for source_scene_id in source_scene_ids:
            markers_to_merge.extend(self.get_scene_markers(source_scene_id))

        created_markers = []
        for marker in markers_to_merge:
            if marker["seconds"] in existing_marker_timestamps:
                # skip existing marker
                # TODO merge missing data between markers
                continue
            marker_id = self.create_scene_marker(
                {
                    "title": marker["title"],
                    "seconds": marker["seconds"],
                    "scene_id": target_scene_id,
                    "primary_tag_id": marker["primary_tag"]["id"],
                    "tag_ids": [t["id"] for t in marker["tags"]],
                }
            )
            created_markers.append(marker_id)
        return created_markers

    # Scene Utils
    def destroy_scene_stash_id(self, stash_id):
        scenes = self.find_scenes(
            f={"stash_id_endpoint": {"value": stash_id, "modifier": "EQUALS"}},
            fragment="id stash_ids {endpoint stash_id}",
        )

        for scene in scenes:
            scene["stash_ids"] = [sid for sid in scene["stash_ids"] if sid["stash_id"] != stash_id]
            self.update_scene(scene)

    def find_duplicate_scenes(self, distance: PhashDistance = PhashDistance.EXACT, fragment="id"):
        query = """
            query FindDuplicateScenes($distance: Int) {
                findDuplicateScenes(distance: $distance) {
                    ...SceneSlim
                }
            }
        """
        query = re.sub(r"\.\.\.SceneSlim", fragment, query)

        variables = {"distance": distance}
        result = self.call_GQL(query, variables)
        return result["findDuplicateScenes"]

    # Scraper Operations
    def reload_scrapers(self):
        query = """
            mutation ReloadScrapers {
                reloadScrapers
            }
        """

        result = self.call_GQL(query)
        return result["reloadScrapers"]

    def list_scrapers(self, types: list[StashItem]):
        query = """
        query ListScrapers ($types: [ScrapeContentType!]!) {
            listScrapers(types: $types) {
              id
              name
              performer { supported_scrapes }
              scene { supported_scrapes }
              gallery { supported_scrapes }
              movie { supported_scrapes }
              image { supported_scrapes }
            }
          }
        """
        result = self.call_GQL(query, {"types": [t.value for t in types]})
        return result["listScrapers"]

    def list_performer_scrapers(self):
        return [
            {k: scraper[k] for k in ["id", "name", "performer"]}
            for scraper in self.list_scrapers([StashItem.PERFORMER])
        ]

    def list_scene_scrapers(self):
        return [{k: scraper[k] for k in ["id", "name", "scene"]} for scraper in self.list_scrapers([StashItem.SCENE])]

    def list_gallery_scrapers(self):
        return [
            {k: scraper[k] for k in ["id", "name", "gallery"]} for scraper in self.list_scrapers([StashItem.GALLERY])
        ]

    def list_movie_scrapers(self):
        return [{k: scraper[k] for k in ["id", "name", "movie"]} for scraper in self.list_scrapers([StashItem.MOVIE])]

    def list_image_scrapers(self):
        return [{k: scraper[k] for k in ["id", "name", "image"]} for scraper in self.list_scrapers([StashItem.IMAGE])]

    # Fragment Scrape
    def scrape_scenes(self, source, input, fragment=None):
        query = """query ScrapeMultiScenes($source: ScraperSourceInput!, $input: ScrapeMultiScenesInput!) {
        scrapeMultiScenes(source: $source, input: $input) {
            ...ScrapedScene
        }
        }"""
        if fragment:
            query = re.sub(r"\.\.\.ScrapedScene", fragment, query)
        return self.call_GQL(query, {"source": source, "input": input})["scrapeMultiScenes"]

    def scrape_scene(self, source, input):
        if isinstance(source, str):
            source = {"scraper_id": source}
        if isinstance(input, (str, int)):
            input = {"scene_id": input}

        if not isinstance(source, dict):
            self.log.warning(
                f'Unexpected Object passed to source {type(source)}{source}\n, expecting "ScraperSourceInput" or string of scraper_id'
            )
            return None
        if not isinstance(input, dict):
            self.log.warning(
                f'Unexpected Object passed to input {type(input)}{input}\n, expecting "ScrapeSingleSceneInput" or string of scene_id'
            )
            return None

        query = """query ScrapeSingleScene($source: ScraperSourceInput!, $input: ScrapeSingleSceneInput!) {
            scrapeSingleScene(source: $source, input: $input) {
              ...ScrapedScene
            }
          }
        """
        scraped_scene_list = self.call_GQL(query, {"source": source, "input": input})["scrapeSingleScene"]
        if len(scraped_scene_list) == 0:
            return None
        else:
            return scraped_scene_list

    def scrape_gallery(self, source, input):
        if isinstance(source, str):
            source = {"scraper_id": source}
        if isinstance(input, (str, int)):
            input = {"gallery_id": input}

        if not isinstance(source, dict):
            self.log.warning(
                f'Unexpected Object passed to source {type(source)}{source}\n, expecting "ScraperSourceInput" or string of scraper_id'
            )
            return None
        if not isinstance(input, dict):
            self.log.warning(
                f'Unexpected Object passed to input {type(input)}{input}\n, expecting "ScrapeSingleGalleryInput" or string of gallery_id'
            )
            return None

        query = """query ScrapeSingleGallery($source: ScraperSourceInput!, $input: ScrapeSingleGalleryInput!) {
            scrapeSingleGallery(source: $source, input: $input) {
              ...ScrapedGallery
            }
          }
        """
        scraped_gallery_list = self.call_GQL(query, {"source": source, "input": input})["scrapeSingleGallery"]
        if len(scraped_gallery_list) == 0:
            return None
        else:
            return scraped_gallery_list

    def scrape_performer(self, source, input):
        if isinstance(source, str):
            source = {"scraper_id": source}
        if isinstance(input, (str, int)):
            input = {"performer_id": input}

        if not isinstance(source, dict):
            self.log.warning(
                f'Unexpected Object passed to source {type(source)}{source}\n, expecting "ScraperSourceInput" or string of scraper_id'
            )
            return None
        if not isinstance(input, dict):
            self.log.warning(
                f'Unexpected Object passed to input {type(input)}{input}\n, expecting "ScrapeSinglePerformerInput" or string of performer_id'
            )
            return None

        query = """query ScrapeSinglePerformer($source: ScraperSourceInput!, $input: ScrapeSinglePerformerInput!) {
            scrapeSinglePerformer(source: $source, input: $input) {
              ...ScrapedPerformer
            }
          }
        """
        scraped_performer_list = self.call_GQL(query, {"source": source, "input": input})["scrapeSinglePerformer"]
        if len(scraped_performer_list) == 0:
            return None
        else:
            return scraped_performer_list

    def scrape_image(self, source, input):
        if isinstance(source, str):
            source = {"scraper_id": source}
        if isinstance(input, (str, int)):
            input = {"image_id": input}

        if not isinstance(source, dict):
            self.log.warning(
                f'Unexpected Object passed to source {type(source)}{source}\n, expecting "ScraperSourceInput" or string of scraper_id'
            )
            return None
        if not isinstance(input, dict):
            self.log.warning(
                f'Unexpected Object passed to input {type(input)}{input}\n, expecting "ScrapeSingleImageInput" or string of image_id'
            )
            return None

        query = """query ScrapeSingleImage($source: ScraperSourceInput!, $input: ScrapeSingleImageInput!) {
            scrapeSingleImage(source: $source, input: $input) {
              ...ScrapedImage
            }
          }
        """

        scraped_image_list = self.call_GQL(query, {"source": source, "input": input})["scrapeSingleImage"]
        if len(scraped_image_list) == 0:
            return None
        else:
            return scraped_image_list

    # URL Scrape
    def scrape_scene_url(self, url):
        query = "query($url: String!) { scrapeSceneURL(url: $url) { ...ScrapedScene } }"
        return self.call_GQL(query, {"url": url})["scrapeSceneURL"]

    def scrape_group_url(self, url):
        query = "query($url: String!) { scrapeGroupURL(url: $url) { ...ScrapedGroup } }"
        return self.call_GQL(query, {"url": url})["scrapeGroupURL"]

    def scrape_movie_url(self, url):
        self.log.warning("scrape_movie_url() is depracated use scrape_group_url()")
        query = "query($url: String!) { scrapeMovieURL(url: $url) { ...ScrapedMovie } }"
        return self.call_GQL(query, {"url": url})["scrapeMovieURL"]

    def scrape_gallery_url(self, url):
        query = "query($url: String!) { scrapeGalleryURL(url: $url) { ...ScrapedGallery } }"
        return self.call_GQL(query, {"url": url})["scrapeGalleryURL"]

    def scrape_performer_url(self, url):
        query = "query($url: String!) { scrapePerformerURL(url: $url) { ...ScrapedPerformer } }"
        return self.call_GQL(query, {"url": url})["scrapePerformerURL"]

    def scrape_image_url(self, url):
        query = "query($url: String!) { scrapeImageURL(url: $url) { ...ScrapedImage } }"
        return self.call_GQL(query, {"url": url})["scrapeImageURL"]

    # Identify
    def get_identify_config(self):
        query = """
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
        result = self.call_GQL(query)
        return result["configuration"]["defaults"]["identify"]["options"]

    def get_identify_source_config(self, source_identifier):
        query = """
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
        configs = self.call_GQL(query)["configuration"]["defaults"]["identify"]["sources"]
        for c in configs:
            if c["source"]["stash_box_endpoint"] == source_identifier:
                return c["options"]
            if c["source"]["scraper_id"] == source_identifier:
                return c["options"]
        return None

    # Stash Box
    def get_stashbox_connection(self, sbox_endpoint):
        for sbox_idx, sbox_cfg in enumerate(self.get_stashbox_connections()):
            if sbox_endpoint in sbox_cfg["endpoint"]:
                sbox_cfg["Logger"] = self.log
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
        result = self.call_GQL(query)
        return result["configuration"]["general"]["stashBoxes"]

    def stashbox_scene_scraper(self, scene_ids, stashbox_index: int = 0):
        query = """
            query QueryStashBoxScene($input: StashBoxSceneQueryInput!) {
                queryStashBoxScene(input: $input) {
                    ...ScrapedScene
                }
            }
        """
        variables = {"input": {"scene_ids": scene_ids, "stash_box_index": stashbox_index}}

        result = self.call_GQL(query, variables)

        return result["queryStashBoxScene"]

    def stashbox_submit_scene_fingerprints(self, scene_ids, stashbox_index: int = 0):
        query = """
            mutation SubmitStashBoxFingerprints($input: StashBoxFingerprintSubmissionInput!) {
                submitStashBoxFingerprints(input: $input)
            }
        """
        variables = {"input": {"scene_ids": scene_ids, "stash_box_index": stashbox_index}}

        result = self.call_GQL(query, variables)
        return result["submitStashBoxFingerprints"]

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
                    "source": {"stash_box_endpoint": stashbox_endpoint},
                }
            ],
        }
        return self.call_GQL(query, variables)

    def submit_scene_draft(self, scene_id, sbox_index=0):
        query = """
            mutation submitScenesToStashbox($input: StashBoxDraftSubmissionInput!) {
                  submitStashBoxSceneDraft(input: $input)
            }
        """
        variables = {"input": {"id": scene_id, "stash_box_index": sbox_index}}
        result = self.call_GQL(query, variables)
        return result["submitStashBoxSceneDraft"]
