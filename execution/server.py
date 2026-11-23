"""
Server Module - BurgerSync Ourinhos
Servidor Flask unificado para a API REST, página pública de feedback e dashboard administrativo.
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, send_from_directory

# Adicionar pasta raiz ao path se necessário
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, BASE_DIR)

# Carregar variáveis de ambiente do .env de forma resiliente
ENV_PATH = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

from database import (
    load_feedbacks,
    save_feedback,
    update_feedback_status,
    get_feedback_by_id,
    get_metrics
)
from ai_analyzer import analyze_feedback
from alert_service import dispatch_critical_alert, get_recent_alerts

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

@app.route("/")
def public_index():
    """Página web pública para envio de feedback pelos clientes"""
    return render_template("index.html")

@app.route("/admin")
def admin_dashboard():
    """Painel administrativo de controle de feedbacks e alertas"""
    return render_template("admin.html")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "BurgerSync Feedback Analyzer",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.route("/api/feedbacks", methods=["GET"])
def list_feedbacks():
    feedbacks = load_feedbacks()
    
    # Filtros opcionais via query parameters
    sentimento = request.args.get("sentimento")
    tag = request.args.get("tag")
    status = request.args.get("status")
    search = request.args.get("search", "").strip().lower()
    sort_by = request.args.get("sort", "recent")
    
    filtered = feedbacks
    
    if sentimento and sentimento != "Todos":
        filtered = [f for f in filtered if f.get("sentimento", "").lower() == sentimento.lower()]
        
    if tag and tag != "Todas":
        filtered = [f for f in filtered if tag.lower() in [t.lower() for t in f.get("tags", [])]]
        
    if status and status != "Todos":
        filtered = [f for f in filtered if f.get("status", "").lower() == status.lower()]
        
    if search:
        filtered = [
            f for f in filtered
            if search in f.get("nome", "").lower()
            or search in f.get("pedido_id", "").lower()
            or search in f.get("comentario", "").lower()
            or search in f.get("contato", "").lower()
        ]
        
    if sort_by == "recent":
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    elif sort_by == "oldest":
        filtered.sort(key=lambda x: x.get("timestamp", ""))
    elif sort_by == "rating_desc":
        filtered.sort(key=lambda x: x.get("nota", 0), reverse=True)
    elif sort_by == "rating_asc":
        filtered.sort(key=lambda x: x.get("nota", 0))
        
    return jsonify(filtered)

@app.route("/api/feedbacks", methods=["POST"])
def create_feedback():
    data = request.get_json() or {}
    
    nome = data.get("nome", "").strip() or "Cliente Anônimo"
    contato = data.get("contato", "").strip() or "Não informado"
    pedido_id = data.get("pedido_id", "").strip() or "N/A"
    try:
        nota = int(data.get("nota", 5))
    except (ValueError, TypeError):
        nota = 5
    nota = max(1, min(5, nota))
    
    comentario = data.get("comentario", "").strip()
    if not comentario:
        return jsonify({"erro": "O comentário do cliente é obrigatório."}), 400
        
    # Análise de IA com Gemini e fallback resiliente
    print(f"[INFO] Processando nova avaliação do pedido {pedido_id}...")
    analise = analyze_feedback(comentario, nota, {
        "nome": nome,
        "contato": contato,
        "pedido_id": pedido_id
    })
    
    sentimento = analise.get("sentimento", "Neutro")
    tags = analise.get("tags", ["Geral"])
    detalhes = analise.get("detalhes_analise", "")
    
    feedback_record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nome": nome,
        "contato": contato,
        "pedido_id": pedido_id,
        "nota": nota,
        "comentario": comentario,
        "sentimento": sentimento,
        "tags": tags,
        "detalhes_analise": detalhes,
        "status": "pendente" if sentimento == "Crítico" else "lida",
        "alerta_disparado": False
    }
    
    # Se o feedback for Crítico, dispara alerta imediato
    if sentimento == "Crítico":
        print(f"[ALERTA] Feedback Crítico detectado para o pedido {pedido_id}! Despachando notificação de crise...")
        alert_result = dispatch_critical_alert(feedback_record)
        feedback_record["alerta_disparado"] = alert_result.get("sucesso", True)
        feedback_record["alerta_detalhe"] = alert_result
        
    saved = save_feedback(feedback_record)
    return jsonify({
        "mensagem": "Feedback recebido e analisado com sucesso!",
        "feedback": saved
    }), 201

@app.route("/api/feedbacks/<feedback_id>/status", methods=["PATCH"])
def patch_status(feedback_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"erro": "Novo status não fornecido."}), 400
        
    try:
        updated = update_feedback_status(feedback_id, new_status)
        if not updated:
            return jsonify({"erro": "Feedback não encontrado."}), 404
        return jsonify(updated)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

@app.route("/api/stats", methods=["GET"])
def stats():
    metrics = get_metrics()
    return jsonify(metrics)

@app.route("/api/alerts", methods=["GET"])
def alerts():
    limit = int(request.args.get("limit", 20))
    recent = get_recent_alerts(limit=limit)
    return jsonify(recent)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Iniciando servidor BurgerSync Ourinhos na porta {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
