### ARIA-Autonomous-Research-Integrity-Agent- - CLAUDE.md

## Project Overview
ARIA (Autonomous Research Integrity Agent) is an AI-powered system designed to evaluate the reproducibility of scientific research papers. It analyzes papers across multiple dimensions to determine whether findings can be independently reproduced, helping to ensure the quality and integrity of published research.

## Architecture
ARIA uses a LangGraph-based orchestrator to coordinate multiple specialized agent nodes that each evaluate different aspects of a research paper:

1. **Ingestion Agent**: Processes research papers in PDF or Markdown format into a standardized text representation.
2. **Claim Extraction Agent**: Uses Gemini 2.5 Flash to extract testable scientific claims from the paper with rigorous chain-of-thought reasoning.
3. **Statistics Agent**: Evaluates statistical validity, checking for questionable research practices (QRPs) like p-hacking, HARKing, and selective reporting.
4. **Wet Lab Agent**: Verifies experimental details including reagents and protocols.
5. **Methodology Agent**: Assesses overall experimental design quality.
6. **Code Verdict Agent**: Checks for availability of code, Dockerfiles, and CI/CD pipelines.
7. **Literature Consistency Agent**: Compares claims against related publications for consistency.

The orchestrator combines results from all agents to produce a comprehensive reproducibility report.

## Configuration
- Configuration is loaded from environment variables and Google Cloud Secret Manager
- Key secrets include: GOOGLE_API_KEY, NVIDIA_NIM_KEY, GITLAB_TOKEN, TAVILY_API_KEY
- Logging is configured for both development (Rich console output) and production (Google Cloud structured logs)
- Environment is determined by the ENVIRONMENT variable (development/production)

## LLM Selection Strategy
- **Gemini 2.5 Pro**: Used for complex reasoning tasks like methodology assessment
- **Gemini 2.5 Flash**: Used for high-throughput tasks like claim extraction and statistical analysis
- **NVIDIA Nemotron-3 Super 49B**: Used for specialized reasoning tasks requiring high precision

## Data Flow
1. Input paper (PDF or Markdown) → Ingestion Agent
2. Processed text → Claim Extraction Agent
3. Extracted claims → Statistics, Wet Lab, and Methodology Agents
4. Agent results aggregated by Orchestrator → Final Reproducibility Report

## Key Components
- **Agent/state.py**: Defines the shared state schema and Pydantic models for data exchange between agents
- **Agent/model.py**: Factory functions for LLM instances with appropriate configurations
- **Agent/config.py**: Centralized configuration loader with secret management
- **Agent/prompts/**: Specialized prompt templates for each agent
- **Agent/nodes/**: Implementation of individual agent nodes
- **Agent/Tools/**: External tool integrations for ingestion and statistical analysis

## External Dependencies
- LangChain, LangGraph (orchestration)
- Google Generative AI (Gemini models)
- NVIDIA NIM (Nemotron models)
- FastAPI, Uvicorn (API server)
- Pydantic (data validation)
- SpaCy (NLP)
- SciPy, NumPy (statistical analysis)

## Usage
1. Prepare a research paper in PDF or Markdown format
2. Set environment variables including GOOGLE_API_KEY and other required secrets
3. Run the orchestrator with the paper file path
4. Receive a comprehensive reproducibility report with scores across multiple dimensions

## Development Guidelines
- Add new agent nodes in Agent/nodes/
- Create new prompts in Agent/prompts/
- Extend state schema in Agent/state.py when adding new data fields
- Use lru_cache for expensive LLM initialization
- Always validate external API keys in configuration
- Follow existing logging patterns for production readiness
- Keep agent responsibilities focused (single responsibility principle)

## Testing
- Test data located in test_data/ directory
- Use test files with known outcomes to verify agent functionality
- Each agent should have unit tests verifying its core functionality
- End-to-end tests should verify complete workflow from ingestion to final report

## Deployment
- For production deployment, use Google Cloud Secret Manager for secrets
- Configure Cloud Logging for production environment
- Containerize with Docker for consistent deployment
- Use CI/CD pipelines for automated testing and deployment

## Limitations
- Currently supports only PDF and Markdown formats
- Statistical analysis is limited to what can be inferred from text
- Code availability checks are based on metadata (repository URLs) rather than programmatic analysis
- Literature consistency assessment relies on external search capabilities

## Future Enhancements
- Support additional paper formats (e.g., Word, LaTeX)
- Implement direct code repository analysis
- Add automated verification of statistical methods
- Integrate with academic databases for better literature consistency checks
- Develop web interface for user interaction
- Implement continuous monitoring of published papers

### System Requirements
- Python 3.9+
- Environment variables for required API keys
- Internet access for LLM API calls
- Google Cloud access for Secret Manager and Cloud Logging (production)

### License
See LICENSE file for licensing information.

### Attribution
Generated with [Claude Code](https://claude.com/claude-code)