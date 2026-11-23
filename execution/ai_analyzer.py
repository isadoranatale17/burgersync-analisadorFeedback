"""
AI Analyzer Module - BurgerSync Ourinhos
Responsável pela integração com a API do Google Gemini para classificação
de sentimento (Positivo, Neutro, Crítico) e extração de tags com mecanismo
de tentativas, backoff exponencial e contingência determinística local (Self-Annealing).
"""

import os
import json
import time
import re
import socket
import urllib.request
import urllib.error
from typing import Dict, Any, List

TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
LOGS_PATH = os.path.join(TMP_DIR, "request_logs.json")

def _log_request(record: Dict[str, Any]):
    os.makedirs(TMP_DIR, exist_ok=True)
    try:
        logs = []
        if os.path.exists(LOGS_PATH):
            with open(LOGS_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
        logs.append(record)
        logs = logs[-100:]
        with open(LOGS_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[AVISO] Falha ao registrar log de requisição em {LOGS_PATH}: {str(e)}")

def _fallback_deterministic_analysis(comentario: str, nota: int = 5) -> Dict[str, Any]:
    """
    Motor determinístico de contingência local quando a API externa estiver
    indisponível ou atingir limite de cota. Garante resiliência ininterrupta (Self-Annealing).
    """
    texto = (comentario or "").lower()
    
    criticos_keywords = [
        "péssimo", "horrível", "ruim", "frio", "gelado", "atraso", "demorou", "demora",
        "absurdo", "cru", "errado", "queimado", "murcha", "murcho", "nojento", "falta de respeito",
        "decepção", "nunca mais", "estragado", "sujo", "barata", "cabelo", "péssima", "incompetente",
        "demoraram", "falta", "estragada"
    ]
    
    positivos_keywords = [
        "ótimo", "ótima", "excelente", "maravilhoso", "maravilhosa", "delícia", "delicioso",
        "muito bom", "muito boa", "perfeito", "perfeita", "top", "saboroso", "suculento",
        "adoramos", "adorei", "parabéns", "rápido", "quentinho", "recomendo", "impecável"
    ]
    
    tags = set()
    if any(k in texto for k in ["entrega", "motoboy", "entregador", "demorou", "atraso", "tempo", "chegou"]):
        tags.add("Entrega")
    if any(k in texto for k in ["sabor", "lanche", "carne", "hambúrguer", "hamburguer", "ponto", "molho", "bacon", "queijo", "batata", "pão", "gostoso", "delícia", "salgado", "gorduroso"]):
        tags.add("Sabor")
    if any(k in texto for k in ["atendimento", "garçom", "garcom", "atendente", "educação", "educado", "suporte", "balcão"]):
        tags.add("Atendimento")
    if any(k in texto for k in ["frio", "gelado", "quentinho", "temperatura"]):
        tags.add("Temperatura")
    if any(k in texto for k in ["embalagem", "aberta", "amassada", "vazando", "murcha"]):
        tags.add("Embalagem")
    if any(k in texto for k in ["caro", "preço", "custo", "barato", "valor"]):
        tags.add("Preço")
    if any(k in texto for k in ["errado", "faltou", "trocado", "refrigerante errado"]):
        tags.add("Pedido Incorreto")
    if any(k in texto for k in ["higiene", "sujo", "limpeza", "cabelo"]):
        tags.add("Higiene")
        
    if not tags:
        tags.add("Geral")
        
    score_critico = sum(1 for k in criticos_keywords if k in texto)
    score_positivo = sum(1 for k in positivos_keywords if k in texto)
    
    if nota <= 2 or score_critico > score_positivo or (score_critico > 0 and nota <= 3):
        sentimento = "Crítico"
        resumo = f"Classificado como Crítico via contingência local devido a indicadores de insatisfação (Nota: {nota}, Termos críticos identificados)."
    elif nota >= 4 or score_positivo > score_critico:
        sentimento = "Positivo"
        resumo = f"Classificado como Positivo via contingência local com base em termos elogiosos e avaliação satisfatória (Nota: {nota})."
    else:
        sentimento = "Neutro"
        resumo = f"Classificado como Neutro via contingência local por conter observações moderadas ou mistas (Nota: {nota})."
        
    return {
        "sentimento": sentimento,
        "tags": list(tags),
        "detalhes_analise": resumo,
        "origem": "fallback_deterministico_local"
    }

def analyze_feedback(comentario: str, nota: int = 5, cliente_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Submete o texto do feedback à API do Google Gemini com fallback e backoff exponencial.
    Exige categorização de sentimento e extração precisa de tags.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    prompt_system = f"""Você é o analisador de feedbacks e controle de qualidade da hamburgueria artesanal 'BurgerSync Ourinhos'.
Analise o feedback deixado pelo cliente a seguir e retorne ESTRITAMENTE um objeto JSON válido, sem texto adicional nem formatação Markdown.

Nota atribuída: {nota}/5 estrelas
Comentário do cliente: "{comentario}"

O JSON de retorno deve possuir exatamente os campos:
- "sentimento": uma dentre as 3 opções: "Positivo", "Neutro" ou "Crítico" (Observação: avaliações com nota <= 2, atrasos excessivos, erros grosseiros de pedido, comida fria/estragada ou grosserias DEVEM ser "Crítico").
- "tags": lista com 1 a 4 tags temáticas (Exemplos: "Entrega", "Sabor", "Atendimento", "Temperatura", "Preço", "Embalagem", "Pedido Incorreto", "Higiene", "Qualidade").
- "detalhes_analise": resumo de 1 ou 2 frases explicando o diagnóstico e eventuais riscos.
"""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    
    if api_key:
        network_unreachable = False
        for model in models_to_try:
            if network_unreachable:
                break
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_system}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 300
                }
            }
            
            headers = {"Content-Type": "application/json"}
            data_bytes = json.dumps(payload).encode("utf-8")
            
            for attempt in range(1, 3):
                try:
                    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=4) as response:
                        if response.status == 200:
                            body = response.read().decode("utf-8")
                            res_json = json.loads(body)
                            candidate_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                            
                            if candidate_text.startswith("```"):
                                candidate_text = re.sub(r"^```(?:json)?\s*", "", candidate_text)
                                candidate_text = re.sub(r"\s*```$", "", candidate_text)
                                
                            parsed = json.loads(candidate_text)
                            
                            sentimento = parsed.get("sentimento", "Neutro")
                            if sentimento not in ["Positivo", "Neutro", "Crítico"]:
                                sentimento = "Neutro"
                                
                            result = {
                                "sentimento": sentimento,
                                "tags": parsed.get("tags", ["Geral"]),
                                "detalhes_analise": parsed.get("detalhes_analise", "Classificado com sucesso pela IA."),
                                "origem": f"gemini_api_{model}"
                            }
                            
                            print(f"[SUCESSO] Feedback analisado via {model}: {sentimento} | Tags: {result['tags']}")
                            _log_request({
                                "status": "sucesso",
                                "modelo": model,
                                "comentario": comentario,
                                "resultado": result,
                                "timestamp": time.time()
                            })
                            return result
                except urllib.error.URLError as uerr:
                    # Se falhar resolução de DNS/rede externa, não insistir repetidamente
                    if isinstance(uerr.reason, socket.gaierror) or "getaddrinfo failed" in str(uerr):
                        print(f"[AVISO] Rede externa inacessível no ambiente atual ({str(uerr.reason)}). Ativando contingência direta.")
                        network_unreachable = True
                        break
                    print(f"[AVISO] Tentativa {attempt} com {model} falhou: {str(uerr)}. Aplicando backoff...")
                    time.sleep(attempt * 1.0)
                except Exception as err:
                    print(f"[AVISO] Tentativa {attempt} com {model} falhou: {str(err)}. Aplicando backoff...")
                    time.sleep(attempt * 1.0)
                    
    # Contingência determinística ativada se a API não responder
    print("[AVISO] Ativando contingência determinística local de alta precisão (Self-Annealing).")
    fallback_res = _fallback_deterministic_analysis(comentario, nota)
    _log_request({
        "status": "fallback_local",
        "motivo": "API Gemini indisponível ou limite atingido",
        "comentario": comentario,
        "resultado": fallback_res,
        "timestamp": time.time()
    })
    return fallback_res
