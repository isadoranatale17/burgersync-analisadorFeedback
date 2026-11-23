"""
Alert Service - BurgerSync Ourinhos
Responsável pelo envio de notificações críticas para a gerência via SMTP
com resiliência e fallback automático em .tmp/alerts.log.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any

TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
ALERTS_LOG_PATH = os.path.join(TMP_DIR, "alerts.log")

def _log_to_file(entry: str):
    os.makedirs(TMP_DIR, exist_ok=True)
    with open(ALERTS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry + "\n" + ("=" * 80) + "\n")

def dispatch_critical_alert(feedback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Despacha alerta crítico para o gestor.
    Se credenciais SMTP estiverem ausentes ou falharem, aciona fallback para .tmp/alerts.log.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    nome = feedback.get("nome", "Cliente Não Informado")
    contato = feedback.get("contato", "Contato Não Informado")
    pedido_id = feedback.get("pedido_id", "N/A")
    nota = feedback.get("nota", "N/A")
    comentario = feedback.get("comentario", "")
    tags = ", ".join(feedback.get("tags", []))
    resumo = feedback.get("detalhes_analise", "Avaliação classificada como crítica pela IA.")
    
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    manager_email = os.getenv("MANAGER_EMAIL", "gerencia.ourinhos@burgersync.com.br")
    
    log_content = f"""[ALERTA CRÍTICO DE CLIENTE] - {timestamp}
Restaurante: BurgerSync Ourinhos
Pedido: {pedido_id} | Nota: {nota}/5
Cliente: {nome}
Contato: {contato}
Tags Identificadas: {tags}
Resumo da IA: {resumo}
Depoimento Original do Cliente:
"{comentario}"
"""

    if smtp_host and smtp_port and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = manager_email
            msg['Subject'] = f"🚨 [CRISE URGENTE] BurgerSync Ourinhos - Pedido #{pedido_id}"

            body = f"""
            <h2>🚨 Alerta de Crise: Feedback Crítico Recebido</h2>
            <p><strong>Unidade:</strong> Ourinhos</p>
            <p><strong>Pedido ID:</strong> {pedido_id}</p>
            <p><strong>Cliente:</strong> {nome} ({contato})</p>
            <p><strong>Avaliação:</strong> {nota}/5 estrelas</p>
            <p><strong>Tags de Problema:</strong> {tags}</p>
            <hr>
            <p><strong>Diagnóstico da IA:</strong> {resumo}</p>
            <blockquote><em>"{comentario}"</em></blockquote>
            <hr>
            <p style="color: red;"><strong>Ação requerida:</strong> Entre em contato imediatamente com o cliente para contenção de crise e retenção.</p>
            """
            msg.attach(MIMEText(body, 'html'))

            port = int(smtp_port)
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, port, timeout=10)
                server.starttls()
                
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            print(f"[SUCESSO] Alerta crítico enviado via SMTP para {manager_email} referente ao pedido {pedido_id}")
            _log_to_file(f"[STATUS: ENVIADO VIA SMTP PARA {manager_email}]\n" + log_content)
            return {"status": "enviado_smtp", "destinatario": manager_email, "sucesso": True}
        except Exception as e:
            print(f"[AVISO] Falha ao enviar via SMTP ({str(e)}). Acionando fallback para .tmp/alerts.log...")
            _log_to_file(f"[STATUS: FALLBACK LOCAL - FALHA SMTP: {str(e)}]\n" + log_content)
            return {"status": "fallback_local", "erro": str(e), "sucesso": True}
    else:
        print(f"[INFO] SMTP não configurado no .env. Registrando alerta crítico em .tmp/alerts.log")
        _log_to_file("[STATUS: FALLBACK LOCAL - CREDENCIAIS SMTP NÃO DEFINIDAS]\n" + log_content)
        return {"status": "fallback_local", "sucesso": True, "detalhe": "Registrado em .tmp/alerts.log"}

def get_recent_alerts(limit: int = 20) -> list:
    """Lê as entradas recentes gravadas em .tmp/alerts.log"""
    if not os.path.exists(ALERTS_LOG_PATH):
        return []
    try:
        with open(ALERTS_LOG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            blocks = [b.strip() for b in content.split("=" * 80) if b.strip()]
            return blocks[-limit:][::-1]
    except Exception as e:
        print(f"[ERRO] Falha ao ler alertas de log: {str(e)}")
        return []
