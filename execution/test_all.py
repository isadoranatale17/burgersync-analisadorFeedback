"""
Test Suite - BurgerSync Ourinhos
Validação determinística e automatizada de todos os módulos da Camada 3 e da API Flask.
"""

import os
import sys
import json
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, BASE_DIR)

from database import load_feedbacks, save_feedback, update_feedback_status, get_metrics
from alert_service import dispatch_critical_alert, get_recent_alerts, ALERTS_LOG_PATH
from ai_analyzer import analyze_feedback
from server import app

class TestBurgerSync(unittest.TestCase):
    
    def test_01_database_operations(self):
        print("\n[TEST] 1. Testando operações de banco de dados JSON...")
        sample_fb = {
            "nome": "Cliente Teste",
            "contato": "(14) 99999-0000",
            "pedido_id": "ORD-TEST-99",
            "nota": 5,
            "comentario": "Hambúrguer excelente e carne suculenta!",
            "sentimento": "Positivo",
            "tags": ["Sabor", "Qualidade"],
            "detalhes_analise": "Teste automatizado"
        }
        saved = save_feedback(sample_fb)
        self.assertIsNotNone(saved.get("id"))
        self.assertEqual(saved["status"], "lida")
        
        # Test update status
        updated = update_feedback_status(saved["id"], "resolvida")
        self.assertEqual(updated["status"], "resolvida")
        
        # Test metrics
        metrics = get_metrics()
        self.assertGreater(metrics["total"], 0)
        print(" -> Banco de dados JSON validado com sucesso!")

    def test_02_alert_service(self):
        print("\n[TEST] 2. Testando serviço de alertas e fallback...")
        sample_critical = {
            "nome": "Cliente Furioso",
            "contato": "(14) 98888-7777",
            "pedido_id": "ORD-CRIT-01",
            "nota": 1,
            "comentario": "Comida chegou fria e com atraso de duas horas!",
            "sentimento": "Crítico",
            "tags": ["Entrega", "Temperatura", "Atraso"],
            "detalhes_analise": "Gravidade alta."
        }
        result = dispatch_critical_alert(sample_critical)
        self.assertTrue(result.get("sucesso"))
        
        # Verificar se gravou no log de fallback
        self.assertTrue(os.path.exists(ALERTS_LOG_PATH))
        recent = get_recent_alerts()
        self.assertGreater(len(recent), 0)
        print(" -> Serviço de alertas e fallback em .tmp/alerts.log validado!")

    def test_03_ai_analyzer(self):
        print("\n[TEST] 3. Testando motor de análise de IA com contingência...")
        # Teste de comentário crítico
        res_crit = analyze_feedback("O hambúrguer veio queimado, horrível e totalmente frio!", nota=1)
        self.assertEqual(res_crit["sentimento"], "Crítico")
        self.assertTrue(any(t in ["Sabor", "Temperatura", "Geral"] for t in res_crit["tags"]))
        
        # Teste de comentário positivo
        res_pos = analyze_feedback("Tudo maravilhoso! Hambúrguer artesanal saboroso e entrega super rápida.", nota=5)
        self.assertEqual(res_pos["sentimento"], "Positivo")
        self.assertTrue(any(t in ["Sabor", "Entrega", "Geral"] for t in res_pos["tags"]))
        print(" -> Motor de IA e contingência determinística validados!")

    def test_04_flask_api_endpoints(self):
        print("\n[TEST] 4. Testando rotas e endpoints da aplicação Flask...")
        client = app.test_client()
        
        # Teste rota pública
        res_home = client.get("/")
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"BurgerSync Ourinhos", res_home.data)
        
        # Teste dashboard admin
        res_admin = client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"Painel de Controle", res_admin.data)
        
        # Teste API stats
        res_stats = client.get("/api/stats")
        self.assertEqual(res_stats.status_code, 200)
        data_stats = json.loads(res_stats.data)
        self.assertIn("total", data_stats)
        
        # Teste POST novo feedback via API
        payload = {
            "nome": "Mariana Souza",
            "contato": "(14) 99111-2222",
            "pedido_id": "ORD-API-55",
            "nota": 1,
            "comentario": "O motoboy foi grosseiro e o refrigerante veio vazando na sacola toda murcha!"
        }
        res_post = client.post("/api/feedbacks", json=payload)
        self.assertEqual(res_post.status_code, 201)
        data_post = json.loads(res_post.data)
        self.assertEqual(data_post["feedback"]["sentimento"], "Crítico")
        self.assertTrue(data_post["feedback"]["alerta_disparado"])
        print(" -> Rotas web e endpoints REST da API validados com 100% de sucesso!")

if __name__ == "__main__":
    unittest.main()
