import base64
from collections import defaultdict
import hashlib
import math
import re
import string

import requests
from typing_extensions import deprecated

RE_PUNCTUATION = re.compile(f"[{string.punctuation}]")
RE_WHITESPACE = re.compile(f"[{string.whitespace}]")


def defaultify(d: dict, default=None):
    """Return default dict for given nested dictionaries with provided default value"""
    if not isinstance(d, dict):
        return d
    return defaultdict(lambda: default, {k: defaultify(v) for k, v in d.items()})


def clean_dict(to_clean):
    # returns dictionary where values are not None
    return {k: v for k, v in to_clean.items() if v and "__" not in k}


def normalize_str(string_in: str) -> str:
    # remove punctuation
    string_in = re.sub(RE_PUNCTUATION, " ", string_in)

    # normalize whitespace
    string_in = re.sub(RE_WHITESPACE, " ", string_in)

    # remove leading and trailing whitespace
    string_in = string_in.strip(string.whitespace)

    return string_in


def str_compare(s1: str, s2: str, ignore_case: bool = True) -> bool:
    """
    Normalize and compare the given strings. Performs a case-insensitive comparison by default. Use the `ignore_case`
    parameter to control this behavior.

    Args:
        s1 (str): the first string
        s2 (str): the second string
        ignore_case (bool, optional): whether to perform case-insensitive
            (True, default) or case sensitive (False) comparison
    """
    s1 = normalize_str(s1)
    s2 = normalize_str(s2)

    if ignore_case:
        return s1.lower() == s2.lower()
    return s1 == s2


def sha256(pth: str, return_object: bool = False, buffer: int = 65536):
    sha256_value = hashlib.sha256()
    with open(pth, "rb") as f:
        while True:
            data = f.read(buffer)
            if not data:
                break
            sha256_value.update(data)
    if return_object:
        return sha256_value
    return sha256_value.hexdigest()


@deprecated("Use file_to_base64() instead")
def get_base64(pth: str) -> str:
    return file_to_base64(pth)


def url_to_base64(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=2)
    except:
        return None

    if not r.ok:
        return None

    b64img_bytes = base64.b64encode(r.content)
    content_type = r.headers.get("Content-Type", "image/jpeg")
    return f"data:{content_type};base64,{b64img_bytes.decode('utf-8')}"


def file_to_base64(image_path: str) -> str:
    """
    get base64 encoded image from local image path

    Args:
        image_path (str): path to image file

    Returns:
        str: base64 encoded string of image
    """

    from pathlib import Path
    import mimetypes

    mime = mimetypes.types_map.get(Path(image_path).suffix, "image/jpeg")
    with open(image_path, "rb") as img:
        b64img_bytes = base64.b64encode(img.read())
    return f"data:{mime};base64,{b64img_bytes.decode('utf-8')}"


def si_prefix(value: float, decimals: int, preferred_prefix: str = "") -> str:
    SI_PREFIX_UNITS = "yzafpnµm kMGTPEZY"

    units_mid = (len(SI_PREFIX_UNITS) - 1) // 2
    if preferred_index := SI_PREFIX_UNITS.index(preferred_prefix):
        tens_exponent = 3 * (preferred_index - units_mid)
    else:
        tens_exponent = int(math.log(value, 10))
    si_level = tens_exponent // 3
    try:
        prefix = SI_PREFIX_UNITS[si_level + units_mid]
    except:
        prefix = f"e{tens_exponent}"

    value /= 10 ** (si_level * 3)
    return f"{value:.{decimals}f}{prefix}"


def human_bytes(value: float, round: int = 1, prefix: str = ""):
    try:
        return f"{si_prefix(value, round, prefix)}B"
    except:
        return f"{value:.{round}f}B"


def human_bits(value: float, round: int = 1, prefix: str = ""):
    try:
        return f"{si_prefix(value, round, prefix)}b"
    except:
        return f"{value:.{round}f}b"


def phash_distance(lhash: str, rhash: str) -> int:
    assert len(lhash) == len(rhash)
    hamming = int(lhash, 16) ^ int(rhash, 16)
    return bin(hamming).count("1")


def similarity_score(lhash: str, rhash: str) -> float:
    """
    compares two phashes to determine how simmilar they are

    Args:
        lhash (str): "left" phash
        rhash (str): "right" phash

    Returns:
        float: simmilarity percentage
    """
    return 1 - (phash_distance(lhash, rhash) / 64.0)


def crypto_hash(remote, algorithm: str = "md5") -> str:
    if algorithm == "md5":
        hashfn = hashlib.md5()
    elif algorithm == "sha1":
        hashfn = hashlib.sha1()
    elif algorithm == "sha256":
        hashfn = hashlib.sha256()
    elif algorithm == "sha384":
        hashfn = hashlib.sha384()
    elif algorithm == "sha512":
        hashfn = hashlib.sha512()
    else:
        raise NotImplementedError(f'Unsupported hash function "{algorithm}"')

    while True:
        data = remote.read(4096)
        if not data:
            break
        hashfn.update(data)
    return hashfn.hexdigest()
