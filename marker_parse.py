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
		return self.seconds == other.seconds and self.primary_tag["id"] == other.primary_tag["id"]
	def __nq__(self, other) -> bool:
		return not self.__eq__(other)
	def __lt__(self, other) -> bool:
		return  self.seconds < other.seconds
	def __hash__(self) -> int:
		return hash(f'{self.primary_tag["id"]}@{self.seconds}')

	def __repr__(self) -> str:
		return f'<Marker>{str(self)}'
	def __str__(self) -> str:
		return f'{self.title}@{self.seconds}'

	def within_distance(self, other, seconds_distance:int=15):
		if not isinstance(other, Marker):
			raise ValueError(f"Marker.within_distance() must compare to <Marker> type not {type(other)}")
		return abs(self.seconds - other.seconds) < seconds_distance

	@property
	def tag_ids(self):
		return [t["id"] for t in self.tags]
	@property
	def primary_tag_id(self):
		return self.primary_tag["id"]

	@classmethod
	def from_gql(cls, fragment):
		return cls({
			"scene_id":fragment["scene"]["id"],
			"title": fragment["title"],
			"seconds":fragment["seconds"],
			"tags":fragment["tags"],
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
		tags = []
		for t in scraped.get("tags",[]):
			stash_tag = stash.find_tag(t)
			if not stash_tag:
				log.warning(f'Could not find/create tag for <tag>:"{t["name"]}"')
				continue
			tags.append(stash_tag)

		return cls({
			"scene_id":scene_id,
			"title": scraped.get("title", primary_tag["name"]),
			"seconds": seconds,
			"primary_tag":primary_tag,
			"tags":tags
		})

	def gql_input(self):
		return {
			"scene_id":self.scene_id,
			"title":self.title,
			"seconds":self.seconds,
			"tag_ids":self.tag_ids,
			"primary_tag_id":self.primary_tag_id
		}


def merge_markers(marker_list, distance=15):
	marker_list.sort(key=lambda m: m.seconds)
	merged_markers = []
	close_marker_sets = []
	for marker in marker_list:
		added_to_set = False
		for merged in close_marker_sets:
			for m in merged:
				if marker != m and marker.within_distance(m, distance):
					merged.append(marker)
					added_to_set = True
					break
			if added_to_set:
				break
		if not added_to_set:
			close_marker_sets.append([marker])
	
	for close_markers in close_marker_sets:
		log.debug(f"merged marker tags  {close_markers}")
		merge_target = close_markers[0]
		for marker in close_markers[1:]:
			merge_target.tags.append(marker.primary_tag)
		merged_markers.append(merge_target)
	return merged_markers

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

	# merges scraped markers within distance of each other into one marker 
	mapped_markers = merge_markers(mapped_markers, closest_allowed_common_marker)

	new_marker_list = []
	for scraped in mapped_markers:
		if scraped.seconds == 0: # skip all timestamps at 0 seconds
			continue

		within_limit = [existing.seconds for existing in stash_markers if scraped.within_distance(existing, closest_allowed_common_marker)]
		if within_limit:
			log.debug(f'Skipped Tag: {scraped.primary_tag["name"]} {scraped.seconds} +/- {closest_allowed_common_marker}(s) of {within_limit}')
			continue
			
		stash_marker = stash.create_scene_marker(scraped.gql_input(), SCENE_MARKER_FRAGMENT)
		if not stash_marker:
			log.warning(f'issue creating marker {scraped}')
		new_marker_list.append(stash_marker)

		
	log.info(f"created ({len(new_marker_list)}) new marker(s) for SceneID ({stash_scene_id})")
	new_marker_log = [f'{m["primary_tag"]["name"]}@{m["seconds"]}' for m in new_marker_list if m]
	log.debug(f"Markers: {new_marker_log}")
	
	return new_marker_list