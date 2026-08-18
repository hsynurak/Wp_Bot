"""Görsel ön işleme: boyutlandırma, RGB dönüşümü ve normalizasyon."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union

import torch
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


def pad_image_to_square(
    image: Image.Image,
    bg_color: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """
    Görseli en-boy oranını bozmadan beyaz pad ile kareye tamamlar.

    En uzun kenar referans alınır; orijinal görsel canvas'ın ortasına yapıştırılır.
    Böylece CLIP/Fashion-CLIP'e esnetilmiş (stretched) görsel gitmez.
    """
    width, height = image.size
    if width == height:
        return image

    side = max(width, height)
    canvas = Image.new("RGB", (side, side), bg_color)
    canvas.paste(image, ((side - width) // 2, (side - height) // 2))
    return canvas


class ImagePreprocessor:
    """
    Kalitesiz, farklı boyutlu veya bozuk görsellere karşı dayanıklı ön işleyici.
    ImageNet istatistikleri ile normalize edilmiş tensör üretir.
    """

    def __init__(self, image_size: int = 224) -> None:
            self._image_size = image_size
            self._transform = transforms.Compose(
                [
                    # 1. Oranı (aspect ratio) koruyarak en kısa kenarı 256 piksele düşür
                    transforms.Resize(256),
                    
                    # 2. Görselin tam merkezinden 224x224 boyutunda temiz bir kare kes
                    transforms.CenterCrop(image_size),
                    
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
        )

    def load_and_transform(self, image_path: PathLike) -> Optional[torch.Tensor]:
        """
        Tek bir görseli yükler ve (3, H, W) tensöre dönüştürür.
        Hata durumunda None döner; pipeline çökmez.
        """
        path = Path(image_path)
        try:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                return self._transform(rgb)
        except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
            logger.warning("Görsel işlenemedi [%s]: %s", path.name, exc)
            return None

    def load_batch(
        self, image_paths: List[PathLike]
    ) -> tuple[torch.Tensor, List[str]]:
        """
        Geçerli görselleri batch tensörüne birleştirir.
        Dönüş: (N, 3, H, W) tensörü ve başarılı dosya adları listesi.
        """
        tensors: List[torch.Tensor] = []
        valid_names: List[str] = []

        for path in image_paths:
            tensor = self.load_and_transform(path)
            if tensor is not None:
                tensors.append(tensor)
                valid_names.append(Path(path).name)

        if not tensors:
            return torch.empty(0, 3, self._image_size, self._image_size), []

        return torch.stack(tensors, dim=0), valid_names
