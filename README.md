# Cross Publication Insight Assistant

**Cross Publication Insight Assistant** is a multi-agent, LLM-powered system designed to analyze, compare, and summarize trends across AI/ML GitHub repositories or research publications.

It supports deep repository parsing, LLM-based and semantic trend extraction, fact-checking, summarization, and user-defined aggregation queries such as:
- “What % of these projects use LangGraph?”
- “How do CrewAI and LangChain projects differ?”
- “Show me projects that use vector DBs.”

---


## Features

### ** Multi-Agent Architecture** using LangGraph
- **Project Analyzer Agent**: Inspects repo content and structure
- **Trend Aggregator Agent**: Extracts trends via LLM or semantic embeddings (fallback)
- **Comparison Agent**: Highlights similarities and differences
- **Fact Checker Agent**: Validates the accuracy of LLM outputs
- **Aggregate Query Agent**: Answers cross-repo questions (e.g., tool usage)
- **Summarizer Agent**: Produces human-readable insights

### ** Production-Ready API Server**
- **FastAPI Backend**: High-performance async web framework
- **Session Persistence**: Cross-restart session continuity
- **Comprehensive Monitoring**: Health checks, metrics, and alerting
- **Security Features**: Rate limiting, CORS, request validation
- **Error Resilience**: Automatic retries and graceful degradation

### ** Flexible LLM Integration**
- **OpenAI GPT-4o Mini**: Cost-effective, high-quality analysis (recommended)
- **Google Gemini**: Free tier option with excellent performance
- **Anthropic Claude**: Premium option for complex analysis
- **Local Models**: Backward compatibility support

### **⚡ Enhanced Performance**
- **20x Faster**: API-based models vs local inference (3s vs 60s)
- **Automated Processing**: HITL disabled by default for seamless operation
- **Structured Outputs**: Clean, formatted analysis results
- **Comprehensive Testing**: Unit, integration, and end-to-end validation

### **🛠️ Developer Experience**
- **Custom LLM Prompting**: Configurable templates with Jinja2 + YAML
- **Extensive Documentation**: Migration guides and production deployment docs
- **CLI Interface**: Legacy command-line support
- **Easy Extension**: Modular architecture for new features

---

## Quickstart

### 1. Configure LLM API (Required)
Choose one of the supported LLM providers:

**Option 1: OpenAI (Recommended)**
```bash
# Get API key at: https://platform.openai.com/api-keys
cp .env.example .env
echo "OPENAI_API_KEY=your-key-here" >> .env
```

**Option 2: Google Gemini (Free Tier)**
```bash
# Get API key at: https://aistudio.google.com/app/apikey
cp .env.example .env  
echo "GEMINI_API_KEY=your-key-here" >> .env
```

**Option 3: Anthropic Claude**
```bash
# Get API key at: https://console.anthropic.com/
cp .env.example .env
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the API Server
```bash
python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

### 4. Access the Application
- **API Documentation**: http://127.0.0.1:8000/docs (Swagger UI)
- **Health Check**: http://127.0.0.1:8000/health
- **API Base**: http://127.0.0.1:8000

##  API Endpoints

### **Core Analysis**
- `POST /analysis` - Submit repository analysis request
- `GET /results/{session_id}` - Retrieve analysis results
- `GET /health` - Basic health check

### **Monitoring & Diagnostics**
- `GET /monitoring/health` - Detailed health status
- `GET /monitoring/metrics` - System performance metrics
- `GET /monitoring/summary` - Operational summary
- `GET /monitoring/alerts` - Active alerts and warnings

### **Testing**
Run the comprehensive test suite:
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# API endpoint tests
python test_api.py
python test_endpoints.py
python test_security.py
python test_resilience.py
```

## CLI Usage (Legacy)
```bash
python3 main.py <primary_repo> <comparison_repo1> [comparison_repo2 ...] --query "What % use LangGraph?"
```

### Options
- `--query`: (Optional) Ask a cross-repository question
- `--hitl`: (Optional) Enable human-in-the-loop intervention (disabled by default)

### Examples
```bash
# Basic repository comparison
python3 main.py https://github.com/user/project-a https://github.com/user/project-b

# With custom query
python3 main.py https://github.com/user/project-a https://github.com/user/project-b --query "Which uses vector databases?"

# Enable manual review step
python3 main.py https://github.com/user/project-a https://github.com/user/project-b --hitl
```

**Note**: The CLI interface is now legacy. The recommended approach is using the FastAPI server with the Blazor UI for a better user experience.


## Project Structure
```
cross_pub_insight/
├── 📁 agents/                     # Multi-agent system components
│   ├── project_analyzer.py        # Repository content analysis
│   ├── llm_trend_agent.py         # LLM-based trend extraction
│   ├── trend_aggregator.py        # Trend aggregation logic
│   ├── comparison_agent.py        # Cross-repository comparison
│   ├── fact_checker.py            # AI output validation
│   ├── aggregate_query_agent.py   # Cross-repo query processing
│   └── summarize_agent.py         # Final summary generation
│
├── 📁 api/                        # FastAPI web server
│   ├── server.py                  # Main API endpoints & orchestration
│   ├── models.py                  # Pydantic request/response models
│   ├── security.py               # Authentication & rate limiting
│   └── __init__.py
│
├── 📁 tools/                      # Supporting utilities
│   ├── semantic_trend_detector.py # Embedding-based trend detection
│   ├── repo_parser.py             # Repository content parsing
│   ├── comparison_tool.py         # Repository comparison logic
│   └── hitl_intervention.py       # Human-in-the-loop prompts
│
├── 📁 orchestrator/
│   └── orchestrator.py            # LangGraph workflow orchestration
│
├── 📁 llm/                        # LLM client abstractions
│   └── client.py                  # OpenAI, Gemini, Claude, Local clients
│
├── 📁 config/                     # Configuration management
│   ├── config.yaml               # Main application settings
│   └── prompts/                  # LLM prompt templates
│       ├── analyzer_prompt.txt
│       ├── fact_checker_prompt.txt
│       ├── llm_trend_extractor.txt
│       ├── aggregate_query.txt
│       └── summarize_project.txt
│
├── 📁 utils/                      # Shared utilities
│   ├── config_loader.py          # Configuration management
│   ├── logger.py                 # Structured logging
│   ├── resilience.py             # Error handling & retries
│   ├── resilient_llm.py          # LLM client with fallbacks
│   ├── resilient_orchestrator.py # Orchestrator with error handling
│   ├── simple_monitoring.py      # Basic health monitoring
│   ├── structured_logger.py      # Advanced logging utilities
│   ├── comparison.py             # Repository comparison utilities
│   ├── repo_utils.py             # Repository processing helpers
│   └── malformed_readme_detector.py # README quality detection
│
├── 📁 tests/                      # Comprehensive test suite
│   ├── conftest.py               # Pytest configuration
│   ├── unit/
│   │   └── test_server_unit.py   # Unit tests for API server
│   └── integration/
│       └── test_server_integration.py # End-to-end API tests
│
├── 📁 output/                     # Generated analysis outputs
│
├── 📄 Core Files
├── main.py                       # CLI interface (legacy)
├── session_store.json            # Persistent session storage
├── requirements.txt              # Python dependencies
├── requirements.in               # Dependency source file
├── pytest.ini                   # Test configuration
│
├── 📄 API Testing
├── test_api.py                   # API endpoint tests
├── test_endpoints.py             # Endpoint validation tests
├── test_resilience.py            # Error handling tests
├── test_security.py              # Security feature tests
│
├── 📄 Configuration & Environment
├── .env.example                  # Environment template
├── .env                         # Local environment variables (gitignored)
├── .gitignore                   # Git ignore patterns
│
├── 📄 Documentation
├── README.md                    # This file
├── LICENSE.md                   # Project license
├── LLM_MIGRATION_GUIDE.md       # OpenAI migration guide
├── PRODUCTION_DOCUMENTATION.md  # Production deployment guide
└── cpia_module_3.txt            # Additional documentation
```


## Technology Stack

**Core Framework:**
- **LangGraph** - Multi-agent workflow orchestration
- **FastAPI** - High-performance async web framework
- **Pydantic** - Data validation and serialization

**LLM Integration:**
- **OpenAI GPT-4o Mini** (Primary) - Cost-effective, high-quality analysis
- **Google Gemini 1.5 Flash** - Free tier option with excellent performance
- **Anthropic Claude 3.5 Haiku** - Premium option for complex analysis
- **Local Models** - Backward compatibility (llama-cpp-python)

**AI/ML Components:**
- **SentenceTransformers** (all-MiniLM-L6-v2) - Semantic embeddings for fallback trend detection
- **Structured Prompting** - Jinja2 templated prompts with YAML configuration

**Production Features:**
- **Session Persistence** - JSON-based session storage with cross-restart continuity
- **Comprehensive Testing** - Unit, integration, and API endpoint validation
- **Security Middleware** - Rate limiting, CORS, request validation
- **Monitoring & Logging** - Health checks, structured logging, error tracking
- **Resilience** - Automatic retries, fallback mechanisms, graceful degradation

## Configuration

### **Environment Setup**
Configure your LLM provider in `.env`:
```bash
# Primary configuration (choose one)
OPENAI_API_KEY=your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here
ANTHROPIC_API_KEY=your-claude-key-here
```

### **Application Settings**
Edit `config/config.yaml` to customize:

```yaml
# LLM Configuration
llm:
  model_name: "gpt-4o-mini"        # OpenAI model
  type: "openai"                   # Provider: openai, gemini, anthropic
  temperature: 0.2                 # Response creativity
  context_window: 128000           # Token limit

# Human-in-the-Loop
hitl:
  enabled: false                   # Auto-run without prompts
  step: "pre-summary"             # When to intervene

# Repository Processing
repo_parser:
  max_readme_excerpt_chars: 500   # README processing limit
  num_keywords: 10                 # Keyword extraction count

# Embeddings (Fallback)
embeddings:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  top_k: 5                        # Top similar results
  score_threshold: 0.4            # Similarity threshold
```

### **API Configuration**
- **Default Port**: 8000
- **CORS**: Configured for localhost development
- **Rate Limiting**: Disabled for development (configurable)
- **Session Storage**: `session_store.json`

