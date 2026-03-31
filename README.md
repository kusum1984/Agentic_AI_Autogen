# Multi-Agent AI System for Medical Device CAPA Investigation

## Project Objective

The objective of this project is to demonstrate how agentic AI systems can support quality engineering teams in medical device organizations.
Specifically, the system aims to:
• accelerate defect investigation
• identify probable root causes
• retrieve historical knowledge
• analyze production data
• generate regulatory investigation reports
• continuously learn from new investigations

## Why This Architecture Was Chosen
Traditional AI chatbots are insufficient for complex engineering investigations because they lack:
structured reasoning
data integration
reliability mechanisms
traceability
To address these limitations, this project adopts a multi-agent architecture where specialized AI agents collaborate to perform different parts of the investigation process.
Each agent is responsible for a specific capability, such as:
planning investigation steps
retrieving historical knowledge
analyzing structured production data
performing causal analysis
validating reasoning
enforcing regulatory structure
### This design provides:
1. Modularity
Each capability is implemented as an independent agent that can evolve separately.
2. Explainability
Investigation reasoning can be traced step-by-step across agents.
3. Reliability
Guardrails such as hallucination detection and debate agents improve answer quality.
4. Learning Capability
The system stores new investigation results in a vector database so that future cases benefit from past knowledge.


## Key Technologies Used
The system integrates several modern AI technologies:
AutoGen v5
Used to orchestrate multi-agent collaboration and task planning.
Retrieval Augmented Generation (RAG)
Allows the system to retrieve historical CAPA investigations and SOP documents.
DoWhy Causal Analysis
Used to perform structured root cause analysis on manufacturing data.
Databricks Lakehouse
Provides enterprise data storage, vector search, and experiment tracking.
LangSmith
Tracks agent interactions and debugging traces.
TruLens
Evaluates model hallucination risk and grounding quality.
Streamlit
Provides an interactive investigation dashboard for users.

## System Components
The system consists of five major layers.
1. User Interface
A Streamlit dashboard allows engineers to submit investigation queries and review results.
2. API Layer
A FastAPI backend manages sessions, routing, and system communication.
3. Agent Orchestration Layer
This layer contains the core multi-agent system responsible for reasoning and analysis.
4. Tool Layer
Agents access tools such as:
vector search
SQL queries
document analysis
causal inference
5. Data Layer
All investigation data is stored in a Databricks Lakehouse environment.

## Key Features
The system includes several advanced AI capabilities rarely implemented together.
Multi-Agent Collaboration

14 specialized AI agents collaborate to perform investigations.

#### Debate Reasoning
Multiple agents propose and challenge root cause hypotheses.

#### Self-Reflection
An agent evaluates reasoning quality before producing final results.

#### Hallucination Detection
Guardrails ensure answers remain grounded in evidence.

#### Continuous Learning
The system stores new investigations in a vector database for future retrieval.

#### Regulatory Reporting
Outputs are structured to align with FDA and ISO CAPA documentation.

## Expected Outcomes
This system demonstrates how modern agentic AI can:
accelerate engineering investigations
reduce time spent searching historical data
improve knowledge reuse across teams
increase transparency in AI decision-making


# Project Structure


capa-autonomous-investigation/
├── src/
│   ├── agent_orchestration/
│   │   ├── __init__.py
│   │   ├── supervisor_team.py           # Main orchestration team
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── planner_agent.py
│   │   │   ├── executor_agent.py
│   │   │   ├── rag_retrieval_agent.py
│   │   │   ├── sql_analysis_agent.py
│   │   │   ├── document_analysis_agent.py
│   │   │   ├── causal_analysis_agent.py
│   │   │   ├── root_cause_agent.py
│   │   │   ├── debate_agent.py
│   │   │   ├── self_reflection_agent.py
│   │   │   ├── hallucination_guard_agent.py
│   │   │   ├── compliance_agent.py
│   │   │   ├── report_generator_agent.py
│   │   │   └── learning_agent.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── vector_search_tool.py
│   │       ├── sql_query_tool.py
│   │       ├── document_retrieval_tool.py
│   │       ├── dowhy_causal_tool.py
│   │       └── report_generation_tool.py
│   ├── api_gateway/
│   ├── streamlit_app/
│   └── databricks_integration/
├── requirements.txt
└── .env



###System Architecture Diagram (High-Level)
This diagram shows the complete enterprise architecture including UI, agents, tools, and Databricks infrastructure.
┌──────────────────────────────────────────────────────────┐
│                        USER                              │
│                Quality Engineer / Analyst                │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                         │
│ Investigation dashboard                                  │
│ - submit defect report                                   │
│ - view investigation results                             │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                    FASTAPI GATEWAY                       │
│ Request routing / authentication                         │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                AGENT ORCHESTRATION LAYER                 │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SUPERVISOR AGENT                    │    │
│  │ Controls investigation workflow                  │    │
│  └──────────────────────────────────────────────────┘    │
│                           │                              │
│                           ▼                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │                 PLANNER AGENT                    │    │
│  │ Breaks problem into investigation tasks          │    │
│  └──────────────────────────────────────────────────┘    │
│                           │                              │
│                           ▼                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │                 EXECUTOR AGENT                   │    │
│  │ Dispatches tasks to analysis agents              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Investigation Agents                                    │
│  ───────────────────────────────────────────────         │
│  • RAG Retrieval Agent                                   │
│  • SQL Data Analysis Agent                               │
│  • Document Analysis Agent                               │
│  • Causal Analysis Agent (DoWhy)                         │
│  • Root Cause Investigator                               │
│  • Debate Agents (Hypothesis testing)                    │
│  • Self Reflection Agent                                 │
│  • Hallucination Guard Agent                             │
│  • Compliance Agent                                      │
│  • Report Generator Agent                                │
│  • Learning Agent                                        │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                       TOOL LAYER                         │
│                                                          │
│ Vector Search Tool                                       │
│ SQL Query Tool                                           │
│ Document Retrieval Tool                                  │
│ DoWhy Causal Analysis Tool                               │
│ Report Generation Tool                                   │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                DATABRICKS LAKEHOUSE                      │
│                                                          │
│ Delta Tables                                             │
│ CAPA Investigations                                      │
│ Manufacturing Data                                       │
│                                                          │
│ Vector Search                                            │
│ CAPA Knowledge Base                                      │
│ SOP Documentation                                        │
│                                                          │
│ MLflow                                                   │
│ Experiment Tracking                                      │
│ Model Evaluation                                         │
└──────────────────────────────────────────────────────────┘





