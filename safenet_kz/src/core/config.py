"""
Загрузка и валидация конфигурации проекта SafeNet KZ.
"""

from pathlib import Path
from typing import Dict, Any
import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


class AppConfig:
    def __init__(self, config_dict: Dict[str, Any]):
        self.raw = config_dict
        self.app_name = config_dict.get("app", {}).get("name", "SafeNet KZ")
        self.disclaimer = config_dict.get("app", {}).get("disclaimer", "")
        self.risk_levels = config_dict.get("risk_levels", {})
        self.scoring = config_dict.get("scoring", {})
        self.graph = config_dict.get("graph", {})
        self.languages = config_dict.get("languages", {})

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "AppConfig":
        if not path.exists():
            raise FileNotFoundError(f"Config file not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(data)

    def get_risk_level_label(self, score: float) -> str:
        """Определяет уровень риска по скору 0..100 согласно порогам в конфиге."""
        if score >= self.risk_levels.get("high", {}).get("min_score", 70.0):
            return "Высокий"
        elif score >= self.risk_levels.get("medium", {}).get("min_score", 40.0):
            return "Средний"
        return "Низкий"