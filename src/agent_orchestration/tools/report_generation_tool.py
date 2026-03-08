"""
report_generation_tool.py
=========================
Report generation tools for creating formatted investigation reports.
"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import logging
import markdown

logger = logging.getLogger(__name__)

def generate_pdf_report(
    investigation_data: Dict[str, Any],
    template: str = "standard"
) -> Dict[str, Any]:
    """
    Generate a formatted PDF report of investigation findings.
    
    Args:
        investigation_data: Complete investigation data
        template: Report template to use
    
    Returns:
        PDF report data or error
    """
    try:
        # This would use a PDF generation library like reportlab or weasyprint
        # For now, return structured data that can be used by frontend
        
        report_structure = {
            "investigation_id": investigation_data.get("investigation_id"),
            "generated_at": datetime.now().isoformat(),
            "template": template,
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": _format_executive_summary(investigation_data)
                },
                {
                    "title": "Defect Description",
                    "content": investigation_data.get("defect_report", {})
                },
                {
                    "title": "Evidence Gathered",
                    "content": _format_evidence(investigation_data.get("findings", []))
                },
                {
                    "title": "Root Cause Analysis",
                    "content": _format_root_cause(investigation_data)
                },
                {
                    "title": "Recommendations",
                    "content": _format_recommendations(investigation_data)
                }
            ],
            "pdf_available": False,  # Set to True when PDF generation is implemented
            "download_url": f"/api/v1/investigations/{investigation_data.get('investigation_id')}/results?format=pdf"
        }
        
        return report_structure
        
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return {"error": str(e)}

def format_findings(
    findings: List[Dict[str, Any]],
    format_type: str = "markdown"
) -> str:
    """
    Format investigation findings into structured text.
    
    Args:
        findings: List of finding objects
        format_type: Output format (markdown, json, text)
    
    Returns:
        Formatted findings
    """
    try:
        if format_type == "json":
            return json.dumps(findings, indent=2)
        
        elif format_type == "markdown":
            md_lines = ["## Investigation Findings\n"]
            
            for i, finding in enumerate(findings, 1):
                md_lines.append(f"### Finding {i}: {finding.get('title', 'Untitled')}")
                md_lines.append(f"\n**Agent**: {finding.get('agent', 'Unknown')}")
                md_lines.append(f"\n**Timestamp**: {finding.get('timestamp', 'Unknown')}")
                md_lines.append(f"\n**Content**:\n{finding.get('content', 'No content')}\n")
                md_lines.append("---\n")
            
            return "\n".join(md_lines)
        
        else:  # plain text
            text_lines = ["INVESTIGATION FINDINGS", "=" * 30, ""]
            
            for i, finding in enumerate(findings, 1):
                text_lines.append(f"Finding {i}: {finding.get('title', 'Untitled')}")
                text_lines.append(f"Agent: {finding.get('agent', 'Unknown')}")
                text_lines.append(f"Time: {finding.get('timestamp', 'Unknown')}")
                text_lines.append(f"Content: {finding.get('content', 'No content')}")
                text_lines.append("-" * 30)
            
            return "\n".join(text_lines)
            
    except Exception as e:
        logger.error(f"Findings formatting failed: {e}")
        return f"Error formatting findings: {str(e)}"

def _format_executive_summary(data: Dict) -> str:
    """Format executive summary section."""
    summary = []
    
    summary.append(f"Investigation ID: {data.get('investigation_id', 'N/A')}")
    summary.append(f"Status: {data.get('status', 'N/A')}")
    
    defect = data.get('defect_report', {})
    summary.append(f"Defect: {defect.get('title', 'N/A')}")
    summary.append(f"Severity: {defect.get('severity', 'N/A')}")
    
    root_causes = data.get('root_causes', [])
    if root_causes:
        summary.append(f"Root Causes: {', '.join(root_causes)}")
    
    return "\n".join(summary)

def _format_evidence(findings: List) -> str:
    """Format evidence section."""
    evidence = []
    
    for finding in findings:
        evidence.append(f"• {finding.get('content', '')[:200]}...")
    
    return "\n".join(evidence) if evidence else "No evidence recorded"

def _format_root_cause(data: Dict) -> str:
    """Format root cause analysis section."""
    rc_data = data.get('root_cause_analysis', {})
    
    lines = [
        f"Primary Root Cause: {rc_data.get('primary', 'Not determined')}",
        f"Confidence Level: {rc_data.get('confidence', 'N/A')}",
        "\nContributing Factors:",
    ]
    
    for factor in rc_data.get('contributing_factors', []):
        lines.append(f"  • {factor}")
    
    return "\n".join(lines)

def _format_recommendations(data: Dict) -> str:
    """Format recommendations section."""
    recs = data.get('recommendations', [])
    
    if not recs:
        return "No recommendations provided"
    
    lines = []
    for rec in recs:
        lines.append(f"• {rec}")
    
    return "\n".join(lines)
