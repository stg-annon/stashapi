import base64, math
from collections import defaultdict

def defaultify(d:dict, default=None):
	"""Return default dict for given nested dictionaries with provided default value"""
	if not isinstance(d, dict):
		return d
	return defaultdict(lambda: default, {k: defaultify(v) for k, v in d.items()})

def clean_dict(to_clean):
# returns dictionary where values are not None
	return {k:v for k,v in to_clean.items() if v and "__" not in k}

def get_base64(pth):
	"""deprecated use file_to_base64() instead"""
	return file_to_base64(pth)

def url_to_base64(url):
	import requests
	return base64.b64encode(requests.get(url).content)

def file_to_base64(image_path):

	from pathlib import Path
	import mimetypes
	"""get base64 encoded image from local image path

	Args:
		 image_path (str): path to image file

	Returns:
		 str: base64 encoded string of image
	"""
	mime =  mimetypes.types_map.get(Path(image_path).suffix, 'image/jpeg')
	with open(image_path, "rb") as img:
		b64img_bytes = base64.b64encode(img.read())
	if not b64img_bytes:
		return None
	return f"data:{mime};base64,{b64img_bytes.decode('utf-8')}"

def si_prefix(size, round):
	power_labels = {3:'K', 6:'M', 9:'G', 12:'T'}
	log_s = int(math.log(size,10))
	use_power = [p for p in power_labels.keys() if p <= log_s]
	if not use_power:
		return f"{size:.{round}f}"
	use_power = max(use_power)
	size = size / 10**use_power
	return f"{size:.{round}f}{power_labels[use_power]}"

def human_bytes(size, round=1):
	return f"{si_prefix(size, round)}B"
def human_bits(size, round=1):
	return f"{si_prefix(size, round)}b"
	
def phash_distance(lhash, rhash):
	assert len(lhash) == len(rhash)
	hamming = int(lhash,16) ^ int(rhash,16)
	return bin(hamming).count("1")

def similarity_score(lhash, rhash):
	return 1-(phash_distance(lhash, rhash)/64.0)