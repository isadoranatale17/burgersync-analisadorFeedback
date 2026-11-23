"""
Database Module - BurgerSync Ourinhos
Responsável por operações determinísticas de I/O no banco de dados JSON.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "feedbacks.json")

def _ensure_db_exists():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

def load_feedbacks() -> List[Dict[str, Any]]:
    _ensure_db_exists()
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[ERRO] Falha ao ler banco de dados JSON ({DB_PATH}): {str(e)}")
        return []

def save_feedback(feedback_data: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_db_exists()
    feedbacks = load_feedbacks()
    
    if "id" not in feedback_data or not feedback_data["id"]:
        feedback_data["id"] = f"fb_{uuid.uuid4().hex[:8]}"
        
    if "timestamp" not in feedback_data or not feedback_data["timestamp"]:
        feedback_data["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
    if "status" not in feedback_data:
        # Padrão: se crítico, status inicial 'pendente', caso contrário 'lida'
        feedback_data["status"] = "pendente" if feedback_data.get("sentimento") == "Crítico" else "lida"
        
    feedbacks.insert(0, feedback_data)
    
    # Gravação atômica via arquivo temporário
    temp_path = f"{DB_PATH}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, DB_PATH)
    
    print(f"[SUCESSO] Feedback registrado com sucesso: ID {feedback_data['id']} | Sentimento: {feedback_data.get('sentimento')}")
    return feedback_data

def update_feedback_status(feedback_id: str, new_status: str) -> Optional[Dict[str, Any]]:
    _ensure_db_exists()
    valid_statuses = ["pendente", "lida", "em_tratamento", "resolvida"]
    if new_status not in valid_statuses:
        raise ValueError(f"Status inválido: {new_status}. Permitidos: {valid_statuses}")
        
    feedbacks = load_feedbacks()
    updated_item = None
    
    for item in feedbacks:
        if item.get("id") == feedback_id:
            item["status"] = new_status
            item["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            updated_item = item
            break
            
    if updated_item:
        temp_path = f"{DB_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(feedbacks, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, DB_PATH)
        print(f"[SUCESSO] Status do feedback {feedback_id} alterado para '{new_status}'")
        
    return updated_item

def get_feedback_by_id(feedback_id: str) -> Optional[Dict[str, Any]]:
    feedbacks = load_feedbacks()
    for item in feedbacks:
        if item.get("id") == feedback_id:
            return item
    return None

def get_metrics() -> Dict[str, Any]:
    feedbacks = load_feedbacks()
    total = len(feedbacks)
    
    positivos = sum(1 for f in feedbacks if f.get("sentimento") == "Positivo")
    neutros = sum(1 for f in feedbacks if f.get("sentimento") == "Neutro")
    criticos = sum(1 for f in feedbacks if f.get("sentimento") == "Crítico")
    
    criticos_pendentes = sum(1 for f in feedbacks if f.get("sentimento") == "Crítico" and f.get("status") in ["pendente", "em_tratamento"])
    
    tag_counter: Dict[str, int] = {}
    for f in feedbacks:
        for t in f.get("tags", []):
            tag_counter[t] = tag_counter.get(t, 0) + 1
            
    top_tags = sorted([{"tag": k, "count": v} for k, v in tag_counter.items()], key=lambda x: x["count"], reverse=True)
    
    pct_pos = round((positivos / total * 100), 1) if total > 0 else 0.0
    pct_neu = round((neutros / total * 100), 1) if total > 0 else 0.0
    pct_cri = round((criticos / total * 100), 1) if total > 0 else 0.0
    
    media_nota = round(sum(f.get("nota", 5) for f in feedbacks) / total, 2) if total > 0 else 5.0
    
    return {
        "total": total,
        "positivos": positivos,
        "neutros": neutros,
        "criticos": criticos,
        "pct_positivos": pct_pos,
        "pct_neutros": pct_neu,
        "pct_criticos": pct_cri,
        "criticos_pendentes": criticos_pendentes,
        "media_nota": media_nota,
        "top_tags": top_tags
    }
