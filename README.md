# ScamCoup — site funcional

Aplicação web educativa em **Flask + HTML/CSS + SQLite + OpenCV** para analisar indícios de golpes em mensagens, URLs e QR Codes.

## Como executar

1. Instale Python 3.10 ou superior.
2. Abra um terminal dentro desta pasta.
3. Crie um ambiente virtual: `python -m venv .venv`.
4. Ative-o: Windows `.venv\\Scripts\\activate`; macOS/Linux `source .venv/bin/activate`.
5. Instale dependências: `pip install -r requirements.txt`.
6. Inicie: `python app.py`.
7. Acesse `http://127.0.0.1:5000`.

## Páginas

- `/` — página inicial e escolha da análise
- `/analisar` — verificação de mensagem
- `/link` — verificação de URL
- `/qrcode` — envio de QR Code
- `/historico` — registros de verificações

## Deploy Render

Crie um *Web Service* Python apontando para este repositório. **Build Command**: `pip install -r requirements.txt`; **Start Command**: `gunicorn app:app`.

**Importante:** a versão atual utiliza SQLite local, cujo conteúdo pode não persistir em hospedagens com disco efêmero. Não use dados pessoais reais no histórico; o histórico do MVP é público e não há contas de usuário. Para disponibilização pública, implemente autenticação/isolamento de dados ou desative o histórico. O analisador utiliza heurísticas e **não garante** que um conteúdo classificado com risco baixo seja seguro.
