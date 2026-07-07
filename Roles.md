# Senior Expert Engineer Roles for FRONTLINE AI Triage System

This document outlines the specialized roles required to build, maintain, and enhance the FRONTLINE AI Customer Support Triage System. Each role represents a domain of expertise needed to successfully deliver all three levels of the challenge.

## 1. AI/ML Engineer (LLM & Prompt Engineering Specialist)
**Primary Focus:** Core AI/triage logic, prompt engineering, model selection, and uncertainty handling

### Responsibilities:
- Design and refine the hardened two-part prompt system (system prompt + user prompt)
- Implement and validate security rules against prompt injection and adversarial inputs
- Optimize model selection (GPT-4o-mini vs Gemini 1.5 Flash) based on cost/latency/accuracy tradeoffs
- Implement confidence scoring and uncertainty handling (confidence < 0.6 → needs_human: true)
- Design and implement the validation layer that sanitizes and corrects LLM outputs
- Handle edge cases: multi-issue messages, non-English inputs, garbage input, adversarial attempts
- Implement fallback mechanisms for LLM API failures
- Optimize token usage and latency through prompt engineering
- Experiment with few-shot examples vs. zero-shot approaches

### Key Files to Own:
- `src/triage/engine.py` (especially SYSTEM_PROMPT, validation logic)
- `src/triage/processor.py` (LLM calling logic)
- `tests/test_engine.py` (validation test cases)

### Required Expertise:
- Advanced prompt engineering techniques
- LLM security and prompt injection defense
- Structured output parsing and validation
- Uncertainty quantification and calibration
- Cost-latency-accuracy tradeoff analysis
- Experience with OpenAI API and/or Google Gemini API

## 2. Backend Engineer (Python Systems Architect)
**Primary Focus:** Core processing pipeline, batch processing, error handling, and system reliability

### Responsibilities:
- Design and maintain the batch processing pipeline (`processor.py`)
- Implement rate limiting, retry logic, and exponential backoff for API calls
- Build robust error handling and fallback mechanisms
- Design extensible architecture for adding new LLM providers
- Implement logging, monitoring, and observability
- Optimize batch processing performance (batching, caching, async processing)
- Ensure fault tolerance and graceful degradation
- Implement proper state management for resumable processing

### Key Files to Own:
- `src/triage/processor.py` (core processing logic)
- `main.py` (orchestration and CLI handling)
- Error handling and logging systems
- Batch processing optimizations

### Required Expertise:
- Advanced Python programming (typing, async patterns, error handling)
- API client design and rate limiting
- Batch processing systems
- Fault tolerance and resilience patterns
- Logging and monitoring best practices
- CLI application design (argparse, etc.)

## 3. Frontend Engineer (Web Dashboard Developer)
**Primary Focus:** Level 3 UI implementation - CLI dashboard and web dashboard

### Responsibilities:
- Build and maintain the Rich-based CLI table viewer (`src/ui/cli.py`)
- Develop and maintain the Flask-based web dashboard (`src/ui/app.py`)
- Design responsive, accessible UI components
- Implement real-time data visualization (charts, stats, filtering)
- Create dark-mode compatible interfaces
- Implement search, filter, and sorting capabilities
- Develop mobile-responsive dashboard views
- Implement error boundaries and loading states

### Key Files to Own:
- `src/ui/cli.py` (Rich terminal interface)
- `src/ui/app.py` (Flask web application)
- `src/ui/templates/dashboard.html` (HTML template)
- Static assets (CSS, JS if needed)

### Required Expertise:
- Python web frameworks (Flask)
- Rich library for terminal UIs
- HTML5, CSS3, modern JavaScript
- Responsive design principles
- Data visualization concepts
- RESTful API design and consumption
- Template engines (Jinja2)

## 4. DevOps/Infrastructure Engineer
**Primary Focus:** Deployment, configuration, environment management, and reproducibility

### Responsibilities:
- Manage environment configuration (.env.example → .env)
- Dependency management and version locking (requirements.txt)
- Containerization readiness (Dockerfile preparation)
- CI/CD pipeline design (GitHub Actions, etc.)
- Environment variable management and security
- Logging configuration and log rotation
- Performance monitoring and profiling setup
- Dependency vulnerability scanning
- Build and release automation

### Key Files to Own:
- `.env.example` and environment configuration
- `requirements.txt` (dependency management)
- Dockerfile creation (for future containerization)
- CI/CD pipeline configuration
- Logging configuration optimization
- Performance benchmarking scripts

### Required Expertise:
- Python packaging and dependency management
- Environment configuration best practices
- CI/CD pipeline design
- Containerization concepts (Docker)
- Monitoring and observability tools
- Security scanning for dependencies

## 5. QA/Test Engineer (Quality & Reliability Focus)
**Primary Focus:** Testing strategy, validation, evaluation metrics, and quality assurance

### Responsibilities:
- Design and maintain unit test suite (`tests/test_engine.py`)
- Develop comprehensive test cases for edge cases and adversarial inputs
- Implement and maintain evaluation framework (`evaluation/evaluate.py`)
- Create and maintain gold-standard datasets (ground truth)
- Design metrics for accuracy, precision, recall by category/priority
- Implement regression testing suites
- Create chaos engineering tests for failure scenarios
- Develop performance benchmarking and load testing
- Validate safety and security properties

### Key Files to Own:
- `tests/test_engine.py` (unit tests)
- `evaluation/evaluate.py` (evaluation metrics)
- `evaluation/ground_truth.json` (gold standard data)
- Test data generation and validation scripts
- Property-based testing for edge cases

### Required Expertise:
- Software testing methodologies (unit, integration, property-based)
- Machine learning evaluation metrics
- Test data generation and curation
- Adversarial testing techniques
- Performance and load testing
- Quality gate definition and enforcement

## 6. Product Engineer / Technical Lead
**Primary Focus:** End-to-end product vision, architecture decisions, and cross-cutting concerns

### Responsibilities:
- Define and maintain overall system architecture
- Make technology stack decisions (LLM providers, frameworks)
- Balance Level 1, 2, and 3 requirements trade-offs
- Ensure security-first mindset throughout the system
- Drive documentation quality (README, AI Decisions note)
- Coordinate cross-functional dependencies
- Make product-level trade-off decisions (cost vs accuracy vs latency)
- Ensure compliance with requirements specification
- Mentor junior engineers and conduct code reviews

### Key Files to Own:
- Overall architecture decisions
- README.md (main documentation)
- AI Decisions section in README
- System design documents
- Cross-cutting concerns (security, performance, usability)

### Required Expertise:
- System architecture and design patterns
- Product thinking and trade-off analysis
- Technical leadership and mentorship
- Requirements traceability
- Documentation excellence
- AI product sense

## 7. Security Engineer (Prompt Injection & AI Safety Specialist)
**Primary Focus:** AI safety, prompt injection defense, and secure LLM usage

### Responsibilities:
- Design and validate prompt injection defenses
- Implement and test system prompt integrity protections
- Create adversarial test cases for jailbreak attempts
- Ensure no information leakage via side channels
- Validate that the system never takes actions (only classifies)
- Implement output sanitization to prevent data leakage
- Design defense-in-depth for LLM interactions
- Conduct red-team exercises against the system
- Monitor for emerging LLM attack vectors

### Key Files to Own:
- `src/triage/engine.py` (SYSTEM_PROMPT security rules)
- Adversarial test case creation and validation
- Security testing frameworks
- Input sanitization and validation layers
- Output encoding and safe display practices

### Required Expertise:
- LLM security and prompt injection vulnerabilities
- Adversarial machine learning
- AI safety principles
- Secure coding practices for LLM applications
- Threat modeling for LLM systems
- OWASP LLM Top 10 knowledge

## 8. Data Engineer (Data Pipeline & Message Processing)
**Primary Focus:** Message dataset handling, preprocessing, and language detection

### Responsibilities:
- Design and maintain message data pipeline
- Implement language detection and handling (non-English messages)
- Create data validation and cleaning pipelines
- Implement message deduplication and caching strategies
- Design multi-issue message handling and decomposition
- Create data augmentation strategies for edge cases
- Implement data versioning and lineage tracking
- Optimize data storage and retrieval performance

### Key Files to Own:
- Data processing enhancements in `processor.py`
- Language detection integration (using langdetect)
- Message preprocessing and normalization
- Caching mechanisms for repeated messages
- Data validation schemas

### Required Expertise:
- Data pipeline design and ETL processes
- Natural language processing basics (language detection)
- Data validation and sanitization
- Caching strategies (Redis, memoization)
- Data versioning and lineage
- Performance optimization for data processing

## Cross-Cutting Responsibilities for All Senior Engineers:

### 1. Code Quality & Maintainability
- Write clean, readable, well-documented code
- Follow established code style and patterns in the repository
- Write meaningful commit messages and PR descriptions
- Conduct thorough code reviews with constructive feedback
- Maintain and improve existing test coverage

### 2. Documentation Excellence
- Keep README and documentation up-to-date with changes
- Document architectural decisions and trade-offs
- Create runbooks for common operations and troubleshooting
- Document API contracts and data schemas
- Maintain knowledge sharing through code comments

### 3. Security Consciousness
- Follow security best practices in all code
- Validate and sanitize all inputs and outputs
- Never trust user input or LLM outputs without validation
- Report security concerns immediately
- Stay updated on emerging security threats

### 4. Performance Awareness
- Consider performance implications of all changes
- Profile and optimize critical paths when needed
- Consider memory usage and garbage collection impact
- Implement efficient algorithms and data structures
- Monitor and optimize external API usage costs

### 5. Testing Mindset
- Write tests for new functionality and bug fixes
- Ensure tests are maintainable and readable
- Follow testing best practices (arrange-act-assert)
- Test edge cases and failure modes
- Participate in improving test infrastructure

## Level-Specific Responsibilities:

### For Level 1 (Basic Functionality):
- All engineers ensure core functionality works without crashing
- Focus on basic message processing and JSON output generation
- Ensure end-to-end pipeline runs successfully on the dataset

### For Level 2 (Reliability & Safety):
- AI/ML Engineer: Focus on uncertainty handling and security
- QA/Test Engineer: Focus on adversarial testing and edge cases
- Security Engineer: Focus on prompt injection defense
- All engineers: Focus on error handling and graceful degradation

### For Level 3 (Provability & Polish):
- Product Engineer: Focus on evaluation framework and metrics
- Data Engineer: Focus on ground truth creation and validation
- Frontend Engineer: Focus on polished UI/UX experiences
- All engineers: Focus on documentation, observability, and polish

## Collaboration Patterns:

### Daily Practices:
- Daily standups to sync on progress and blockers
- Pair programming on complex components
- Regular code reviews with constructive feedback
- Shared ownership of code quality and technical debt

### Decision Making:
- Architecture decisions made collectively with Tech Lead input
- Technical spikes for exploring new approaches
- Data-driven decisions based on metrics and measurements
- Consensus-driven with clear escalation paths

### Knowledge Sharing:
- Weekly tech talks on relevant topics
- Brown bag sessions on lessons learned
- Documentation of learned lessons and best practices
- Mentoring and skill sharing across specialties

This structure ensures that all aspects of the FRONTLINE system receive expert attention while maintaining clear ownership and accountability. Each role brings specialized expertise that contributes to building a robust, secure, and high-quality AI triage system worthy of unsupervised operation in a production customer support environment.