# StatPlay v0.1

SaaS de inteligência estatística esportiva com probabilidades, comparação de odds, histórico auditável, alertas Telegram/WhatsApp e camada de explicação por IA.

## Stack
- Python 3.13 / Django 5.2
- PostgreSQL 16
- Redis 7
- Celery + Celery Beat
- Docker Compose

## Módulos
- `accounts`: autenticação e usuários
- `billing`: planos PRO / PRO+
- `sports`: esportes, competições, equipes, eventos e estatísticas
- `odds`: casas, mercados e snapshots de odds
- `predictions`: versões de modelos e previsões imutáveis/auditáveis
- `alerts`: Telegram e WhatsApp
- `ai_insights`: explicações das análises
- `core`: dashboard

## Inicialização
```bash
cp .env.example .env
# Edite pelo menos DJANGO_SECRET_KEY, SUPERUSER_EMAIL e SUPERUSER_PASSWORD
docker compose up -d --build
```
Abra: http://localhost:8012

## Criar migrações na primeira execução do código
```bash
docker compose run --rm web python manage.py makemigrations accounts billing sports odds predictions alerts ai_insights
docker compose up -d --build
```

## Segurança
- Segredos somente em `.env`.
- CSRF ativo; cookies seguros fora de DEBUG.
- Sem credenciais de fornecedores no repositório.
- Previsões têm campo `locked` para preservar auditoria pré-jogo.

## Estado da v0.1
A fundação do SaaS está pronta. Os adaptadores de fontes esportivas/odds, modelo estatístico treinado, pagamento e provedores de mensagem/IA serão implementados nas próximas etapas, sem alterar a arquitetura central.
