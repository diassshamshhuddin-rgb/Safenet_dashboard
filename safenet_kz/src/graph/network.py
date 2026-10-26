"""
Модуль графового анализа связей SafeNet KZ на базе NetworkX.
Выявляет организованные сети мошеннических схем:
- Общие банковские карты / телефоны переводов (shared_card, shared_phone)
- Единые домены и зеркала сайтов-прокладок (shared_domain)
- Одинаковые реферальные промокоды (shared_promocode)
- Расчет метрик центральности и графовое усиление риска (Graph Risk Boost).
"""

from typing import List, Dict, Any, Tuple, Optional
import networkx as nx
from src.core.types import GraphLinkInfo, InputCase
from src.preprocessing.pipeline import PreprocessingResult


class InvestigationGraph:
    def __init__(self, high_risk_threshold: float = 70.0):
        self.g = nx.Graph()
        self.high_risk_threshold = high_risk_threshold

    def add_case(self, case: InputCase, score: float, prep: PreprocessingResult):
        """Добавляет сущности кейса и связи в граф расследования."""
        acc_node = f"acc:{case.channel_or_account}"
        if not self.g.has_node(acc_node):
            self.g.add_node(acc_node, type="account", label=case.channel_or_account, risk=score, cases=[case.id])
        else:
            self.g.nodes[acc_node]["risk"] = max(self.g.nodes[acc_node].get("risk", 0.0), score)
            if case.id not in self.g.nodes[acc_node]["cases"]:
                self.g.nodes[acc_node]["cases"].append(case.id)

        # 1. Связи с картами
        for tail in prep.entities.get("card_tails", []):
            card_node = f"card:****{tail}"
            if not self.g.has_node(card_node):
                self.g.add_node(card_node, type="card", label=f"Карта ****{tail}", risk=score)
            else:
                self.g.nodes[card_node]["risk"] = max(self.g.nodes[card_node].get("risk", 0.0), score)
            self.g.add_edge(acc_node, card_node, relation="shared_card", weight=1.0)

        # 2. Связи с телефонами
        for phone in prep.entities.get("phones", []):
            phone_node = f"phone:{phone}"
            if not self.g.has_node(phone_node):
                self.g.add_node(phone_node, type="phone", label=phone, risk=score)
            else:
                self.g.nodes[phone_node]["risk"] = max(self.g.nodes[phone_node].get("risk", 0.0), score)
            self.g.add_edge(acc_node, phone_node, relation="shared_phone", weight=1.0)

        # 3. Связи с доменами
        for domain in prep.entities.get("domains", []):
            dom_node = f"domain:{domain}"
            if not self.g.has_node(dom_node):
                self.g.add_node(dom_node, type="domain", label=domain, risk=score)
            else:
                self.g.nodes[dom_node]["risk"] = max(self.g.nodes[dom_node].get("risk", 0.0), score)
            self.g.add_edge(acc_node, dom_node, relation="shared_domain", weight=1.0)

        # 4. Связи с промокодами
        for promo in prep.entities.get("promocodes", []):
            promo_node = f"promo:{promo}"
            if not self.g.has_node(promo_node):
                self.g.add_node(promo_node, type="promocode", label=promo, risk=score)
            else:
                self.g.nodes[promo_node]["risk"] = max(self.g.nodes[promo_node].get("risk", 0.0), score)
            self.g.add_edge(acc_node, promo_node, relation="shared_promo", weight=1.0)

    def compute_graph_boost(self, case: InputCase, prep: PreprocessingResult) -> Tuple[float, List[GraphLinkInfo]]:
        """
        Вычисляет графовое усиление риска (Graph Boost).
        Если аккаунт или его реквизиты связаны с другими аккаунтами,
        имеющими высокий риск, скор кейса увеличивается.
        """
        boost = 0.0
        links: List[GraphLinkInfo] = []
        acc_node = f"acc:{case.channel_or_account}"

        target_nodes = []
        for tail in prep.entities.get("card_tails", []):
            target_nodes.append((f"card:****{tail}", "shared_card", 20.0))
        for domain in prep.entities.get("domains", []):
            target_nodes.append((f"domain:{domain}", "shared_domain", 15.0))
        for phone in prep.entities.get("phones", []):
            target_nodes.append((f"phone:{phone}", "shared_phone", 15.0))
        for promo in prep.entities.get("promocodes", []):
            target_nodes.append((f"promo:{promo}", "shared_promo", 10.0))

        for node_id, rel_type, rel_boost in target_nodes:
            if self.g.has_node(node_id):
                node_data = self.g.nodes[node_id]
                # Проверяем соседей (другие аккаунты, использующие этот же ресурс)
                neighbors = list(self.g.neighbors(node_id))
                other_accounts = [n for n in neighbors if n != acc_node and n.startswith("acc:")]
                
                # Если ресурс уже использовался другим подозрительным аккаунтом
                if len(other_accounts) > 0 or node_data.get("risk", 0.0) >= self.high_risk_threshold:
                    max_neighbor_risk = max([self.g.nodes[a].get("risk", 0.0) for a in other_accounts] or [node_data.get("risk", 0.0)])
                    if max_neighbor_risk >= 50.0:
                        applied_boost = rel_boost * (max_neighbor_risk / 100.0)
                        boost = max(boost, applied_boost)
                        links.append(GraphLinkInfo(
                            source_entity=case.channel_or_account,
                            target_entity=node_data.get("label", node_id),
                            relation_type=rel_type,
                            weight=round(applied_boost, 1)
                        ))

        return round(boost, 1), links

    def get_top_clusters(self, min_size: int = 2) -> List[Dict[str, Any]]:
        """Возвращает связные кластеры подозрительных сетей."""
        clusters = []
        components = list(nx.connected_components(self.g))
        
        for idx, comp in enumerate(components):
            if len(comp) < min_size:
                continue
            subgraph = self.g.subgraph(comp)
            accounts = [n for n in comp if self.g.nodes[n].get("type") == "account"]
            cards = [n for n in comp if self.g.nodes[n].get("type") == "card"]
            domains = [n for n in comp if self.g.nodes[n].get("type") == "domain"]
            avg_risk = sum(self.g.nodes[n].get("risk", 0.0) for n in comp) / len(comp)
            
            clusters.append({
                "cluster_id": f"cluster_{idx + 1}",
                "total_nodes": len(comp),
                "accounts_count": len(accounts),
                "cards_count": len(cards),
                "domains_count": len(domains),
                "avg_risk_score": round(avg_risk, 1),
                "nodes": [self.g.nodes[n].get("label", n) for n in comp],
            })
            
        clusters.sort(key=lambda x: (x["avg_risk_score"], x["total_nodes"]), reverse=True)
        return clusters

    def export_to_d3(self) -> Dict[str, Any]:
        """Экспорт графа в формат D3/Cytoscape (nodes, links) для визуализации в дашборде."""
        nodes = []
        for n, d in self.g.nodes(data=True):
            nodes.append({
                "id": n,
                "label": d.get("label", n),
                "type": d.get("type", "unknown"),
                "risk": d.get("risk", 0.0),
            })
            
        links = []
        for u, v, d in self.g.edges(data=True):
            links.append({
                "source": u,
                "target": v,
                "relation": d.get("relation", "link"),
                "weight": d.get("weight", 1.0),
            })
            
        return {"nodes": nodes, "links": links}