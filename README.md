# Agentic AI Customer Support & Resolution System

An AI-powered customer support application that identifies customer intent, retrieves relevant policies, checks order information, and assists with support-ticket creation.

## Features

- **Intent Detection:** Classifies customer queries.
- **Policy Retrieval (RAG):** Searches local refund and delivery policies.
- **Order Lookup:** Retrieves information from sample order records.
- **Ticket Management:** Creates support tickets for supported issues.
- **Local LLM:** Uses Ollama with the `llama3.2:3b` model.
- **Controlled Responses:** Uses available evidence and avoids claiming unverified refunds or actions.
- **Automated Tests:** Includes tests for intent detection and support-agent behavior.

## Architecture

```text
Customer Message
       |
       v
Intent Detection
       |
       v
Support Agent
       |
       +----> Policy Knowledge Base
       |
       +----> Order Lookup Tools
       |
       +----> Ticket Management Tools
       |
       v
Response Generation
       |
       v
Customer Response
```

## Technology Stack

- Python
- Streamlit
- Ollama
- Llama 3.2 (3B)
- Retrieval-Augmented Generation (RAG)
- JSON sample data
- Pytest

## Project Structure

```text
agentic-customer-support/
|-- app/
|   |-- agents/
|   |-- rag/
|   |-- tools/
|   `-- main.py
|-- data/
|   |-- database/
|   `-- knowledge_base/
|-- tests/
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Prerequisites

- Python 3.11 or compatible version
- Git
- Ollama

## Setup on Windows

### 1. Clone the repository

```powershell
git clone https://github.com/manojreddy2997/Agentic-AI-Customer-Support-Resolution-System.git
cd Agentic-AI-Customer-Support-Resolution-System
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Download the model

```powershell
ollama pull llama3.2:3b
```

Ensure Ollama is running before starting the application.

### 5. Start the application

```powershell
python -m streamlit run app/main.py
```

Open the local URL displayed in the terminal.

## Run Tests

```powershell
python -m pytest -v
```

## Privacy and Limitations

- This project uses sample order and ticket records.
- Do not add real customer information, credentials, API keys, or secrets to the repository.
- This is a portfolio project, not a production-ready customer support platform.
- Production use requires appropriate authentication, authorization, secure data storage, monitoring, and safeguards for customer-impacting actions.

## Future Improvements

- Semantic search with embeddings and a vector database.
- Human approval for sensitive actions.
- Retrieval and response-quality evaluation.
- Secure integrations with order-management and help-desk systems.
- Audit logs and production deployment.

## License

No license has been selected yet. Add a license before permitting others to reuse the code.
