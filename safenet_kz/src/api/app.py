"""
FastAPI REST API для системы SafeNet KZ.
Предоставляет эндпоинты для анализа контента, работы с очередью дел,
графом связей, сбора обратной связи аналитиков и мониторинга метрик.
"""

from pathlib import Path
import json
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.types import (
    InputCase,
    AnalysisExplanation,
    AnalystDecision,
    CaseAuditRecord,
)
from src.core.config import AppConfig
from src.scoring.engine import ScoringEngine
from src.graph.network import InvestigationGraph


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
IMAGES_DIR = DATA_DIR / "images"

config = AppConfig.load()
graph = InvestigationGraph()
engine = ScoringEngine(config=config, graph=graph)

AUDIT_RECORDS: Dict[str, CaseAuditRecord] = {}


def init_demo_cases():
    """Загружает часть тестовых дел для очереди."""
    test_path = DATA_DIR / "test.jsonl"
    if not test_path.exists():
        return
    with open(test_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= 60:
                break
            if line.strip():
                item = json.loads(line)
                case = InputCase(
                    id=item["id"],
                    text=item["text"],
                    image_paths=item.get("image_paths", []),
                    channel_or_account=item.get("channel_or_account", "@anon"),
                    platform=item.get("platform", "telegram"),
                    metadata=item.get("metadata", {}),
                    synthetic=item.get("synthetic", True),
                )
                analysis = engine.analyze_case(case)
                AUDIT_RECORDS[case.id] = CaseAuditRecord(
                    case=case,
                    analysis=analysis,
                    analyst_decision=AnalystDecision.PENDING
                )


# Инициализируем при загрузке
init_demo_cases()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not AUDIT_RECORDS:
        init_demo_cases()
    yield


app = FastAPI(
    title="SafeNet KZ API",
    description="Цифровой щит против сомнительных схем в соцсетях и мессенджерах Казахстана",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FeedbackPayload(BaseModel):
    case_id: str
    decision: AnalystDecision
    comment: Optional[str] = None


@app.get("/api/v1/health")
def healthcheck():
    return {"status": "ok", "app": config.app_name, "disclaimer": config.disclaimer}


@app.post("/api/v1/analyze", response_model=AnalysisExplanation)
def analyze_content(case: InputCase):
    return engine.analyze_case(case)


@app.get("/api/v1/cases", response_model=List[CaseAuditRecord])
def get_cases(
    risk_level: Optional[str] = Query(None, description="Фильтр: Высокий / Средний / Низкий"),
    track: Optional[str] = Query(None, description="Фильтр: lottery / casino / pyramid / benign"),
    decision: Optional[str] = Query(None, description="Фильтр статуса"),
):
    records = list(AUDIT_RECORDS.values())
    if risk_level:
        records = [r for r in records if r.analysis.level.value == risk_level]
    if track:
        records = [r for r in records if r.analysis.primary_track.value == track]
    if decision:
        records = [r for r in records if r.analyst_decision.value == decision]
    
    records.sort(key=lambda x: x.analysis.score, reverse=True)
    return records


@app.post("/api/v1/feedback")
def submit_feedback(payload: FeedbackPayload):
    if payload.case_id not in AUDIT_RECORDS:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    
    record = AUDIT_RECORDS[payload.case_id]
    record.analyst_decision = payload.decision
    record.analyst_comment = payload.comment
    return {"status": "success", "case_id": payload.case_id, "saved_decision": payload.decision}


@app.get("/api/v1/graph")
def get_investigation_graph():
    return {
        "graph": graph.export_to_d3(),
        "top_clusters": graph.get_top_clusters(min_size=2),
    }


@app.get("/api/v1/metrics")
def get_system_metrics():
    metrics_path = ARTIFACTS_DIR / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Файл метрик еще не сформирован")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)