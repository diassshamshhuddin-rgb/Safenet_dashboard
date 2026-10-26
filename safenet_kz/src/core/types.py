"""
Типы данных и Pydantic-модели для системы SafeNet KZ.
Строго соблюдается принцип формулировок: только «признаки», «возможные схемы» и «требует проверки».
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TrackType(str, Enum):
    LOTTERY = "lottery"       # Платные розыгрыши / лотереи
    CASINO = "casino"         # Скрытое онлайн-казино
    PYRAMID = "pyramid"       # Финансовые пирамиды
    BENIGN = "benign"         # Легальный контент


class RiskLevel(str, Enum):
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"


class AnalystDecision(str, Enum):
    PENDING = "Ожидает проверки"
    CONFIRMED_SIGNS = "Подтвердить наличие признаков"
    FALSE_POSITIVE = "Ложное срабатывание"
    NEEDS_ADDITIONAL_INFO = "Требуется дополнительная проверка"


class EvidenceItem(BaseModel):
    """Единичный сработавший признак с объяснением."""
    feature_name: str = Field(..., description="Название признака (например: Оплата за участие)")
    weight: float = Field(..., description="Вклад признака в итоговый балл (от 0 до 100)")
    snippet: str = Field(..., description="Цитата или фрагмент, вызвавший срабатывание")
    track: TrackType = Field(..., description="К какому треку относится данный признак")
    description: str = Field("", description="Пояснение для модератора")


class GraphLinkInfo(BaseModel):
    """Связь в графе аккаунтов / реквизитов."""
    source_entity: str
    target_entity: str
    relation_type: str  # 'shared_card', 'shared_domain', 'shared_promocode', 'repost_chain'
    weight: float = 1.0


class InputCase(BaseModel):
    """Входной случай для анализа."""
    id: str
    text: str
    image_paths: List[str] = Field(default_factory=list)
    channel_or_account: str
    platform: str = "telegram"  # 'telegram', 'whatsapp', 'instagram', 'tiktok'
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    synthetic: bool = True


class AnalysisExplanation(BaseModel):
    """Полный объяснительный слой решения."""
    score: float = Field(..., ge=0.0, le=100.0, description="Интегральный скор риска 0-100")
    level: RiskLevel = Field(..., description="Категория риска: Низкий / Средний / Высокий")
    primary_track: TrackType = Field(..., description="Преобладающий трек выявленных признаков")
    triggered_features: List[EvidenceItem] = Field(default_factory=list)
    graph_boost: float = 0.0
    graph_links: List[GraphLinkInfo] = Field(default_factory=list)
    detected_languages: List[str] = Field(default_factory=list)
    normalized_text: str = ""
    masked_text: str = ""
    disclaimer: str = (
        "Система выявляет признаки возможного нарушения. Окончательное решение "
        "принимает аналитик в соответствии с законодательством Республики Казахстан."
    )


class CaseAuditRecord(BaseModel):
    """Запись дела с результатами скоринга и решением аналитика."""
    case: InputCase
    analysis: AnalysisExplanation
    analyst_decision: AnalystDecision = AnalystDecision.PENDING
    analyst_comment: Optional[str] = None
    reviewed_at: Optional[str] = None