"""
Ядро скоринга SafeNet KZ (Scoring Engine).
Объединяет извлечение признаков по трем трекам, применяет FPR-митигацию,
мультимодальный OCR скриншотов, графовый анализ связей (NetworkX),
рассчитывает интегральный балл 0-100 и формирует карточку объяснения для аналитика.
"""

from typing import List, Tuple, Optional
from src.core.types import (
    InputCase,
    AnalysisExplanation,
    RiskLevel,
    TrackType,
    EvidenceItem,
    GraphLinkInfo,
)
from src.core.config import AppConfig
from src.preprocessing.pipeline import preprocess_text, PreprocessingResult
from src.features import (
    extract_lottery_features,
    extract_casino_features,
    extract_pyramid_features,
    extract_benign_mitigation,
)
from src.multimodal.ocr_extractor import OCRExtractor
from src.graph.network import InvestigationGraph


class ScoringEngine:
    def __init__(self, config: AppConfig = None, graph: Optional[InvestigationGraph] = None):
        self.config = config or AppConfig.load()
        self.ocr_extractor = OCRExtractor()
        self.graph = graph or InvestigationGraph()

    def analyze_text(self, text: str, case_id: str = "temp") -> AnalysisExplanation:
        """Быстрый анализ чистого текста."""
        case = InputCase(
            id=case_id,
            text=text,
            channel_or_account="@unknown",
            platform="telegram"
        )
        return self.analyze_case(case)

    def analyze_case(
        self,
        case: InputCase,
        use_multimodal: bool = True,
        use_graph: bool = True
    ) -> AnalysisExplanation:
        """
        Полный мультимодальный и графовый анализ дела.
        Флаги use_multimodal и use_graph поддерживают ablation-исследования.
        """
        # 1. Мультимодальный OCR анализ скриншотов
        ocr_text = ""
        ocr_evidence: List[EvidenceItem] = []
        if use_multimodal and case.image_paths:
            ocr_text, ocr_evidence = self.ocr_extractor.process_case_images(case.image_paths)

        full_text = case.text
        if ocr_text:
            full_text = f"{case.text}\n[Текст со скриншота]: {ocr_text}".strip()

        # 2. Предобработка полного текста
        prep: PreprocessingResult = preprocess_text(full_text)

        # 3. Извлечение признаков по трекам
        lottery_items = extract_lottery_features(prep)
        casino_items = extract_casino_features(prep)
        pyramid_items = extract_pyramid_features(prep)

        # 4. Извлечение смягчающих признаков легального контента
        mitigation_discount, mitigation_items = extract_benign_mitigation(prep)

        # 5. Расчет суммарных весов по трекам
        sum_lottery = sum(item.weight for item in lottery_items)
        sum_casino = sum(item.weight for item in casino_items)
        sum_pyramid = sum(item.weight for item in pyramid_items)

        track_scores = [
            (TrackType.LOTTERY, sum_lottery),
            (TrackType.CASINO, sum_casino),
            (TrackType.PYRAMID, sum_pyramid),
        ]
        track_scores.sort(key=lambda x: x[1], reverse=True)
        primary_track, max_raw_score = track_scores[0]

        if max_raw_score <= 0.0:
            primary_track = TrackType.BENIGN

        # 6. Мультимодальное усиление
        multimodal_boost = 0.0
        if use_multimodal and ocr_text and max_raw_score > 20.0:
            multimodal_boost = 10.0
            for item in ocr_evidence:
                item.track = primary_track
                item.description = "Информация на скриншоте подтверждает признаки схемы (мультимодальное усиление)."

        # 7. Графовый анализ связей (Network Boost)
        graph_boost = 0.0
        graph_links: List[GraphLinkInfo] = []
        if use_graph:
            graph_boost, graph_links = self.graph.compute_graph_boost(case, prep)

        # 8. Итоговый скор
        raw_score = max_raw_score + multimodal_boost + graph_boost - mitigation_discount
        final_score = max(0.0, min(100.0, round(raw_score, 1)))

        if final_score < 15.0:
            primary_track = TrackType.BENIGN

        # 9. Определение уровня риска
        level_label = self.config.get_risk_level_label(final_score)
        if level_label == "Высокий":
            level = RiskLevel.HIGH
        elif level_label == "Средний":
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        # 10. Формирование перечня сработавших признаков для объяснения
        all_triggered_features: List[EvidenceItem] = []
        if primary_track == TrackType.LOTTERY:
            all_triggered_features.extend(lottery_items)
        elif primary_track == TrackType.CASINO:
            all_triggered_features.extend(casino_items)
        elif primary_track == TrackType.PYRAMID:
            all_triggered_features.extend(pyramid_items)
        else:
            all_triggered_features.extend(lottery_items + casino_items + pyramid_items)

        if use_multimodal and ocr_text and multimodal_boost > 0:
            all_triggered_features.extend(ocr_evidence)

        if use_graph and graph_boost > 0:
            all_triggered_features.append(EvidenceItem(
                feature_name="Связь в графе с ранее выявленной сетью",
                weight=graph_boost,
                snippet=f"Связи: {[f'{l.relation_type}->{l.target_entity}' for l in graph_links]}",
                track=primary_track,
                description="Аккаунт или реквизиты связаны с другими узлами, имеющими подтвержденный высокий риск."
            ))

        all_triggered_features.extend(mitigation_items)

        # Регистрируем кейс в графе для последующих связей
        if use_graph:
            self.graph.add_case(case, final_score, prep)

        return AnalysisExplanation(
            score=final_score,
            level=level,
            primary_track=primary_track,
            triggered_features=all_triggered_features,
            graph_boost=graph_boost,
            graph_links=graph_links,
            detected_languages=prep.languages,
            normalized_text=prep.cleaned_text,
            masked_text=prep.masked_text,
            disclaimer=self.config.disclaimer,
        )