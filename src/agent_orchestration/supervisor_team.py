"""
capa_supervisor_team.py
=======================
Core orchestration logic for the CAPA autonomous investigation system built with
AutoGen v0.4+ AgentChat stack. This module drives a multi-agent team that:
- Plans investigation strategy
- Executes specialized analysis tasks
- Debates hypotheses
- Validates findings
- Generates compliance-ready reports

The system uses a hierarchical team structure with a supervisor agent coordinating
multiple specialized sub-agents.
"""

from __future__ import annotations
import os
import asyncio
import json
from typing import AsyncGenerator, Dict, List, Any, Optional
from datetime import datetime
import logging

from autogen_core.tools import FunctionTool
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import (
    RoundRobinGroupChat, 
    SelectorGroupChat,
    HierarchicalTeam
)
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import tools
from src.agent_orchestration.tools.vector_search_tool import vector_search, similarity_search
from src.agent_orchestration.tools.sql_query_tool import execute_sql_query, get_table_schema
from src.agent_orchestration.tools.document_retrieval_tool import retrieve_document, extract_sections
from src.agent_orchestration.tools.dowhy_causal_tool import perform_causal_analysis, build_causal_graph
from src.agent_orchestration.tools.report_generation_tool import generate_pdf_report, format_findings

# Import agents
from src.agent_orchestration.agents.planner_agent import create_planner_agent
from src.agent_orchestration.agents.executor_agent import create_executor_agent
from src.agent_orchestration.agents.rag_retrieval_agent import create_rag_agent
from src.agent_orchestration.agents.sql_analysis_agent import create_sql_agent
from src.agent_orchestration.agents.document_analysis_agent import create_document_agent
from src.agent_orchestration.agents.causal_analysis_agent import create_causal_agent
from src.agent_orchestration.agents.root_cause_agent import create_root_cause_agent
from src.agent_orchestration.agents.debate_agent import create_debate_agent
from src.agent_orchestration.agents.self_reflection_agent import create_reflection_agent
from src.agent_orchestration.agents.hallucination_guard_agent import create_guard_agent
from src.agent_orchestration.agents.compliance_agent import create_compliance_agent
from src.agent_orchestration.agents.report_generator_agent import create_report_agent
from src.agent_orchestration.agents.learning_agent import create_learning_agent

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Tool Definitions -------------------------------------------------------
# ---------------------------------------------------------------------------

# Vector Search Tools
vector_search_tool = FunctionTool(
    vector_search,
    description="Search the CAPA knowledge base for similar historical cases using vector similarity. Returns relevant past investigations with similarity scores."
)

similarity_search_tool = FunctionTool(
    similarity_search,
    description="Find semantically similar documents, SOPs, or procedures based on text input."
)

# SQL Query Tools
sql_query_tool = FunctionTool(
    execute_sql_query,
    description="Execute SQL queries against Databricks Delta tables containing manufacturing data, test results, and investigation history."
)

schema_tool = FunctionTool(
    get_table_schema,
    description="Get the schema of a specific Delta table to understand available columns and data types."
)

# Document Retrieval Tools
doc_retrieval_tool = FunctionTool(
    retrieve_document,
    description="Retrieve full document content by ID or title from the document store."
)

section_extraction_tool = FunctionTool(
    extract_sections,
    description="Extract specific sections from SOPs or technical documents (e.g., 'procedure', 'specifications', 'troubleshooting')."
)

# Causal Analysis Tools
causal_analysis_tool = FunctionTool(
    perform_causal_analysis,
    description="Perform causal inference analysis using DoWhy to identify potential root causes from data."
)

causal_graph_tool = FunctionTool(
    build_causal_graph,
    description="Build and visualize causal graphs based on domain knowledge and data relationships."
)

# Report Generation Tools
pdf_report_tool = FunctionTool(
    generate_pdf_report,
    description="Generate a formatted PDF report of investigation findings."
)

findings_formatter_tool = FunctionTool(
    format_findings,
    description="Format investigation findings into structured sections for reporting."
)

# ---------------------------------------------------------------------------
# 2. Agent Factory Functions ------------------------------------------------
# ---------------------------------------------------------------------------

def create_supervisor_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the supervisor agent that coordinates the entire investigation."""
    
    return AssistantAgent(
        name="supervisor",
        description="Supervisor agent that coordinates the entire CAPA investigation process.",
        system_message="""You are the Supervisor Agent responsible for orchestrating the CAPA investigation.

Your responsibilities:
1. Receive defect reports and initiate the investigation workflow
2. Delegate tasks to the Planner agent to create investigation strategy
3. Monitor progress and ensure all investigation phases are completed
4. Coordinate between specialized agents when they need to collaborate
5. Validate that all findings are properly documented and evidence-based
6. Ensure compliance with CAPA standards throughout the process
7. Make final decisions on root cause determination when debates are inconclusive
8. Escalate issues that require human intervention

You have access to a team of specialized agents:
- Planner: Creates investigation plan
- Executor: Executes specific tasks using tools
- RAGRetrieval: Finds similar historical cases
- SQLAnalysis: Analyzes manufacturing data
- DocumentAnalysis: Reviews SOPs and documentation
- CausalAnalysis: Performs causal inference
- RootCause: Determines root causes
- Debate: Debates competing hypotheses
- SelfReflection: Validates reasoning
- HallucinationGuard: Checks for hallucinations
- Compliance: Ensures regulatory compliance
- ReportGenerator: Creates final report
- Learning: Updates knowledge base

Always maintain a systematic approach and document all decisions.""",
        model_client=model_client,
        tools=[],  # Supervisor delegates, doesn't use tools directly
    )

def create_planner_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the planner agent that breaks down investigations into tasks."""
    
    return AssistantAgent(
        name="planner",
        description="Planner agent that creates investigation strategies and task breakdowns.",
        system_message="""You are the Planner Agent. Your role is to analyze defect reports and create comprehensive investigation plans.

For each defect, you must:
1. Categorize the defect type (manufacturing, design, process, supplier, etc.)
2. Identify data sources needed (historical CAPAs, manufacturing data, test results)
3. Determine which specialized agents should be involved
4. Create investigation phases with clear objectives
5. Define success criteria for each phase
6. Identify potential hypotheses to test
7. Specify required evidence for root cause determination
8. Estimate investigation complexity and timeline

Always output your plan in a structured format that can be executed by the Executor Agent.
Include specific tasks, required tools, and expected outcomes.

Example output format:
{
    "defect_category": "manufacturing",
    "complexity": "high",
    "phases": [
        {
            "phase": 1,
            "name": "Data Collection",
            "tasks": ["search_historical_cases", "retrieve_sops"],
            "agents": ["RAGRetrieval", "DocumentAnalysis"],
            "success_criteria": ["historical data found", "relevant SOPs identified"]
        }
    ],
    "hypotheses": ["process deviation", "material defect", "human error"],
    "timeline_estimate_hours": 8
}""",
        model_client=model_client,
        tools=[],  # Planner plans but doesn't execute
    )

def create_executor_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the executor agent that runs specific investigation tasks."""
    
    return AssistantAgent(
        name="executor",
        description="Executor agent that runs specific investigation tasks using available tools.",
        system_message="""You are the Executor Agent. Your role is to execute specific investigation tasks using the available tools.

You have access to these tools:
- vector_search: Find similar historical cases
- similarity_search: Find similar documents
- sql_query: Query manufacturing data
- schema_tool: Understand table structures
- doc_retrieval: Get full documents
- section_extraction: Extract specific sections
- causal_analysis: Perform causal inference
- causal_graph: Build causal models
- pdf_report: Generate reports
- findings_formatter: Format findings

When executing tasks:
1. Understand the task objective from the planner
2. Select the appropriate tools
3. Execute tools with proper parameters
4. Collect and organize results
5. Report findings back clearly
6. Handle errors gracefully and suggest alternatives

Always provide detailed execution results that can be used by other agents.""",
        model_client=model_client,
        tools=[
            vector_search_tool,
            similarity_search_tool,
            sql_query_tool,
            schema_tool,
            doc_retrieval_tool,
            section_extraction_tool,
            causal_analysis_tool,
            causal_graph_tool,
            pdf_report_tool,
            findings_formatter_tool
        ],
    )

# ---------------------------------------------------------------------------
# 3. Team Construction ------------------------------------------------------
# ---------------------------------------------------------------------------

def build_investigation_team(model: str = "gpt-4") -> HierarchicalTeam:
    """
    Build a hierarchical team of agents for CAPA investigation.
    
    The team structure:
    - Supervisor (top-level coordinator)
    - Specialized agents (each with specific roles)
    
    Returns a HierarchicalTeam that manages the investigation workflow.
    """
    
    # Initialize the model client
    llm_client = OpenAIChatCompletionClient(
        model=model,
        api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.2,  # Lower temperature for more consistent results
    )
    
    # Create all specialized agents
    supervisor = create_supervisor_agent(llm_client)
    planner = create_planner_agent(llm_client)
    executor = create_executor_agent(llm_client)
    
    # Import and create other specialized agents
    rag_agent = create_rag_agent(llm_client)
    sql_agent = create_sql_agent(llm_client)
    doc_agent = create_document_agent(llm_client)
    causal_agent = create_causal_agent(llm_client)
    root_cause_agent = create_root_cause_agent(llm_client)
    debate_agent = create_debate_agent(llm_client)
    reflection_agent = create_reflection_agent(llm_client)
    guard_agent = create_guard_agent(llm_client)
    compliance_agent = create_compliance_agent(llm_client)
    report_agent = create_report_agent(llm_client)
    learning_agent = create_learning_agent(llm_client)
    
    # Create specialized sub-teams for different investigation phases
    
    # Data collection team
    data_collection_team = RoundRobinGroupChat(
        participants=[rag_agent, sql_agent, doc_agent],
        max_turns=3,
        name="data_collection_team"
    )
    
    # Analysis team
    analysis_team = RoundRobinGroupChat(
        participants=[causal_agent, root_cause_agent, debate_agent],
        max_turns=5,
        name="analysis_team"
    )
    
    # Validation team
    validation_team = RoundRobinGroupChat(
        participants=[reflection_agent, guard_agent, compliance_agent],
        max_turns=3,
        name="validation_team"
    )
    
    # Create the hierarchical team with supervisor at top
    investigation_team = HierarchicalTeam(
        name="capa_investigation_team",
        supervisor=supervisor,
        teams=[data_collection_team, analysis_team, validation_team],
        workers=[planner, executor, report_agent, learning_agent],
        max_turns=20,  # Maximum conversation turns
        supervisor_turn_after_each_team=True,  # Supervisor coordinates between phases
    )
    
    return investigation_team

# ---------------------------------------------------------------------------
# 4. Investigation Orchestrator ---------------------------------------------
# ---------------------------------------------------------------------------

class CAPAInvestigationOrchestrator:
    """
    Orchestrator for CAPA investigations that manages the entire workflow.
    """
    
    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self.team = build_investigation_team(model)
        self.investigation_history = {}
        
    async def conduct_investigation(
        self,
        defect_report: Dict[str, Any],
        investigation_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Conduct a full CAPA investigation based on the defect report.
        
        Args:
            defect_report: Dictionary containing defect details
            investigation_id: Optional custom ID for the investigation
            
        Yields:
            Strings representing the investigation progress and results
        """
        
        # Generate investigation ID if not provided
        if not investigation_id:
            investigation_id = f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Store investigation context
        context = {
            "investigation_id": investigation_id,
            "defect_report": defect_report,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        
        self.investigation_history[investigation_id] = context
        
        # Construct the investigation prompt
        investigation_prompt = self._build_investigation_prompt(defect_report, investigation_id)
        
        yield f"🚀 Starting CAPA Investigation {investigation_id}\n"
        yield f"📋 Defect: {defect_report.get('title', 'Untitled')}\n"
        yield f"⚠️ Severity: {defect_report.get('severity', 'Not specified')}\n"
        yield "-" * 50 + "\n\n"
        
        try:
            # Run the investigation through the hierarchical team
            async for message in self.team.run_stream(task=investigation_prompt):
                if isinstance(message, TextMessage):
                    formatted_message = self._format_message(message)
                    yield formatted_message
                    
                    # Update context with important findings
                    await self._update_investigation_context(investigation_id, message)
            
            # Investigation completed
            context["status"] = "completed"
            context["end_time"] = datetime.now().isoformat()
            
            yield "\n✅ Investigation completed successfully!\n"
            yield f"📊 Final report available for investigation {investigation_id}\n"
            
        except Exception as e:
            logger.error(f"Investigation failed: {e}")
            context["status"] = "failed"
            context["error"] = str(e)
            
            yield f"\n❌ Investigation failed: {str(e)}\n"
    
    def _build_investigation_prompt(self, defect_report: Dict[str, Any], investigation_id: str) -> str:
        """Build the initial investigation prompt."""
        
        return f"""Please conduct a thorough CAPA investigation for the following defect report:

Investigation ID: {investigation_id}

DEFECT REPORT:
---------------
ID: {defect_report.get('defect_id', 'N/A')}
Title: {defect_report.get('title', 'N/A')}
Description: {defect_report.get('description', 'N/A')}
Severity: {defect_report.get('severity', 'N/A')}
Product/Process: {defect_report.get('product', 'N/A')}
Date Detected: {defect_report.get('detection_date', 'N/A')}
Detected By: {defect_report.get('detected_by', 'N/A')}
Immediate Actions Taken: {defect_report.get('immediate_actions', 'None reported')}
Additional Context: {defect_report.get('context', 'None provided')}

INVESTIGATION REQUIREMENTS:
---------------------------
1. Search for similar historical cases using RAG retrieval
2. Analyze relevant manufacturing data and test results
3. Review applicable SOPs and documentation
4. Perform causal analysis to identify potential root causes
5. Generate and debate competing hypotheses
6. Validate findings for accuracy and hallucinations
7. Ensure regulatory compliance with CAPA standards
8. Determine the most likely root cause(s)
9. Generate a comprehensive investigation report
10. Update the knowledge base with findings for future cases

Please coordinate all agents to complete this investigation thoroughly and efficiently.
The final output should include:
- All evidence gathered
- Hypotheses considered and debated
- Root cause determination with supporting evidence
- Recommended corrective and preventive actions
- Compliance assessment

Begin the investigation now.
"""
    
    def _format_message(self, message: TextMessage) -> str:
        """Format agent messages for display."""
        
        # Define emoji mapping for different agents
        agent_emojis = {
            "supervisor": "🎯",
            "planner": "📋",
            "executor": "⚙️",
            "rag_agent": "🔍",
            "sql_agent": "📊",
            "doc_agent": "📄",
            "causal_agent": "🔄",
            "root_cause_agent": "🎯",
            "debate_agent": "⚖️",
            "reflection_agent": "🪞",
            "guard_agent": "🛡️",
            "compliance_agent": "✓",
            "report_agent": "📝",
            "learning_agent": "🧠",
            "data_collection_team": "📚",
            "analysis_team": "🔬",
            "validation_team": "✅"
        }
        
        emoji = agent_emojis.get(message.source, "🤖")
        
        return f"{emoji} **{message.source}**: {message.content}\n\n"
    
    async def _update_investigation_context(self, investigation_id: str, message: TextMessage):
        """Update investigation context with key findings."""
        
        context = self.investigation_history.get(investigation_id, {})
        
        if "findings" not in context:
            context["findings"] = []
        
        # Check if message contains important findings
        content_lower = message.content.lower()
        if any(keyword in content_lower for keyword in ["root cause", "hypothesis", "evidence", "conclusion"]):
            context["findings"].append({
                "agent": message.source,
                "content": message.content,
                "timestamp": datetime.now().isoformat()
            })
        
        self.investigation_history[investigation_id] = context
    
    async def get_investigation_status(self, investigation_id: str) -> Dict[str, Any]:
        """Get the current status of an investigation."""
        return self.investigation_history.get(investigation_id, {})
    
    async def cancel_investigation(self, investigation_id: str) -> bool:
        """Cancel an ongoing investigation."""
        if investigation_id in self.investigation_history:
            self.investigation_history[investigation_id]["status"] = "cancelled"
            return True
        return False

# ---------------------------------------------------------------------------
# 5. Public API -------------------------------------------------------------
# ---------------------------------------------------------------------------

# Global orchestrator instance
_orchestrator: Optional[CAPAInvestigationOrchestrator] = None

def get_orchestrator(model: str = "gpt-4") -> CAPAInvestigationOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CAPAInvestigationOrchestrator(model)
    return _orchestrator

async def run_investigation(
    defect_report: Dict[str, Any],
    investigation_id: Optional[str] = None,
    model: str = "gpt-4"
) -> AsyncGenerator[str, None]:
    """
    Run a CAPA investigation and yield progress messages.
    
    This is the main public API for starting investigations.
    
    Args:
        defect_report: Dictionary containing defect details
        investigation_id: Optional custom ID
        model: OpenAI model to use
    
    Yields:
        Progress messages and final results
    """
    orchestrator = get_orchestrator(model)
    async for message in orchestrator.conduct_investigation(defect_report, investigation_id):
        yield message

# ---------------------------------------------------------------------------
# 6. CLI Testing ------------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    
    async def demo_investigation():
        """Run a demo investigation with sample defect."""
        
        sample_defect = {
            "defect_id": "DEF-2024-001",
            "title": "Intermittent sensor failure in production line A",
            "description": "Temperature sensor showing intermittent readings outside spec range during peak production hours. Affects product quality in final testing.",
            "severity": "High",
            "product": "Temperature Sensor Model XT-2000",
            "detection_date": "2024-03-15",
            "detected_by": "QA Inspector",
            "immediate_actions": "Increased inspection frequency, quarantined affected batch",
            "context": "Sensor has been in operation for 6 months, recently calibrated. Similar issues reported at other facilities."
        }
        
        print("=" * 60)
        print("CAPA Autonomous Investigation System - Demo")
        print("=" * 60)
        print()
        
        async for message in run_investigation(sample_defect):
            print(message)
    
    asyncio.run(demo_investigation())
