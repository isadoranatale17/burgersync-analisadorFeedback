# 🍔 BurgerSync Ourinhos - Analisador Inteligente de Feedbacks

Sistema web completo para coleta, análise de sentimento com IA (Google Gemini) e gestão em tempo real de avaliações dos clientes da hamburgueria artesanal **BurgerSync** na unidade de Ourinhos/SP.

---

## 🏛️ Arquitetura em 3 Camadas

O sistema é construído estritamente seguindo o padrão de 3 camadas especificado na diretiva do projeto:

1. **Layer 1 (Diretiva):** `directive/projeto.md` — Regras de negócio, critérios de classificação de sentimento e protocolos de contenção de crise.
2. **Layer 2 (Orquestração):** Coordenação de fluxo entre submissões web públicas, processamento assíncrono de IA e acionamento de alertas.
3. **Layer 3 (Execução):** Scripts determinísticos e modulares em Python localizados na pasta `execution/`:
   - `execution/database.py`: Operações atômicas de I/O no banco de dados JSON estruturado (`data/feedbacks.json`).
   - `execution/ai_analyzer.py`: Integração com Gemini API (`gemini-3.6-flash`), tentativas com backoff exponencial e motor de contingência determinístico local (**Self-Annealing**).
   - `execution/alert_service.py`: Disparo de e-mails via SMTP com fallback automático e resiliente em `.tmp/alerts.log`.
   - `execution/server.py`: Servidor unificado Flask servindo tanto a API REST quanto as interfaces públicas e administrativas.
   - `execution/test_all.py`: Bateria completa de testes automatizados com cobertura de banco de dados, alertas, IA e endpoints.

---

## 🚀 Funcionalidades Principais

- **Página Web Pública para Clientes (`/`):**
  - Interface responsiva com tema escuro e detalhes artesanais.
  - Campos: Nome, WhatsApp/E-mail, Número do Pedido, Avaliação em Estrelas (1 a 5) e Comentário.
  - Feedback em tempo real com indicador de processamento por IA.

- **Classificação Inteligente com Gemini e Self-Annealing:**
  - Classificação de sentimento: **Positivo**, **Neutro** ou **Crítico**.
  - Extração automática de tags temáticas: *Entrega, Sabor, Atendimento, Temperatura, Embalagem, Preço, Higiene, Pedido Incorreto*.
  - Contingência local determinística que garante operação ininterrupta mesmo se a rede externa ou cota estiver indisponível.

- **Sistema de Alerta Automático de Crises:**
  - Identificação imediata de clientes insatisfeitos (sentimento Crítico).
  - Despacho de alerta por e-mail ou gravação estruturada com prioridade em `.tmp/alerts.log`.

- **Painel Administrativo de Gestão (`/admin`):**
  - Cartões de KPI com cálculo em tempo real: Total de feedbacks, % Positivos, % Neutros, % Críticos, Pendências Críticas e Média Geral de Estrelas.
  - Banner pulsante de crise alertando a gerência sobre reclamações pendentes.
  - Filtros interativos por Sentimento e Status (*Pendente, Lida, Em Tratamento, Resolvida*).
  - Busca instantânea e ordenação dinâmica por data ou nota.
  - Visualizador completo dos logs de alertas gerenciais.

---

## 🛠️ Como Executar Localmente

### 1. Pré-requisitos
- Python 3.12+ instalado

### 2. Instalação das Dependências
```bash
pip install -r requirements.txt
```

### 3. Configuração do `.env`
Crie ou edite o arquivo `.env` na raiz do projeto:
```env
GEMINI_API_KEY=sua_chave_gemini_aqui
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@empresa.com
SMTP_PASSWORD=sua_senha_ou_app_password
MANAGER_EMAIL=gerente@burgersync.com.br
PORT=5000
```
> *Nota: Se as variáveis SMTP não forem preenchidas, o sistema automaticamente operará em modo de contingência, gravando os alertas em `.tmp/alerts.log` sem interromper o serviço.*

### 4. Executando o Servidor
```bash
python execution/server.py
```
- Acesse a página do cliente em: `http://localhost:5000/`
- Acesse o painel administrativo em: `http://localhost:5000/admin`

### 5. Executando os Testes Automatizados
```bash
python execution/test_all.py
```

---

## ☁️ Deploy em Nuvem (Render / Docker)

O projeto inclui arquivos prontos para deploy contínuo:
- `Dockerfile`: Container pronto para produção.
- `render.yaml` e `Procfile`: Configuração de 1 clique para Render ou plataformas compatíveis.
