# Agentic AI Customer Support & Resolution System

An AI-powered customer support dashboard designed to help support teams analyze customer queries, retrieve relevant policies, manage support tickets, and evaluate AI-generated responses.

The project combines a local large language model (LLM), policy-based retrieval, support tools, evaluation workflows, and analytics in an interactive Streamlit dashboard.

## Key Features

- **AI Support Chat:** Generate responses to customer support queries using a local LLM.
- **Policy Retrieval:** Retrieve relevant information from the project's customer support knowledge base.
- **Ticket Management:** Create and manage support tickets using local application data.
- **Intent Detection:** Identify the likely intent behind customer queries.
- **AI Response Evaluation:** Evaluate generated responses against predefined test cases.
- **Audit Logging:** Record supported application activities for traceability.
- **Evaluation History:** Store and review previous evaluation results.
- **Performance Analytics:** View dashboard metrics related to tickets and evaluation results.
- **Safety Checks:** Reduce unsupported claims, such as stating that a refund has been approved when no such approval occurred.

## Dashboard Pages

The application includes six dashboard pages:

1. **Overview** — View key support metrics.

   ![ResolveAI Dashboard Overview](assets/dashboard-overview.png)

2. **Ticket Management** — Review and manage support tickets.
3. **Audit Log** — Inspect recorded application activities.
4. **AI Support Chat** — Interact with the AI support assistant.
5. **AI Evaluation** — Run response evaluations against a test dataset.
6. **Performance Analytics** — Review support and evaluation performance.

## Technology Stack

- **Python** — Application logic
- **Streamlit** — Interactive dashboard
- **Ollama** — Run a local language model
- **Llama 3.2 (3B)** — Local model used for response generation
- **JSON / JSONL** — Local application and evaluation data storage
- **Pytest** — Automated testing

## Architecture

```text
Customer Query
      |
      v
Streamlit Dashboard
      |
      v
Intent Detection
      |
      v
Support Agent
      |
      +--------------------+
      |                    |
      v                    v
Policy Knowledge Base   Support Tools
      |                 - Ticket Management
      |                 - Order Lookup
      |                 - Audit Logging
      +--------------------+
                 |
                 v
        Local LLM via Ollama
                 |
                 v
       Generated Support Response
                 |
                 v
       Evaluation and Analytics
```

## Project Structure

```text
agentic-customer-support/
├── app/
│   ├── agents/
│   │   ├── intent_detector.py
│   │   └── support_agent.py
│   ├── core/
│   │   └── config.py
│   ├── evaluation/
│   │   ├── evaluator.py
│   │   └── history.py
│   ├── rag/
│   │   └── knowledge_base.py
│   ├── tools/
│   │   ├── audit_log.py
│   │   ├── order_tools.py
│   │   └── ticket_tools.py
│   ├── dashboard_metrics.py
│   └── main.py
├── data/
│   ├── database/
│   ├── evaluation/
│   │   └── test_cases.json
│   └── knowledge_base/
│       ├── delivery_policy.txt
│       └── refund_policy.txt
├── tests/
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

Runtime files and generated evaluation history may be created locally and are not necessarily included in the GitHub repository.

## Getting Started

### Prerequisites

- Python 3.11 or later
- Git
- Ollama installed and running
- The `llama3.2:3b` model downloaded locally

### 1. Clone the repository

```powershell
git clone https://github.com/manojreddy2997/Agentic-AI-Customer-Support-Resolution-System.git
cd Agentic-AI-Customer-Support-Resolution-System
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Download the local language model

Make sure Ollama is installed, then run:

```powershell
ollama pull llama3.2:3b
```

### 6. Start the dashboard

From the project root, run:

```powershell
python -m streamlit run app/main.py
```

Open the local URL displayed in the terminal, usually:

```text
http://localhost:8501
```

## Running Tests

Run the automated test suite from the project root:

```powershell
python -m pytest
```

The current automated test suite contains **61 passing tests**, including regression coverage for audit logging failures. Run the command above to verify the results in your own environment.

## Continuous Integration

GitHub Actions runs the automated test suite when changes are pushed to the repository or submitted through a pull request.

The workflow is defined in `.github/workflows/tests.yml` and helps catch regressions before changes are merged.

## Current Limitations

- The application is a portfolio and demonstration project, not a production customer support platform.
- Order and ticket operations use local demonstration data rather than a live business system.
- Policy retrieval uses the project's policy knowledge base; it should not be described as embedding-based or vector-database RAG.
- The application does not perform real payments, issue actual refunds, or connect automatically to external customer service platforms.
- Generated answers should be reviewed before being used for real customer decisions.
- Ticket and audit data are stored locally, so a fresh installation may not contain existing tickets or history.

## Future Improvements

- Improve policy retrieval and evaluate retrieval relevance across a broader test dataset.
- Expand response-quality evaluation and monitoring.
- Add authenticated users and role-based access controls.
- Integrate approved external customer support systems.
- Expand regression tests for tool failures, audit logging, and safety scenarios.
- Extend CI to test multiple supported Python versions.
## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Built as a hands-on project exploring agentic AI, local LLMs, customer support automation, evaluation, and analytics.**