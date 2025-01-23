import numpy as np
import cv2
from .base import FisheyeBase
from numpy import arange, sqrt, arctan, sin, tan, meshgrid, pi, hypot

class DefisheyeNode(FisheyeBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mapping": (["equidistant", "equisolid", "orthographic", "stereographic"],),
                "format": (["fullframe", "circular"],),
                "fov": ("FLOAT", {"default": 180.0, "min": 0.0, "max": 360.0, "step": 10.0}),
                "pfov": ("FLOAT", {"default": 120.0, "min": 0.0, "max": 360.0, "step": 10.0}),
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
