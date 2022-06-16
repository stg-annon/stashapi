from collections import defaultdict

def defaultify(d:dict, default=None):
	"""Return default dict for given nested dictionaries with provided default value"""
	if not isinstance(d, dict):
		return d
	return defaultdict(lambda: default, {k: defaultify(v) for k, v in d.items()})

def clean_dict(to_clean):
# returns dictionary where values are not None
	return {k:v for k,v in to_clean.items() if v and "__" not in k}

def human_bytes(size):
	# 2**10 = 1024
	size = int(size)
	power = 2**10
	n = 0
	power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
	while size > power:
		size /= power
		n += 1
	return f"{size:.2f}{power_labels[n]}B"
	
