"""
Çoklu model destekli embedding çıkarıcılar (Factory Pattern).

Desteklenen modeller: ResNet50, EfficientNet-B0/B4, CLIP.
Sınıflandırma başlıkları devre dışı — yalnızca vektör üretilir.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union
from PIL import Image, UnidentifiedImageError

import torch
import torch.nn as nn
import io
from src.preprocessing.image_preprocessor import pad_image_to_square
from torch.utils.data import default_collate
from torchvision import models, transforms

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


class BaseExtractor(nn.Module, ABC):
    """
    Tüm feature extractor'lar için ortak arayüz.
    Her alt sınıf kendi ön işleme ve backbone mantığını uygular.
    """

    def __init__(self, device: Optional[str] = None) -> None:
        super().__init__()
        self._device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )

    @property
    def device(self) -> torch.device:
        return self._device

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Benzersiz model tanımlayıcı (örn. resnet50)."""

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Çıktı vektör boyutu."""

    @abstractmethod
    def preprocess_paths(
        self, image_paths: List[PathLike]
    ) -> Tuple[torch.Tensor, List[str]]:
        """
        Dosya yollarından model-uyumlu batch tensörü üretir.
        Dönüş: (N, ...) tensör ve geçerli dosya adları.
        """

    @torch.inference_mode()
    def extract(self, batch: torch.Tensor) -> torch.Tensor:
        """
        Batch tensöründen embedding üretir.
        Alt sınıflar gerekirse override edebilir.
        """
        if batch.numel() == 0:
            return torch.empty(0, self.embedding_dim)

        batch = batch.to(self._device)
        features = self._forward_features(batch)
        return features.cpu()

    @abstractmethod
    def _forward_features(self, batch: torch.Tensor) -> torch.Tensor:
        """Model forward — ham özellik vektörü."""

    @torch.inference_mode()
    def extract_from_paths(
        self,
        image_paths: List[PathLike],
        batch_size: int = 16,
    ) -> Tuple[List[List[float]], List[str]]:
        """RAM dostu batch'ler halinde dosyalardan embedding üretir."""
        all_embeddings: List[List[float]] = []
        all_ids: List[str] = []

        for start in range(0, len(image_paths), batch_size):
            chunk = image_paths[start : start + batch_size]
            batch_tensor, valid_names = self.preprocess_paths(chunk)

            if batch_tensor.numel() == 0:
                logger.warning(
                    "[%s] Batch atlandı (geçersiz görseller): %d",
                    self.model_name,
                    start,
                )
                continue

            vectors = self.extract(batch_tensor)
            all_embeddings.extend(vectors.tolist())
            all_ids.extend(valid_names)

        return all_embeddings, all_ids


class TorchvisionExtractor(BaseExtractor):
    """
    torchvision tabanlı modeller için ortak taban (ResNet, EfficientNet).
    ImageNet ağırlıklarına uygun resmi transform pipeline kullanır.
    """

    def __init__(
        self,
        device: Optional[str] = None,
        build_fn: Optional[Callable[[], Tuple[nn.Module, transforms.Compose]]] = None,
    ) -> None:
        super().__init__(device)
        if build_fn is None:
            raise ValueError("build_fn zorunludur")
        self._model, self._transform = build_fn()
        self._model = self._model.to(self._device).eval()

    def preprocess_paths(
        self, image_paths: List[PathLike]
    ) -> Tuple[torch.Tensor, List[str]]:
        tensors: List[torch.Tensor] = []
        valid_names: List[str] = []

        for path in image_paths:
            path = Path(path)
            try:
                with Image.open(path) as img:
                    tensor = self._transform(img.convert("RGB"))
                    tensors.append(tensor)
                    valid_names.append(path.name)
            except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
                logger.warning("Görsel işlenemedi [%s]: %s", path.name, exc)

        if not tensors:
            return torch.empty(0), []

        return default_collate(tensors), valid_names

    def _forward_features(self, batch: torch.Tensor) -> torch.Tensor:
        return self._model(batch)


class ResNetExtractor(TorchvisionExtractor):
    """ResNet50 — fc katmanı Identity; 2048 boyutlu vektör."""

    def __init__(self, device: Optional[str] = None) -> None:
        super().__init__(device=device, build_fn=self._create_backbone)
        logger.info(
            "%s hazır | boyut=%d | cihaz=%s",
            self.model_name,
            self.embedding_dim,
            self._device,
        )

    @property
    def model_name(self) -> str:
        return "resnet50"

    @property
    def embedding_dim(self) -> int:
        return 2048

    @staticmethod
    def _create_backbone() -> Tuple[nn.Module, transforms.Compose]:
        weights = models.ResNet50_Weights.IMAGENET1K_V2
        backbone = models.resnet50(weights=weights)
        backbone.fc = nn.Identity()  # Sınıflandırma yok — sadece embedding
        return backbone, weights.transforms()


class EfficientNetExtractor(TorchvisionExtractor):
    """EfficientNet-B0 veya B4 — classifier Identity ile özellik vektörü."""

    _VARIANTS: Dict[str, Tuple[Callable, object, int]] = {
        "b0": (
            models.efficientnet_b0,
            models.EfficientNet_B0_Weights.IMAGENET1K_V1,
            1280,
        ),
        "b4": (
            models.efficientnet_b4,
            models.EfficientNet_B4_Weights.IMAGENET1K_V1,
            1792,
        ),
    }

    def __init__(self, variant: str = "b0", device: Optional[str] = None) -> None:
        variant = variant.lower()
        if variant not in self._VARIANTS:
            raise ValueError(
                f"Geçersiz variant: {variant}. Seçenekler: {list(self._VARIANTS)}"
            )
        self._variant = variant
        self._dim = self._VARIANTS[variant][2]
        super().__init__(device=device, build_fn=self._create_backbone)
        logger.info(
            "%s hazır | boyut=%d | cihaz=%s",
            self.model_name,
            self.embedding_dim,
            self._device,
        )

    @property
    def model_name(self) -> str:
        return f"efficientnet_{self._variant}"

    @property
    def embedding_dim(self) -> int:
        return self._dim

    def _create_backbone(self) -> Tuple[nn.Module, transforms.Compose]:
        builder, weights_enum, _ = self._VARIANTS[self._variant]
        weights = weights_enum
        backbone = builder(weights=weights)
        backbone.classifier = nn.Identity()
        return backbone, weights.transforms()


class CLIPExtractor(BaseExtractor):
    """
    OpenAI CLIP — görsel encoder.
    Ön işleme ResNet'ten farklıdır; CLIPProcessor zorunludur.
    """

    DEFAULT_MODEL_ID = "patrickjohncyh/fashion-clip"

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        device: Optional[str] = None,
        normalize: bool = True,
        pad_to_square: bool = False,
        pad_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        super().__init__(device)
        self._model_id = model_id
        self._normalize = normalize
        self._pad_to_square = pad_to_square
        self._pad_color = pad_color

        try:
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise ImportError(
                "CLIP için transformers gerekli: pip install transformers"
            ) from exc

        self._processor = CLIPProcessor.from_pretrained(model_id)
        self._model = CLIPModel.from_pretrained(model_id)
        self._model = self._model.to(self._device).eval()

        logger.info(
            "%s hazır | model=%s | boyut=%d | pad=%s | cihaz=%s",
            self.model_name,
            model_id,
            self.embedding_dim,
            pad_to_square,
            self._device,
        )

    @property
    def model_name(self) -> str:
        return "clip"

    @property
    def embedding_dim(self) -> int:
        return self._model.config.projection_dim

    def preprocess_paths(
        self, image_paths: List[PathLike]
    ) -> Tuple[torch.Tensor, List[str]]:
        images: List[Image.Image] = []
        valid_names: List[str] = []

        for path in image_paths:
            path = Path(path)
            try:
                with Image.open(path) as img:
                    rgb = img.convert("RGB")
                    # CLIPProcessor öncesi: aspect ratio korunarak kareye pad
                    if self._pad_to_square:
                        rgb = pad_image_to_square(rgb, bg_color=self._pad_color)
                    images.append(rgb)
                    valid_names.append(path.name)
            except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
                logger.warning("Görsel işlenemedi [%s]: %s", path.name, exc)

        if not images:
            return torch.empty(0), []

        inputs = self._processor(images=images, return_tensors="pt", padding=True)
        return inputs["pixel_values"], valid_names

    @torch.inference_mode()
    def extract_from_bytes(
        self, image_bytes_list: List[bytes]
    ) -> Tuple[List[List[float]], List[str]]:
        """Görselleri diskten değil, doğrudan RAM'deki byte verisinden okur."""
        import io
        
        images: List[Image.Image] = []
        valid_indices: List[str] = []

        for i, img_bytes in enumerate(image_bytes_list):
            try:
                # Byte verisini sanki bir dosyadan okuyormuş gibi bellekte aç
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                if self._pad_to_square:
                    img = pad_image_to_square(img, bg_color=self._pad_color)
                images.append(img)
                valid_indices.append(str(i))
            except Exception as exc:
                logger.warning("Byte verisi görsel olarak işlenemedi: %s", exc)

        if not images:
            return [], []

        inputs = self._processor(images=images, return_tensors="pt", padding=True)
        batch = inputs["pixel_values"].to(self._device)
        
        features = self._forward_features(batch)
        return features.cpu().tolist(), valid_indices

    @staticmethod
    def _to_feature_tensor(model: nn.Module, output: object) -> torch.Tensor:
        """
        transformers sürümünden bağımsız olarak embedding tensörüne çevirir.
        Eski API: Tensor | Yeni API (>=4.50): BaseModelOutputWithPooling
        """
        if isinstance(output, torch.Tensor):
            return output

        pooler = getattr(output, "pooler_output", None)
        if pooler is not None:
            return pooler

        hidden = getattr(output, "last_hidden_state", None)
        if hidden is not None:
            cls_token = hidden[:, 0, :]
            return model.visual_projection(cls_token)

        raise TypeError(f"CLIP çıktısı tensöre çevrilemedi: {type(output)}")

    def _forward_features(self, batch: torch.Tensor) -> torch.Tensor:
        output = self._model.get_image_features(pixel_values=batch)
        features = self._to_feature_tensor(self._model, output)

        if self._normalize:
            return features / features.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        return features


# Geriye dönük uyumluluk
FeatureExtractor = ResNetExtractor


class FeatureExtractorFactory:
    """Model adına göre uygun extractor örneği üretir (Factory Pattern)."""

    _SUPPORTED = ("resnet50", "efficientnet_b0", "efficientnet_b4", "clip")

    @classmethod
    def supported_models(cls) -> List[str]:
        return list(cls._SUPPORTED)

    @classmethod
    def create(cls, model_name: str, device: Optional[str] = None, **kwargs) -> BaseExtractor:
        """
        Args:
            model_name: resnet50 | efficientnet_b0 | efficientnet_b4 | clip
        """
        key = model_name.lower().strip()

        if key == "resnet50":
            return ResNetExtractor(device=device)
        if key == "efficientnet_b0":
            return EfficientNetExtractor(variant="b0", device=device)
        if key == "efficientnet_b4":
            return EfficientNetExtractor(variant="b4", device=device)
        if key == "clip":
            from src.config import (
                CLIP_MODEL_ID,
                CLIP_NORMALIZE,
                CLIP_PAD_COLOR,
                CLIP_PAD_TO_SQUARE,
            )

            return CLIPExtractor(
                device=device,
                model_id=kwargs.pop("model_id", CLIP_MODEL_ID),
                normalize=kwargs.pop("normalize", CLIP_NORMALIZE),
                pad_to_square=kwargs.pop("pad_to_square", CLIP_PAD_TO_SQUARE),
                pad_color=kwargs.pop("pad_color", CLIP_PAD_COLOR),
                **kwargs,
            )

        raise ValueError(
            f"Bilinmeyen model: {model_name}. Desteklenenler: {cls.supported_models()}"
        )


def get_extractor(model_name: str, device: Optional[str] = None, **kwargs) -> BaseExtractor:
    """Factory kısayolu — notebook ve API'den doğrudan çağrılabilir."""
    return FeatureExtractorFactory.create(model_name, device=device, **kwargs)


def get_clip_extractor(device: Optional[str] = None, **kwargs) -> CLIPExtractor:
    """Config'deki CLIP parametreleriyle extractor oluşturur."""
    extractor = get_extractor("clip", device=device, **kwargs)
    assert isinstance(extractor, CLIPExtractor)
    return extractor
