#!/usr/bin/env python3
"""Upload KLIK-Bench dataset to HuggingFace Hub."""

import argparse
from pathlib import Path

from huggingface_hub import HfApi, create_repo


def collect_task_files(tasks_dir: Path) -> list[Path]:
    """Collect all YAML task files from a directory."""
    return sorted(tasks_dir.glob("*.yaml"))


def upload_benchmark(repo_id: str, token: str) -> None:
    """Upload KLIK-Bench dataset to HF Hub."""
    api = HfApi(token=token)

    # Create repo if needed
    create_repo(repo_id, repo_type="dataset", exist_ok=True, token=token)

    base_dir = Path(__file__).resolve().parent.parent / "data"
    tasks_dir = base_dir / "tasks"
    personas_dir = base_dir / "personas"

    # Upload all YAML task files
    task_files = collect_task_files(tasks_dir)
    for yaml_file in task_files:
        api.upload_file(
            path_or_fileobj=str(yaml_file),
            path_in_repo=f"tasks/{yaml_file.name}",
            repo_id=repo_id,
            repo_type="dataset",
        )

    # Upload persona files
    persona_files = collect_task_files(personas_dir)
    for yaml_file in persona_files:
        api.upload_file(
            path_or_fileobj=str(yaml_file),
            path_in_repo=f"personas/{yaml_file.name}",
            repo_id=repo_id,
            repo_type="dataset",
        )

    # Upload metadata
    metadata_path = base_dir / "metadata.yaml"
    if metadata_path.exists():
        api.upload_file(
            path_or_fileobj=str(metadata_path),
            path_in_repo="metadata.yaml",
            repo_id=repo_id,
            repo_type="dataset",
        )

    print(f"Uploaded KLIK-Bench to https://huggingface.co/datasets/{repo_id}")


def main():
    parser = argparse.ArgumentParser(description="Upload KLIK-Bench to HuggingFace")
    parser.add_argument(
        "--repo-id",
        type=str,
        default="minervacap2022/KLIK-Bench",
        help="HuggingFace dataset repo ID",
    )
    parser.add_argument(
        "--token",
        type=str,
        required=True,
        help="HuggingFace token",
    )
    args = parser.parse_args()

    upload_benchmark(args.repo_id, args.token)


if __name__ == "__main__":
    main()
