# Cross Publication Insight Assistant (CPIA) - Production Documentation

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Production Features](#production-features)
- [API Reference](#api-reference)
- [Monitoring & Observability](#monitoring--observability)
- [Deployment Guide](#deployment-guide)
- [Operations Manual](#operations-manual)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Overview

The Cross Publication Insight Assistant (CPIA) is a production-ready multi-agent system designed to analyze and compare AI/ML repositories. Built with FastAPI and LangGraph, it provides comprehensive repository analysis through intelligent agent orchestration with enterprise-grade resilience, monitoring, and security features.

### Key Capabilities
- **Multi-Repository Analysis**: Analyze and compare multiple GitHub repositories
- **AI-Powered Insights**: Local LLM integration for intelligent code analysis
- **Production Resilience**: Comprehensive retry logic, circuit breakers, and fallback mechanisms
- **Real-time Monitoring**: Health checks, metrics collection, and alerting
- **Enterprise Security**: Rate limiting, input validation, and audit logging
- **Structured Logging**: JSON-formatted logs with contextual information

## System Architecture

### Component Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Multi-Agent   │    │   LLM Client    │
│   Server        │───▶│   Orchestrator  │───▶│   (Phi-2)       │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   Repository    │    │   Resilience    │
│   System        │    │   Parser        │    │   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Agent Architecture
- **ProjectAnalyzerAgent**: Repository structure and code analysis
- **TrendAggregator**: Technology trend identification
- **ComparisonAgent**: Cross-repository comparison analysis
- **FactChecker**: Analysis verification and validation
- **SummarizeAgent**: Final insight generation
- **QueryAgent**: User query processing and response generation

## Production Features

### Phase 1: Input Validation & Security 
- **Enhanced Pydantic Models**: Strict input validation with sanitization
- **Rate Limiting**: 100 requests per hour per IP with sliding window
- **Security Headers**: XSS protection, content type validation
- **Request Size Limits**: Protection against large payload attacks
- **Input Sanitization**: SQL injection and XSS prevention

### Phase 2: Retry Logic & Resilience 
- **Exponential Backoff**: Intelligent retry with jitter to prevent thundering herd
- **Circuit Breakers**: Automatic failure detection and recovery
- **Timeout Handling**: Configurable timeouts for all operations
- **Fallback Mechanisms**: Graceful degradation when services fail
- **Service Health Checks**: Automated monitoring of component health

### Phase 3: Enhanced Logging & Monitoring 
- **Structured Logging**: JSON-formatted logs with contextual metadata
- **Performance Metrics**: Operation timing, success rates, and resource usage
- **Real-time Monitoring**: System health, alerts, and dashboards
- **Audit Trails**: Security events and compliance logging
- **Execution Metadata**: Detailed tracking of multi-agent workflows

## API Reference

### Base URL
```
http://localhost:8000
```

### Core Endpoints

#### Start Analysis
```http
POST /run-analysis/
Content-Type: application/json

{
  "primary_repo": "https://github.com/owner/repo",
  "comparison_repos": [
    "https://github.com/owner/repo2",
    "https://github.com/owner/repo3"
  ],
  "user_query": "What are the key differences in architecture?",
  "use_hitl": false
}
```

**Response:**
```json
{
  "session_id": "uuid4-string",
  "status": "processing",
  "message": "Analysis started successfully",
  "timestamp": "2025-10-27T12:00:00Z"
}
```

#### Get Analysis Results
```http
GET /results/{session_id}
```

**Response:**
```json
{
  "session_id": "uuid4-string",
  "status": "completed",
  "results": [...],
  "execution_metadata": {
    "total_duration": 45.2,
    "node_execution_times": {...},
    "retry_counts": {...},
    "failure_count": 0
  },
  "timestamp": "2025-10-27T12:01:00Z"
}
```

### Monitoring Endpoints

#### Health Check
```http
GET /health
```

#### Detailed Health Check
```http
GET /monitoring/health
```

#### Performance Metrics
```http
GET /monitoring/metrics
```

#### System Summary
```http
GET /monitoring/summary
```

#### Recent Alerts
```http
GET /monitoring/alerts
```

### OpenAPI Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Monitoring & Observability

### Health Monitoring
The system provides comprehensive health monitoring through multiple layers:

#### System Health Checks
- **Resource Usage**: CPU, memory, and disk utilization
- **Service Availability**: Component health and response times
- **Network Connectivity**: External service reachability
- **Application Health**: Agent status and LLM connectivity

#### Performance Metrics
```json
{
  "operation_metrics": {
    "api.run_analysis": {
      "total_calls": 1250,
      "successful_calls": 1201,
      "failed_calls": 49,
      "success_rate": 96.08,
      "avg_duration_ms": 2847.3,
      "retry_count": 87
    }
  }
}
```

#### Structured Logging
All operations are logged with structured JSON format:
```json
{
  "timestamp": "2025-10-27T12:00:00Z",
  "level": "INFO",
  "message": "Analysis completed successfully",
  "context": {
    "session_id": "uuid4",
    "component": "orchestrator",
    "operation": "run_analysis",
    "repo_path": "/path/to/repo"
  },
  "metrics": {
    "duration_ms": 2847.3,
    "retry_count": 2
  }
}
```

### Alerting
Automated alerts are generated for:
- **Critical Failures**: Service unavailability, data corruption
- **Performance Degradation**: High response times, resource exhaustion
- **Security Events**: Rate limit violations, invalid inputs
- **Operational Issues**: Circuit breaker trips, timeout occurrences

## Deployment Guide

### Prerequisites
- **Python 3.10+**
- **Required packages**: `pip install -r requirements.txt`
- **System resources**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB free space for models and logs

### Installation Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/ayorindeadunse/cross_pub_insight.git
   cd cross_pub_insight
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Copy and edit configuration
   cp config/config.yaml.example config/config.yaml
   
   # Set up logging directory
   mkdir -p output
   ```

4. **Download LLM Model**
   ```bash
   # Place Phi-2 model in models/ directory
   # Ensure models/phi-2.Q6_K.gguf is present
   ```

5. **Start Server**
   ```bash
   # Development
   uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
   
   # Production
   uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Production Deployment

#### Docker Deployment
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Environment Variables
```bash
# Application Configuration
CPIA_LOG_LEVEL=INFO
CPIA_RATE_LIMIT_REQUESTS=100
CPIA_RATE_LIMIT_WINDOW=3600

# Model Configuration
CPIA_MODEL_PATH=/app/models/phi-2.Q6_K.gguf
CPIA_LLM_TYPE=local

# Monitoring Configuration
CPIA_MONITORING_ENABLED=true
CPIA_HEALTH_CHECK_INTERVAL=30
```

## Operations Manual

### Daily Operations

#### Health Monitoring
```bash
# Check system health
curl -X GET "http://localhost:8000/monitoring/health"

# Get performance metrics
curl -X GET "http://localhost:8000/monitoring/metrics"

# View recent alerts
curl -X GET "http://localhost:8000/monitoring/alerts"
```

#### Log Analysis
```bash
# View structured logs
tail -f output/cpia.log | jq .

# Filter by component
grep '"component":"orchestrator"' output/cpia.log | jq .

# Monitor error rates
grep '"level":"ERROR"' output/cpia.log | jq -r .timestamp
```

### Performance Tuning

#### Memory Optimization
- **Model Loading**: Use model quantization for reduced memory usage
- **Cache Management**: Implement repository cache cleanup
- **Session Storage**: Configure session timeout and cleanup

#### Concurrency Settings
```python
# FastAPI server configuration
uvicorn api.server:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

#### Rate Limiting Configuration
```python
# Adjust based on capacity
setup_security_middleware(app, rate_limit_requests=200, rate_limit_window=3600)
```

### Backup and Recovery

#### Configuration Backup
```bash
# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz output/
```

#### Data Recovery
```bash
# Restore configuration
tar -xzf config-backup-YYYYMMDD.tar.gz

# Restore logs (if needed for analysis)
tar -xzf logs-backup-YYYYMMDD.tar.gz
```

## Troubleshooting

### Common Issues

#### High Memory Usage
**Symptoms**: System becomes unresponsive, OOM errors
**Diagnosis**:
```bash
# Check memory usage
curl -X GET "http://localhost:8000/monitoring/health" | jq .system_metrics.memory_percent
```
**Resolution**:
- Restart application to clear memory leaks
- Reduce worker processes
- Enable model quantization

#### Rate Limiting Triggered
**Symptoms**: 429 HTTP responses, API unavailable
**Diagnosis**:
```bash
# Check rate limit status
curl -X GET "http://localhost:8000/monitoring/alerts" | jq '.alerts[] | select(.message | contains("rate"))'
```
**Resolution**:
- Implement exponential backoff in clients
- Increase rate limits if legitimate traffic
- Add IP whitelist for trusted sources

#### Circuit Breaker Open
**Symptoms**: Service degradation, fallback responses
**Diagnosis**:
```bash
# Check circuit breaker status
curl -X GET "http://localhost:8000/monitoring/summary" | jq .health_checks
```
**Resolution**:
- Wait for automatic recovery (60 seconds)
- Restart affected services
- Check downstream dependencies

#### LLM Service Failures
**Symptoms**: Analysis timeouts, fallback responses
**Diagnosis**:
```bash
# Check LLM health
grep '"component":"llm"' output/cpia.log | tail -10 | jq .
```
**Resolution**:
- Verify model file integrity
- Check available memory for model loading
- Restart application if model corrupted

### Performance Issues

#### Slow Analysis Times
**Expected**: 30-60 seconds per repository
**Troubleshooting**:
1. Check system resources: `curl /monitoring/health`
2. Review repository size and complexity
3. Monitor LLM response times in logs
4. Consider repository caching

#### High Error Rates
**Threshold**: >5% failure rate
**Investigation**:
1. Review error patterns in structured logs
2. Check external service availability
3. Validate input data quality
4. Monitor retry patterns

### Log Analysis

#### Error Pattern Analysis
```bash
# Most common errors
grep '"level":"ERROR"' output/cpia.log | jq -r .message | sort | uniq -c | sort -nr

# Error trends over time
grep '"level":"ERROR"' output/cpia.log | jq -r .timestamp | cut -d'T' -f1 | sort | uniq -c
```

#### Performance Analysis
```bash
# Average operation times
grep '"metrics":' output/cpia.log | jq '.metrics.duration_ms' | awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'

# Slowest operations
grep '"metrics":' output/cpia.log | jq -r '.context.operation + ": " + (.metrics.duration_ms | tostring) + "ms"' | sort -k2 -nr | head -10
```

## Security Considerations

### Input Validation
- **URL Validation**: GitHub repository URLs only
- **Query Sanitization**: XSS and injection prevention
- **File Size Limits**: Protection against large repository attacks
- **Path Traversal**: Secure repository cloning and access

### Rate Limiting
- **IP-based Limiting**: 100 requests per hour per IP
- **Session Management**: Prevent session abuse
- **Resource Protection**: CPU and memory usage limits

### Audit Logging
- **Security Events**: Failed authentication, rate limit violations
- **Access Logs**: All API requests with user context
- **Error Tracking**: Security-related errors and exceptions
- **Compliance**: Structured logs for security analysis

### Data Protection
- **Repository Access**: Read-only operations, no data modification
- **Temporary Storage**: Automatic cleanup of cloned repositories
- **Log Retention**: Configurable retention periods
- **Sensitive Data**: No storage of user credentials or tokens

### Network Security
- **HTTPS Only**: Force secure connections in production
- **CORS Configuration**: Restrict cross-origin requests
- **Security Headers**: Comprehensive security header implementation
- **Input Filtering**: Multi-layer input validation and sanitization

---

## Support and Maintenance

### Monitoring Dashboards
- **Health Status**: Real-time component health
- **Performance Metrics**: Response times and success rates
- **Resource Usage**: System utilization trends
- **Error Analysis**: Error patterns and resolution

### Maintenance Schedule
- **Daily**: Health check review, log analysis
- **Weekly**: Performance review, capacity planning
- **Monthly**: Security audit, configuration review
- **Quarterly**: System optimization, dependency updates

### Contact Information
- **Technical Issues**: Monitor logs and health endpoints
- **Performance Questions**: Review monitoring dashboards
- **Security Concerns**: Check audit logs and alert systems

---

**CPIA v1.0.0** - Production-Ready Multi-Agent Repository Analysis System