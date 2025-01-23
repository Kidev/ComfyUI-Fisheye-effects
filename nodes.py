from .fisheye import FisheyeNode
from .defisheye import DefisheyeNode

NODE_CLASS_MAPPINGS = {
    "Fisheye": FisheyeNode,
    "Defisheye": DefisheyeNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Fisheye": "Apply Fisheye Effect",
    "Defisheye": "Remove Fisheye Effect"
}
