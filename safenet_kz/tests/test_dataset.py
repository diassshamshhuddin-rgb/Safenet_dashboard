"""
Тесты для генератора датасета и валидации данных SafeNet KZ.
"""

from pathlib import Path
import json
from src.data.generator import generate_dataset, save_dataset_files, PROJECT_ROOT


def test_dataset_generation_and_balance():
    train, val, test = generate_dataset(total_records=1200)
    
    assert len(train) == 840
    assert len(val) == 180
    assert len(test) == 180
    assert len(train) + len(val) + len(test) == 1200
    
    all_records = train + val + test
    
    tracks = set(item["track"] for item in all_records)
    assert "lottery" in tracks
    assert "casino" in tracks
    assert "pyramid" in tracks
    assert "benign" in tracks
    
    labels = set(item["label"] for item in all_records)
    assert labels == {"suspicious", "benign"}
    
    for item in all_records:
        assert item["synthetic"] is True
        if item.get("metadata", {}).get("domain"):
            assert item["metadata"]["domain"].endswith(".test")


def test_dataset_files_persistence(tmp_path):
    train, val, test = generate_dataset(total_records=100)
    # Сохраняем во временную директорию tmp_path, чтобы не перезаписывать рабочий датасет
    save_dataset_files(train, val, test, target_dir=tmp_path)
    
    assert (tmp_path / "train.jsonl").exists()
    assert (tmp_path / "val.jsonl").exists()
    assert (tmp_path / "test.jsonl").exists()
    
    with open(tmp_path / "test.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 0
        first_item = json.loads(lines[0])
        assert "id" in first_item
        assert "text" in first_item
        assert "track" in first_item