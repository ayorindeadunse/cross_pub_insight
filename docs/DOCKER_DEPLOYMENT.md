# Docker Deployment Guide

## Quick Start with Docker

### Development Deployment

1. **Clone the repository:**
```bash
git clone https://github.com/ayorindeadunse/cross_pub_insight.git
cd cross_pub_insight
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run with Docker Compose:**
```bash
docker-compose up -d
```

4. **Check health:**
```bash
curl http://localhost:8000/health
```

### Production Deployment

1. **Build production image:**
```bash
docker build -f Dockerfile.production -t cross-pub-insight:prod .
```

2. **Run production container:**
```bash
docker run -d \
  --name cross-pub-insight-prod \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/session_store.json:/app/session_store.json \
  --restart unless-stopped \
  cross-pub-insight:prod
```

### Environment Variables

Required:
- `OPENAI_API_KEY`: OpenAI API key for LLM integration

Optional:
- `GEMINI_API_KEY`: Google Gemini API key
- `ANTHROPIC_API_KEY`: Anthropic Claude API key
- `ENVIRONMENT`: Set to 'production' for production deployment

### Health Monitoring

The container includes built-in health checks:
```bash
# Check container health
docker ps
docker inspect --format='{{.State.Health.Status}}' container_name

# View logs
docker logs cross-pub-insight-prod
```

### Scaling with Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml cross-pub-insight

# Scale service
docker service scale cross-pub-insight_api=3
```

### Troubleshooting

**Container won't start:**
- Check environment variables are set
- Verify port 8000 is available
- Check logs: `docker logs container_name`

**Health check failing:**
- Ensure all dependencies are installed
- Check if the application is binding to 0.0.0.0:8000
- Verify API keys are valid

**Performance issues:**
- Monitor resource usage: `docker stats`
- Adjust memory limits if needed
- Consider multi-worker deployment for high load