from collections import defaultdict

def defaultify(d:dict, default=None):
    """Return default dict for given nested dictionaries with provided default value"""
    if not isinstance(d, dict):
        return d
    return defaultdict(lambda: default, {k: defaultify(v) for k, v in d.items()})