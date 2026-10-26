"""
Скрипт объективной оценки качества и расчета метрик SafeNet KZ.
1. Подбирает оптимальный порог риска на валидационной выборке (val.jsonl).
2. Вычисляет финальные метрики на отложенной контрольной выборке (test.jsonl).
3. Считает: Precision, Recall, F1, FPR, Confusion Matrix, Precision@K, Per-Track, Per-Language.
4. Проводит Ablation Study (влияние OCR и графового анализа).
5. Сохраняет результаты в artifacts/metrics.json.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from typing import List, Dict, Any, Tuple
import numpy as np

from src.core.types import InputCase, TrackType
from src.scoring.engine import ScoringEngine
from src.graph.network import InvestigationGraph

DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(file_path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def compute_binary_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """Считает TP, FP, TN, FN, Precision, Recall, F1, FPR."""
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
    }


def tune_threshold_on_validation(val_data: List[Dict[str, Any]]) -> float:
    """Подбирает порог решения на валидационной выборке для максимизации F1 при низком FPR."""
    engine = ScoringEngine(graph=InvestigationGraph())
    scores = []
    y_true = []

    for item in val_data:
        case = InputCase(
            id=item["id"],
            text=item["text"],
            image_paths=item.get("image_paths", []),
            channel_or_account=item.get("channel_or_account", "@anon"),
            platform=item.get("platform", "telegram"),
        )
        res = engine.analyze_case(case)
        scores.append(res.score)
        y_true.append(1 if item["label"] == "suspicious" else 0)

    best_thresh = 40.0
    best_f1 = -1.0

    for thresh in np.arange(25.0, 65.0, 5.0):
        y_pred = [1 if s >= thresh else 0 for s in scores]
        m = compute_binary_metrics(y_true, y_pred)
        score_criterion = m["f1"] - (m["fpr"] * 2.0)
        if score_criterion > best_f1:
            best_f1 = score_criterion
            best_thresh = float(thresh)

    return best_thresh


def evaluate_test_dataset(
    test_data: List[Dict[str, Any]],
    threshold: float,
    use_multimodal: bool = True,
    use_graph: bool = True
) -> Dict[str, Any]:
    """Финальная оценка на test.jsonl с возможностью абляции."""
    engine = ScoringEngine(graph=InvestigationGraph())
    
    y_true = []
    y_pred = []
    scores = []
    results = []

    per_track_true = {"lottery": [], "casino": [], "pyramid": []}
    per_track_pred = {"lottery": [], "casino": [], "pyramid": []}

    per_lang_true = {"ru": [], "kk": [], "mixed_translit": []}
    per_lang_pred = {"ru": [], "kk": [], "mixed_translit": []}

    for item in test_data:
        case = InputCase(
            id=item["id"],
            text=item["text"],
            image_paths=item.get("image_paths", []),
            channel_or_account=item.get("channel_or_account", "@anon"),
            platform=item.get("platform", "telegram"),
        )
        res = engine.analyze_case(case, use_multimodal=use_multimodal, use_graph=use_graph)
        scores.append(res.score)
        results.append((res.score, item["label"] == "suspicious"))

        actual_label = 1 if item["label"] == "suspicious" else 0
        pred_label = 1 if res.score >= threshold else 0

        y_true.append(actual_label)
        y_pred.append(pred_label)

        # Разрез по трекам
        for track in ["lottery", "casino", "pyramid"]:
            t_true = 1 if item.get("track") == track else 0
            t_pred = 1 if (pred_label == 1 and res.primary_track.value == track) else 0
            per_track_true[track].append(t_true)
            per_track_pred[track].append(t_pred)

        # Разрез по языкам
        langs = res.detected_languages
        if "kk" in langs and "ru" not in langs:
            lang_cat = "kk"
        elif "translit" in langs or "mixed" in langs:
            lang_cat = "mixed_translit"
        else:
            lang_cat = "ru"

        per_lang_true[lang_cat].append(actual_label)
        per_lang_pred[lang_cat].append(pred_label)

    # 1. Общие бинарные метрики
    overall_metrics = compute_binary_metrics(y_true, y_pred)

    # 2. Метрики по трекам
    track_metrics = {}
    for track in ["lottery", "casino", "pyramid"]:
        m = compute_binary_metrics(per_track_true[track], per_track_pred[track])
        track_metrics[track] = {
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
        }

    # 3. Метрики по языкам
    lang_metrics = {}
    for lang, l_true in per_lang_true.items():
        if len(l_true) > 0:
            m = compute_binary_metrics(l_true, per_lang_pred[lang])
            lang_metrics[lang] = {
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "fpr": m["fpr"],
                "samples": len(l_true),
            }

    # 4. Precision@K (верхняя часть очереди для аналитиков)
    results.sort(key=lambda x: x[0], reverse=True)
    precision_at_k = {}
    for k in [10, 20, 50]:
        top_k = results[:k]
        prec_k = sum(1 for score, is_susp in top_k if is_susp) / len(top_k) if top_k else 0.0
        precision_at_k[f"P@{k}"] = round(prec_k, 4)

    return {
        "overall": overall_metrics,
        "per_track": track_metrics,
        "per_language": lang_metrics,
        "precision_at_k": precision_at_k,
    }


def run_full_evaluation():
    print("=" * 65)
    print(" SafeNet KZ — Автоматический расчет метрик на выборках")
    print("=" * 65)

    val_data = load_dataset(DATA_DIR / "val.jsonl")
    test_data = load_dataset(DATA_DIR / "test.jsonl")

    print(f"Загружено записей: Val={len(val_data)}, Test={len(test_data)}")

    # 1. Тюнинг порога на Val
    optimal_threshold = tune_threshold_on_validation(val_data)
    print(f"\n[Калибровка] Оптимальный порог риска (val): {optimal_threshold} баллов")

    # 2. Полный пайплайн (Full Pipeline) на Test
    full_eval = evaluate_test_dataset(test_data, optimal_threshold, use_multimodal=True, use_graph=True)

    # 3. Ablation Study
    print("\n[Ablation Study] Расчет вкладов компонентов...")
    no_graph_eval = evaluate_test_dataset(test_data, optimal_threshold, use_multimodal=True, use_graph=False)
    no_ocr_eval = evaluate_test_dataset(test_data, optimal_threshold, use_multimodal=False, use_graph=True)
    baseline_eval = evaluate_test_dataset(test_data, optimal_threshold, use_multimodal=False, use_graph=False)

    ablation_summary = {
        "Full_Pipeline": full_eval["overall"]["f1"],
        "Without_Graph": no_graph_eval["overall"]["f1"],
        "Without_OCR": no_ocr_eval["overall"]["f1"],
        "Baseline_Rules_Only": baseline_eval["overall"]["f1"],
    }

    report = {
        "dataset_info": {
            "val_samples": len(val_data),
            "test_samples": len(test_data),
            "calibrated_threshold": optimal_threshold,
        },
        "test_results_full_pipeline": full_eval,
        "ablation_study": {
            "f1_scores": ablation_summary,
            "details": {
                "full": full_eval["overall"],
                "no_graph": no_graph_eval["overall"],
                "no_ocr": no_ocr_eval["overall"],
                "baseline": baseline_eval["overall"],
            }
        },
        "limitations": [
            "Датасет синтетический; реальные паттерны могут содержать ранее неизвестный сленг.",
            "Для продакшн-внедрения требуется пилотная валидация на обезличенном потоке профильного ведомства."
        ]
    }

    metrics_path = ARTIFACTS_DIR / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nРезультаты сохранены в: {metrics_path}")

    print("\n" + "=" * 65)
    print(" РЕЗУЛЬТАТЫ НА ОТЛОЖЕННОЙ ТЕСТОВОЙ ВЫБОРКЕ (TEST SET)")
    print("=" * 65)
    ov = full_eval["overall"]
    print(f" Precision: {ov['precision'] * 100:.2f}% | Recall: {ov['recall'] * 100:.2f}% | F1: {ov['f1']:.4f}")
    print(f" False Positive Rate (FPR): {ov['fpr'] * 100:.2f}%")
    print(f" Матрица ошибок: TP={ov['tp']}, FP={ov['fp']}, TN={ov['tn']}, FN={ov['fn']}")
    print("-" * 65)
    print(" Точность в приоритетной очереди аналитика (Precision@K):")
    for k, v in full_eval["precision_at_k"].items():
        print(f"   {k}: {v * 100:.1f}%")
    print("-" * 65)
    print(" Результаты по трекам:")
    for tr, m in full_eval["per_track"].items():
        print(f"   {tr:10s} -> Precision: {m['precision']*100:.1f}%, Recall: {m['recall']*100:.1f}%, F1: {m['f1']:.3f}")
    print("-" * 65)
    print(" Результаты по языкам:")
    for lang, m in full_eval["per_language"].items():
        print(f"   {lang:14s} -> Precision: {m['precision']*100:.1f}%, Recall: {m['recall']*100:.1f}%, FPR: {m['fpr']*100:.1f}%")
    print("-" * 65)
    print(" Ablation Study (F1-score):")
    for comp, f1 in ablation_summary.items():
        print(f"   {comp:22s}: F1 = {f1:.4f}")
    print("=" * 65)


if __name__ == "__main__":
    run_full_evaluation()