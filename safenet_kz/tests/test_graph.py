"""
Тесты для модуля графового анализа связей и усиления риска (SafeNet KZ).
"""

from src.graph.network import InvestigationGraph
from src.scoring.engine import ScoringEngine
from src.core.types import InputCase, RiskLevel


def test_graph_node_and_edge_addition():
    graph = InvestigationGraph()
    engine = ScoringEngine(graph=graph)

    case1 = InputCase(
        id="case_net_01",
        text="Вложи 10 000 тг забери 30 000 тг. Перевод на карту 4400 4301 0000 8888 куратору. Мест мало!",
        channel_or_account="@pyramid_boss_1",
        platform="telegram"
    )
    res1 = engine.analyze_case(case1)
    assert res1.level == RiskLevel.HIGH

    # Проверяем наличие узлов в графе
    assert graph.g.has_node("acc:@pyramid_boss_1")
    assert graph.g.has_node("card:****8888")
    assert graph.g.has_edge("acc:@pyramid_boss_1", "card:****8888")


def test_graph_boost_on_shared_card():
    graph = InvestigationGraph()
    engine = ScoringEngine(graph=graph)

    # 1. Первый случай — явно подозрительный
    case1 = InputCase(
        id="case_net_01",
        text="Вложи 5000 тг забери 15000 тг. Оплата на карту 4400 4301 1111 7777 куратору. Гарантия 100%!",
        channel_or_account="@scam_account_alpha",
        platform="telegram"
    )
    res1 = engine.analyze_case(case1)
    assert res1.score >= 70.0

    # 2. Второй случай с другого канала, текст нейтральнее, но та же карта
    case2 = InputCase(
        id="case_net_02",
        text="Инвестиционный сбор. Перевод на карту 4400 4301 1111 7777. Успей зайти.",
        channel_or_account="@newbie_account_beta",
        platform="whatsapp"
    )
    res2 = engine.analyze_case(case2)

    # Проверяем графовый буст
    assert res2.graph_boost > 0.0
    assert len(res2.graph_links) > 0
    assert res2.graph_links[0].relation_type == "shared_card"
    assert any("графе" in f.feature_name.lower() for f in res2.triggered_features)


def test_top_clusters_and_d3_export():
    graph = InvestigationGraph()
    engine = ScoringEngine(graph=graph)

    # Создаем сеть из 3 аккаунтов вокруг одного домена
    for i in range(3):
        case = InputCase(
            id=f"case_cluster_{i}",
            text=f"🎰 Слоты занос! Зеркало https://lucky-slot777.test/play Промокод WIN{i}",
            channel_or_account=f"@streamer_node_{i}",
            platform="telegram"
        )
        engine.analyze_case(case)

    clusters = graph.get_top_clusters(min_size=2)
    assert len(clusters) >= 1
    top_c = clusters[0]
    assert top_c["total_nodes"] >= 4  # 3 аккаунта + домен + промокоды
    assert top_c["avg_risk_score"] > 0

    d3_data = graph.export_to_d3()
    assert "nodes" in d3_data
    assert "links" in d3_data
    assert len(d3_data["nodes"]) >= 4
    assert len(d3_data["links"]) >= 3