"""WhatsApp sorgu görselleri için yüz kırpma ve arka plan temizleme."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

from src.config import TEMP_UPLOADS_DIR

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Gelen görsellerde üst bölgedeki yüzleri kırpar, arka planı temizler
    ve beyaz zemin üzerinde kaydeder.
    """

    def __init__(self) -> None:
        self._face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            classifier = cv2.CascadeClassifier(cascade_path)
            if classifier.empty():
                logger.warning(
                    "OpenCV CascadeClassifier yüklenemedi, yüz kırpma atlanacak, "
                    "doğrudan arka plan temizliğine geçilecek."
                )
            else:
                self._face_cascade = classifier
        except (AttributeError, Exception):
            logger.warning(
                "OpenCV CascadeClassifier yüklenemedi, yüz kırpma atlanacak, "
                "doğrudan arka plan temizliğine geçilecek."
            )

    def process_image(self, image_path: str) -> Path:
        """
        Görseli yüz kırpma → arka plan silme → beyaz zemin akışından geçirir.

        Returns:
            TEMP_UPLOADS_DIR altına kaydedilen işlenmiş görselin yolu.
        """
        source = Path(image_path)
        if not source.is_file():
            raise FileNotFoundError(f"Görsel bulunamadı: {image_path}")

        image_bgr = cv2.imread(str(source))
        if image_bgr is None:
            raise ValueError(f"OpenCV görseli okuyamadı: {image_path}")

        if self._face_cascade is not None:
            cropped_bgr = self._crop_upper_face_region(image_bgr)
        else:
            cropped_bgr = image_bgr

        cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(cropped_rgb)

        rgba_output = remove(pil_image)
        final_rgb = self._apply_white_background(rgba_output)

        TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = TEMP_UPLOADS_DIR / f"preprocessed_{uuid.uuid4().hex}.jpg"
        final_rgb.save(output_path, format="JPEG", quality=95)

        logger.info(
            "Görsel ön işlendi | kaynak=%s | hedef=%s",
            source.name,
            output_path.name,
        )
        return output_path

    def _crop_upper_face_region(self, image_bgr: np.ndarray) -> np.ndarray:
        """Üst %35'te yüz varsa çene altından yatay kırpma uygular."""
        if self._face_cascade is None:
            return image_bgr

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )

        if len(faces) == 0:
            return image_bgr

        height = image_bgr.shape[0]
        top_region_limit = height * 0.35

        best_face: tuple[int, int, int, int] | None = None
        best_area = 0
        for x, y, face_w, face_h in faces:
            if y >= top_region_limit:
                continue

            area = face_w * face_h
            if area > best_area:
                best_area = area
                best_face = (x, y, face_w, face_h)

        if best_face is None:
            return image_bgr

        _, y, _, face_h = best_face
        chin_y = y + face_h
        if chin_y >= height - 1:
            return image_bgr

        logger.info(
            "Üst bölge yüzü tespit edildi, kırpılıyor | chin_y=%d | height=%d",
            chin_y,
            height,
        )
        return image_bgr[chin_y:, :]

    @staticmethod
    def _apply_white_background(image: Image.Image) -> Image.Image:
        """RGBA çıktıyı beyaz arka planlı RGB görsele dönüştürür."""
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            return background

        return image.convert("RGB")
