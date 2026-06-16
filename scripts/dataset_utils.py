#!/usr/bin/env python3
"""Shared helpers for building participant-facing datathon datasets."""

from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable


def read_datathon_readme(name: str) -> str:
    readme_path = Path(__file__).resolve().parents[1] / "readmes" / name
    return readme_path.read_text(encoding="utf-8")


def create_staging_directory(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists() or output.is_symlink():
        raise FileExistsError(
            f"Output already exists: {output}. Move or remove it before rebuilding."
        )

    job_id = os.environ.get("SLURM_JOB_ID", str(os.getpid()))
    staging = output.parent / f".{output.name}.building.{job_id}"
    if staging.exists() or staging.is_symlink():
        raise FileExistsError(f"Staging directory already exists: {staging}")

    staging.mkdir()
    return staging


def publish_staging_directory(staging: Path, output: Path) -> None:
    staging.rename(output.resolve())


def remove_staging_directory(staging: Path) -> None:
    if staging.exists():
        shutil.rmtree(staging)


def validate_unique_image(
    seen_images: dict[str, Path], image_name: str, source: Path
) -> None:
    if Path(image_name).name != image_name:
        raise ValueError(f"Image name is not a basename: {image_name}")

    previous = seen_images.get(image_name)
    if previous is not None:
        raise ValueError(
            f"Duplicate output image name {image_name}: {previous} and {source}"
        )
    seen_images[image_name] = source


def copy_images(
    image_sources: Iterable[tuple[Path, str]], destination: Path, workers: int
) -> None:
    tasks = list(image_sources)
    destination.mkdir()

    def copy_one(task: tuple[Path, str]) -> None:
        source, image_name = task
        if not source.is_file():
            raise FileNotFoundError(f"Missing source image: {source}")
        shutil.copy2(source, destination / image_name)

    completed = 0
    batch_size = max(workers * 100, 1_000)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(tasks), batch_size):
            batch = tasks[start : start + batch_size]
            futures = [executor.submit(copy_one, task) for task in batch]
            for future in as_completed(futures):
                future.result()
                completed += 1
                if completed % 10_000 == 0 or completed == len(tasks):
                    print(f"Copied {completed:,}/{len(tasks):,} images", flush=True)
