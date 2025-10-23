# Kali Personal Assistant API

FastAPI backend for the Kali Personal Assistant application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Provision the knowledge graph (optional but recommended):

	Graphiti powers the assistant's long-term memory when Neo4j and an LLM provider are configured.

	- Install Neo4j 5.26+ (Neo4j Desktop or Docker) and ensure it is running.
	- Export the base credentials before starting the API:

		```bash
		export GRAPHITI_ENABLED=true
		export NEO4J_URI=bolt://localhost:7687
		export NEO4J_USER=neo4j
		export NEO4J_PASSWORD=your_password
		export GRAPHITI_GROUP_ID=optional_namespace
		export GRAPHITI_BUILD_INDICES=true  # optional, builds indices on first use
		export GRAPHITI_LLM_PROVIDER=openai  # defaults to openai when unset
		```

	- Configure an LLM provider. Only one provider needs to be active at a time; `GRAPHITI_LLM_PROVIDER` selects which
	  block to use.

	#### OpenAI (default)

	```bash
	export OPENAI_API_KEY=your_openai_api_key
	export OPENAI_MODEL=gpt-4o                             # optional override
	export OPENAI_SMALL_MODEL=gpt-3.5-turbo                 # reranker / "small" model
	export OPENAI_EMBEDDING_MODEL=text-embedding-3-small    # embedding model
	```

	#### Azure OpenAI

	```bash
	export GRAPHITI_LLM_PROVIDER=azure
	export OPENAI_API_KEY=azure_llm_key
	export AZURE_OPENAI_ENDPOINT=https://your-llm-resource.openai.azure.com/
	export AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
	export AZURE_OPENAI_API_VERSION=2024-05-01-preview
	export AZURE_OPENAI_EMBEDDING_API_KEY=azure_embedding_key
	export AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-embedding-resource.openai.azure.com/
	export AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
	export AZURE_OPENAI_EMBEDDING_API_VERSION=2024-05-01-preview
	# Optionally: export AZURE_OPENAI_USE_MANAGED_IDENTITY=true
	```

	#### Google Gemini

	```bash
	export GRAPHITI_LLM_PROVIDER=gemini
	export GOOGLE_API_KEY=your_gemini_api_key
	export GRAPHITI_GEMINI_MODEL=gemini-2.0-flash                  # optional
	export GRAPHITI_GEMINI_EMBEDDING_MODEL=embedding-001            # optional
	export GRAPHITI_GEMINI_RERANKER_MODEL=gemini-2.0-flash-exp      # optional
	```

	#### Anthropic (requires OpenAI embeddings + reranker)

	```bash
	export GRAPHITI_LLM_PROVIDER=anthropic
	export ANTHROPIC_API_KEY=your_anthropic_api_key
	export OPENAI_API_KEY=your_openai_api_key
	export ANTHROPIC_MODEL=claude-sonnet-4-20250514          # optional
	export ANTHROPIC_SMALL_MODEL=claude-3-5-haiku-20241022    # optional
	```

	#### Groq (uses OpenAI for embeddings)

	```bash
	export GRAPHITI_LLM_PROVIDER=groq
	export GROQ_API_KEY=your_groq_api_key
	export OPENAI_API_KEY=your_openai_api_key
	export GROQ_MODEL=llama-3.1-70b-versatile              # optional
	export GROQ_SMALL_MODEL=llama-3.1-8b-instant           # optional
	```

	#### Ollama (local models)

	```bash
	export GRAPHITI_LLM_PROVIDER=ollama
	export OLLAMA_BASE_URL=http://localhost:11434/v1        # defaults to this value
	export OLLAMA_MODEL=deepseek-r1:7b
	export OLLAMA_EMBEDDING_MODEL=nomic-embed-text
	export OLLAMA_EMBEDDING_DIM=768
	```

	#### OpenAI-Compatible (Mistral, Together, etc.)

	```bash
	export GRAPHITI_LLM_PROVIDER=generic
	export GENERIC_API_KEY=your_provider_api_key
	export GENERIC_BASE_URL=https://api.mistral.ai/v1       # provider-specific URL
	export GENERIC_MODEL=mistral-large-latest               # optional
	export GENERIC_SMALL_MODEL=mistral-small-latest         # optional
	export GENERIC_EMBEDDING_MODEL=mistral-embed            # optional
	```

	The first request will automatically build indices when `GRAPHITI_BUILD_INDICES=true` is set. Adjust `SEMAPHORE_LIMIT`
	(default `10`) to tune ingestion concurrency and avoid rate limits. For complete recipes, see the
	[Graphiti Quickstart](https://github.com/getzep/graphiti/tree/main/examples/quickstart).

4. Run the development server:
```bash
pnpm dev:api
# or directly:
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

5. Access the API:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Project Structure

```
apps/api/
├── src/
│   ├── main.py          # FastAPI application entry point
│   ├── routers/         # API route handlers
│   ├── models/          # Pydantic models
│   ├── services/        # Business logic
│   └── utils/           # Utility functions
├── requirements.txt     # Python dependencies
└── README.md

## Knowledge Graph Integration

- `src/services/graphiti_client.py`: Lazily instantiates the Graphiti SDK, performs hybrid fact/node searches, and
	persists agent memory updates as Graphiti episodes with optional namespacing via `GRAPHITI_GROUP_ID`. Gemini is
	supported by setting `GRAPHITI_LLM_PROVIDER=gemini` plus `GOOGLE_API_KEY`.
- `src/orchestration/memory.py`: Provides the orchestration layer with contextual snippets sourced from Graphiti when
	enabled and gracefully falls back to demo placeholders otherwise.

To tune ingestion throughput, set `SEMAPHORE_LIMIT` (default `10`) according to your LLM provider's rate limits. Graphiti
supports additional telemetry and provider toggles; consult the upstream docs for advanced configuration.
```
