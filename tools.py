import base64
from collections import defaultdict

def defaultify(d:dict, default=None):
	"""Return default dict for given nested dictionaries with provided default value"""
	if not isinstance(d, dict):
		return d
	return defaultdict(lambda: default, {k: defaultify(v) for k, v in d.items()})

def clean_dict(to_clean):
# returns dictionary where values are not None
	return {k:v for k,v in to_clean.items() if v and "__" not in k}

def get_base64(image_path):
	"""get base64 encoded image from local image path

	Args:
		 image_path (str): path to image file

	Returns:
		 str: base64 encoded string of image
	"""	
	with open(image_path, "rb") as img:
		b64img_bytes = base64.b64encode(img.read())
	if not b64img_bytes:
		return None
	return f"data:image/jpeg;base64,{b64img_bytes.decode('utf-8')}"

def human_bytes(size):
	size = int(size)
	power = 1024
	n = 0
	power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
	while size > power:
		size /= power
		n += 1
	return f"{size:.2f}{power_labels[n]}B"

def human_bits(size):
	return human_bytes(size/8)
	
def phash_distance(lhash, rhash):
	assert len(lhash) == len(rhash)
	hamming = int(lhash,16) ^ int(rhash,16)
	return bin(hamming).count("1")

def similarity_score(lhash, rhash):
	return 1-(phash_distance(lhash, rhash)/64.0)