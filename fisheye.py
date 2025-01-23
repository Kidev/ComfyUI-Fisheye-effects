import numpy as np
import cv2
from numpy import arange, sqrt, arctan, sin, tan, meshgrid, pi, hypot
from .base import FisheyeBase

class FisheyeNode(FisheyeBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mapping": (["equidistant", "equisolid", "orthographic", "stereographic"],),
                "format": (["fullframe", "circular"],),
                "fov": ("FLOAT", {"default": 180.0, "min": 0.0, "max": 360.0, "step": 10.0}),
                "pfov": ("FLOAT", {"default": 120.0, "min": 0.0, "max": 360.0, "step": 10.0}),
                "entire_image": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_fisheye"
    CATEGORY = "image/processing"

    def calculate_zoom_factor(self, fov_in, fov_out, mapping):
        fov_in_rad = fov_in * pi / 180.0
        fov_out_rad = fov_out * pi / 180.0

        max_in = tan(fov_in_rad / 2.0)

        if mapping == "equidistant":
            max_out = fov_out_rad / 2.0
        elif mapping == "equisolid":
            max_out = 2 * sin(fov_out_rad / 4.0)
        elif mapping == "orthographic":
            max_out = sin(fov_out_rad / 2.0)
        elif mapping == "stereographic":
            max_out = 2 * tan(fov_out_rad / 4.0)

        # Return zoom factor needed to make output radius contain input
        return max_out / max_in if max_in > 0 else 1.0

    def get_focal_length(self, dim, fov_degrees):
        fov_rad = fov_degrees * pi / 180.0
        half_fov = fov_rad / 2.0

        if self.mapping == "equidistant":
            return dim / fov_rad
        elif self.mapping == "equisolid":
            return dim / (4 * sin(half_fov / 2))
        elif self.mapping == "orthographic":
            return dim / (2 * sin(half_fov))
        elif self.mapping == "stereographic":
            return dim / (4 * tan(half_fov / 2))
        return dim / 2

    def map_fisheye(self, i, j, width, height, dim, xcenter, ycenter):
        xd = i - xcenter
        yd = j - ycenter
        rd = hypot(xd, yd)

        f_out = self.get_focal_length(dim, self.fov)
        f_in = self.get_focal_length(dim, self.pfov)

        if self.entire_image:
            zoom = self.calculate_zoom_factor(self.pfov, self.fov, self.mapping)
            f_in *= zoom

        theta = arctan(rd / f_in)

        if self.mapping == "equidistant":
            r = f_out * theta
        elif self.mapping == "equisolid":
            r = 2 * f_out * sin(theta / 2)
        elif self.mapping == "orthographic":
            r = f_out * sin(theta)
        elif self.mapping == "stereographic":
            r = 2 * f_out * tan(theta / 2)

        rdmask = rd != 0
        xs = xd.astype(np.float32).copy()
        ys = yd.astype(np.float32).copy()

        xs[rdmask] = (rd[rdmask] / r[rdmask]) * xd[rdmask] + xcenter
        ys[rdmask] = (rd[rdmask] / r[rdmask]) * yd[rdmask] + ycenter

        xs[~rdmask] = xcenter
        ys[~rdmask] = ycenter

        return xs, ys

    def apply_fisheye(self, image, mapping, format, fov, pfov, entire_image):
        self.setup_parameters(fov, pfov, mapping, format)
        self.entire_image = entire_image

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
