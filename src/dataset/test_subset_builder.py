"""50 fotoğraflık tekrarlanabilir test veri seti oluşturucu."""

from __future__ import annotations

import json
import logging
import random
import shutil
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class TestSubsetBuilder:
    """
    photos/ klasöründen örneklem alır, manifest yazar ve isteğe bağlı kopyalar.
    Thumb görselleri mümkün olduğunca eler (tam çözünürlük tercih).
    """

    def __init__(
        self,
        source_dir: Path,
        output_dir: Path,
        manifest_path: Path,
        subset_size: int = 500,
        seed: int = 42,
        copy_files: bool = True,
    ) -> None:
        self._source_dir = source_dir
        self._output_dir = output_dir
        self._manifest_path = manifest_path
        self._subset_size = subset_size
        self._seed = seed
        self._copy_files = copy_files

    def _list_candidates(self) -> List[Path]:
        all_files = [
            p
            for p in self._source_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
        ]
        # Önce thumb olmayanları tercih et
        full_res = [p for p in all_files if "_thumb" not in p.name.lower()]
        if len(full_res) >= self._subset_size:
            return full_res
        return all_files

    def build(self) -> List[Path]:
        """Test alt kümesini oluşturur ve seçilen yolları döner."""
        candidates = self._list_candidates()
        if len(candidates) < self._subset_size:
            raise ValueError(
                f"Yeterli görsel yok: {len(candidates)} < {self._subset_size}"
            )

        rng = random.Random(self._seed)
        selected = sorted(rng.sample(candidates, self._subset_size))

        if self._copy_files:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            for src in selected:
                dst = self._output_dir / src.name
                if not dst.exists():
                    shutil.copy2(src, dst)

        manifest = {
            "company_id": None,  # notebook tarafında doldurulabilir
            "seed": self._seed,
            "count": len(selected),
            "files": [p.name for p in selected],
            "paths": [str(p) for p in selected],
        }
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        logger.info(
            "%d görsel seçildi | manifest: %s",
            len(selected),
            self._manifest_path,
        )
        return selected
