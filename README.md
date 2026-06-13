# chatbot-backend

Backend de IA para la plataforma SaaS de chatbots empresariales. Construido con FastAPI (Python 3.11) y LangChain para el pipeline RAG.

## Requisitos

- Python 3.11+
- Una cuenta en [Supabase](https://supabase.com) con las credenciales del proyecto

## Configuración inicial

### 1. Clonar el repositorio

```bash
git clone https://github.com/brogrammers-tec/chatbot-backend.git
cd chatbot-backend
```

### 2. Crear el entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y rellena los valores:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://<tu-proyecto>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

> Las credenciales de Supabase las encuentras en **Project Settings → API**.

## Levantar el servidor

```bash
uvicorn app.main:app --reload
```

El servidor queda disponible en `http://localhost:8000`.

## Verificar que funciona

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

También puedes abrir la documentación interactiva en `http://localhost:8000/docs`.

## Estructura del proyecto

```
chatbot-backend/
├── app/
│   ├── main.py        # Entrada de la aplicación, CORS, rutas base
│   ├── routers/       # Endpoints organizados por dominio
│   ├── services/      # Lógica de negocio (RAG, embeddings, chat)
│   └── models/        # Schemas Pydantic
├── requirements.txt
├── .env.example
└── README.md
```

## Stack

| Capa | Tecnología |
|---|---|
| Framework | FastAPI 0.136 |
| Servidor | Uvicorn |
| RAG | LangChain + langchain-openai |
| Modelo de chat | GPT-5.4 mini (plan base) / Claude Sonnet 4.6 (plan Pro) |
| Embeddings | text-embedding-3-small |
| Base de datos | Supabase PostgreSQL + pgvector |
| PDF parsing | pypdf |
