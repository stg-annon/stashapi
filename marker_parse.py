from . import log
from .stashapp import StashInterface

SCENE_MARKER_FRAGMENT = """
title
scene { id, title }
seconds
primary_tag { id, name }
tags { id, name }
"""

class Marker:
    def __init__(self, kwargs):
        self.__dict__.update(kwargs)
    def __eq__(self, other) -> bool:
        return self.seconds == other.seconds
    def __nq__(self, other) -> bool:
        return not self.__eq__(other)
    def __lt__(self, other) -> bool:
        return  self.seconds < other.seconds

    def within_distance(self, other, seconds_distance:int=15):
        if not isinstance(other, Marker):
            raise ValueError(f"Marker.within_distance() must compare to <Marker> type not {type(other)}")
        return self.primary_tag["id"] == other.primary_tag["id"] and abs(self.seconds - other.seconds) < seconds_distance

    @classmethod
    def from_gql(cls, fragment):
        return cls({
            "scene_id":fragment["scene"]["id"],
            "title": fragment["title"],
            "seconds":fragment["seconds"],
            "tag_ids":fragment["tags"],
            "primary_tag":fragment["primary_tag"]
        })

    @classmethod
    def from_scrape(cls, scraped, scene_id, stash:StashInterface):
        seconds = scraped["seconds"]
        if isinstance(seconds, (int, float)):
            seconds = float(seconds)
        elif isinstance(seconds, str):
            try:
                seconds = float(seconds)
            except ValueError:
                raise ValueError(f"Could not cast <Marker>.seconds string to float: '{seconds}' =!=> float()")
        else:
            raise ValueError(f"<Marker>.seconds has unexpected type {seconds}({type(seconds)})")

        # map primary_tag to an existing stash tag or create a new one
        primary_tag = stash.find_tag(scraped["primary_tag"], create=True)
        if not primary_tag:
            raise Exception(f'Could not find/create tag for <primary_tag>:"{scraped["primary_tag"]["name"]}"')
        
        # map other tags to existing stash tags or create them
        tag_ids = []
        for t in scraped.get("tags",[]):
            if t.get("stored_id"):
                tag_ids.append(t["stored_id"])
                continue
            stash_tag = stash.find_tag(t)
            if not stash_tag:
                log.warning(f'Could not find/create tag for <tag>:"{t["name"]}"')
                continue
            tag_ids.append(stash_tag["id"])

        return cls({
            "scene_id":scene_id,
            "title": scraped.get("title", primary_tag["name"]),
            "seconds": seconds,
            "primary_tag":primary_tag,
            "tag_ids":tag_ids
        })

    def gql_input(self):
        return {
            "scene_id":self.scene_id,
            "title":self.title,
            "seconds":self.seconds,
            "tag_ids":self.tag_ids,
            "primary_tag_id":self.primary_tag["id"]
        }


def import_scene_markers(stash:StashInterface, scraped_markers, stash_scene_id, closest_allowed_common_marker:int=15):
    """
    Import scraped scene markers into a scene of a given StashInstance

    :param stash: a StashInterface instance to connect to
    :param scraped_markers: a List of dicts that contain the following attrabutes
        {
            "seconds": <int>, <float>, <string> value parseable to float (REQUIRED)
            "primary_tag": <string> tag name (REQUIRED)
            "tags": [<string> tag name]
            "title": <string> title of marker
        }
    :param stash_scene_id: the SceneID of the Stash Scene from to apply the markers to
    :param closest_allowed_common_marker: markers are cosidered a match when they have the same primary_tag and seconds is +/- this value (Default 15)
    """

    mapped_markers = [Marker.from_scrape(m, stash_scene_id, stash) for m in scraped_markers]
    stash_markers = [Marker.from_gql(m) for m in stash.find_scene_markers(stash_scene_id, fragment=SCENE_MARKER_FRAGMENT)]    

    new_marker_list = []
    for scraped in mapped_markers:
        if scraped.seconds == 0: # skip all timestamps at 0 seconds
            continue

        within_limit = [existing.seconds for existing in stash_markers if scraped.within_distance(existing, closest_allowed_common_marker)]
        if within_limit:
            log.debug(f'Skipped Tag: {scraped.primary_tag["name"]} {scraped.seconds} +/- {closest_allowed_common_marker}(s) of {within_limit}')
            continue
            
        stash_marker = stash.create_scene_marker(scraped.gql_input(), SCENE_MARKER_FRAGMENT)

        # log.debug(f'created marker {m.site_name} ({m.primary_tag["name"]}) @{scraped_timestamp}')
        new_marker_list.append(stash_marker)
        
    log.info(f"created ({len(new_marker_list)}) new marker(s) for SceneID ({stash_scene_id})")
    new_marker_log = [f'{m["primary_tag"]["name"]}@{m["seconds"]}' for m in new_marker_list]
    log.debug(f"Markers: {new_marker_log}")
    
    return new_marker_list