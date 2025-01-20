import os
import numpy as np
import cv2
from PIL import Image
import torch
from numpy import arange, sqrt, arctan, sin, tan, meshgrid, pi, hypot

class FisheyeBase:
    def setup_parameters(self, fov, pfov, mapping, format):
        self.fov = fov
        self.pfov = pfov
        self.mapping = mapping
        self.format = format

    def process_image_tensor(self, image):
        if isinstance(image, torch.Tensor):
            if len(image.shape) == 4:
                image = image[0]
            image_np = (image.cpu().numpy() * 255).astype(np.uint8)
        else:
            image_np = image
        return image_np

    def tensor_to_image(self, tensor):
        img_np = np.array(tensor).astype(np.float32) / 255.0
        return torch.from_numpy(img_np).unsqueeze(0)

class FisheyeNode(FisheyeBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mapping": (["equidistant", "equisolid", "orthographic", "stereographic"],),
                "format": (["fullframe", "circular"],),
                "fov": ("FLOAT", {"default": 180.0, "min": 0.0, "max": 360.0, "step": 0.1}),
                "pfov": ("FLOAT", {"default": 120.0, "min": 0.0, "max": 360.0, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_fisheye"
    CATEGORY = "image/processing"

    def map_fisheye(self, i, j, width, height, dim, xcenter, ycenter):
        xd = i - xcenter
        yd = j - ycenter
        rd = hypot(xd, yd)

        rn = rd / (dim / 2)

        theta = rn * (self.fov * pi / 360)

        # See https://en.wikipedia.org/wiki/Fisheye_lens
        if self.mapping == "equidistant":
            r = theta
        elif self.mapping == "equisolid":
            r = 2 * sin(theta / 2)
        elif self.mapping == "orthographic":
            r = sin(theta)
        elif self.mapping == "stereographic":
            r = 2 * tan(theta / 2)

        r = r * (dim / 2)

        rdmask = rd != 0

        xs = xd.astype(np.float32).copy()
        ys = yd.astype(np.float32).copy()

        xs[rdmask] = (r[rdmask] / rd[rdmask]) * xd[rdmask] + xcenter
        ys[rdmask] = (r[rdmask] / rd[rdmask]) * yd[rdmask] + ycenter

        xs[~rdmask] = xcenter
        ys[~rdmask] = ycenter

        return xs, ys

    def apply_fisheye(self, image, mapping, format, fov, pfov):
        self.setup_parameters(fov, pfov, mapping, format)

        image_np = self.process_image_tensor(image)

        height, width = image_np.shape[:2]
        xcenter = width // 2
        ycenter = height // 2

        if format == "circular":
            dim = min(width, height)
        else:  # fullframe
            dim = sqrt(width ** 2 + height ** 2)

        i = arange(width)
        j = arange(height)
        i, j = meshgrid(i, j)

        xs, ys = self.map_fisheye(i, j, width, height, dim, xcenter, ycenter)

        remapped = cv2.remap(image_np, xs, ys, cv2.INTER_LINEAR)

        return (self.tensor_to_image(remapped),)

class DefisheyeNode(FisheyeBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mapping": (["equidistant", "equisolid", "orthographic", "stereographic"],),
                "format": (["fullframe", "circular"],),
                "fov": ("FLOAT", {"default": 180.0, "min": 0.0, "max": 360.0, "step": 5.0}),
                "pfov": ("FLOAT", {"default": 120.0, "min": 0.0, "max": 360.0, "step": 5.0}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "remove_fisheye"
    CATEGORY = "image/processing"

    def map_defisheye(self, i, j, width, height, dim, xcenter, ycenter):
        xd = i - xcenter
        yd = j - ycenter
        rd = hypot(xd, yd)

        ofoc = dim / (2 * tan(self.pfov * pi / 360))
        ofocinv = 1.0 / ofoc
        phiang = arctan(ofocinv * rd)

        if self.mapping == "equidistant":
            ifoc = dim * 180 / (self.fov * pi)
            rr = ifoc * phiang

        elif self.mapping == "equisolid":
            ifoc = dim / (2.0 * sin(self.fov * pi / 720))
            rr = ifoc * sin(phiang / 2)

        elif self.mapping == "orthographic":
            ifoc = dim / (2.0 * sin(self.fov * pi / 360))
            rr = ifoc * sin(phiang)

        elif self.mapping == "stereographic":
            ifoc = dim / (2.0 * tan(self.fov * pi / 720))
            rr = ifoc * tan(phiang / 2)

        rdmask = rd != 0
        xs = xd.astype(np.float32).copy()
        ys = yd.astype(np.float32).copy()

        xs[rdmask] = (rr[rdmask] / rd[rdmask]) * xd[rdmask] + xcenter
        ys[rdmask] = (rr[rdmask] / rd[rdmask]) * yd[rdmask] + ycenter

        xs[~rdmask] = xcenter
        ys[~rdmask] = ycenter

        return xs, ys

    def remove_fisheye(self, image, mapping, format, fov, pfov):
        self.setup_parameters(fov, pfov, mapping, format)

        image_np = self.process_image_tensor(image)

        height, width = image_np.shape[:2]
        xcenter = width // 2
        ycenter = height // 2

        if format == "circular":
            dim = min(width, height)
        else:  # fullframe
            dim = sqrt(width ** 2 + height ** 2)

        i = arange(width)
        j = arange(height)
        i, j = meshgrid(i, j)

        xs, ys = self.map_defisheye(i, j, width, height, dim, xcenter, ycenter)

        remapped = cv2.remap(image_np, xs, ys, cv2.INTER_LINEAR)

        return (self.tensor_to_image(remapped),)

NODE_CLASS_MAPPINGS = {
    "Fisheye": FisheyeNode,
    "Defisheye": DefisheyeNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Fisheye": "Apply Fisheye Effect",
    "Defisheye": "Remove Fisheye Effect"
}
