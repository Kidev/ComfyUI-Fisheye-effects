import numpy as np
import torch


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
