# stashapi
This library primarily serves as an API wrapper for [Stash](https://github.com/stashapp/stash) written in Python

## Requirements
Developed using python 3.11.X with attempts to make things as backwards compatible where possible, if you are having issues please try using python 3.11

Should be fully supported up to and including Python 3.13. Stash currently bundles Python 3.12.7

## Installation 

##### To install from PyPI use this command:
`pip install stashapi`

##### To install directly from this repo use this command:
`pip install git+https://github.com/stg-annon/stashapi`

## Usage
```python
import stashapi.log as log
from stashapi.stashapp import StashInterface

stash = StashInterface({
    "scheme": "http",
    "host":"localhost",
    "port": "9999",
    "logger": log
})

scene_data = stash.find_scene(1234)
log.info(scene_data)
```
This example creates a connection to Stash query's a scene with ID 1234 and prints the result to Stash's logs
