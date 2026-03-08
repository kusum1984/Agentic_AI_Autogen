"""
dowhy_causal_tool.py
====================
Causal analysis tools using the DoWhy library for causal inference.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import dowhy
from dowhy import CausalModel
import logging

logger = logging.getLogger(__name__)

def perform_causal_analysis(
    data: List[Dict[str, Any]],
    treatment: str,
    outcome: str,
    common_causes: Optional[List[str]] = None,
    instruments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Perform causal inference analysis using DoWhy.
    
    Args:
        data: Dataset as list of dictionaries
        treatment: Name of treatment variable
        outcome: Name of outcome variable
        common_causes: List of common cause variables
        instruments: List of instrument variables
    
    Returns:
        Causal analysis results
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Build causal model
        model = CausalModel(
            data=df,
            treatment=treatment,
            outcome=outcome,
            common_causes=common_causes or [],
            instruments=instruments or []
        )
        
        # Identify causal effect
        identified_estimand = model.identify_effect()
        
        # Estimate causal effect (using linear regression as default)
        estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.linear_regression"
        )
        
        # Refute with random common cause
        refute_random = model.refute_estimate(
            identified_estimand,
            estimate,
            method_name="random_common_cause"
        )
        
        # Refute with placebo treatment
        refute_placebo = model.refute_estimate(
            identified_estimand,
            estimate,
            method_name="placebo_treatment_refuter",
            placebo_type="permute"
        )
        
        # Results
        results = {
            "treatment": treatment,
            "outcome": outcome,
            "causal_estimate": estimate.value,
            "confidence_intervals": {
                "lower": estimate.value - 1.96 * estimate.get_standard_error(),
                "upper": estimate.value + 1.96 * estimate.get_standard_error()
            },
            "p_value": estimate.test_stat_significance().get("p_value"),
            "refutation_tests": {
                "random_common_cause": {
                    "new_estimate": refute_random.new_effect,
                    "difference": refute_random.new_effect - estimate.value
                },
                "placebo_treatment": {
                    "new_estimate": refute_placebo.new_effect,
                    "p_value": refute_placebo.new_effect_p_value
                }
            },
            "model_summary": str(model.summary()),
            "graph": model.graph,
            "method": "linear_regression"
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Causal analysis failed: {e}")
        return {"error": str(e)}

def build_causal_graph(
    variables: List[str],
    known_edges: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Build a causal graph from known relationships.
    
    Args:
        variables: List of variable names
        known_edges: List of dictionaries with 'cause' and 'effect' keys
    
    Returns:
        Causal graph structure and visualization
    """
    try:
        import networkx as nx
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes
        G.add_nodes_from(variables)
        
        # Add edges
        for edge in known_edges:
            G.add_edge(edge['cause'], edge['effect'])
        
        # Check for cycles
        cycles = list(nx.simple_cycles(G))
        
        # Get adjacency list
        adjacency = {}
        for node in G.nodes():
            adjacency[node] = list(G.successors(node))
        
        # Generate graph string
        graph_string = "digraph {"
        for cause, effect in G.edges():
            graph_string += f"{cause} -> {effect};"
        graph_string += "}"
        
        return {
            "variables": variables,
            "edges": known_edges,
            "adjacency": adjacency,
            "has_cycles": len(cycles) > 0,
            "cycles": cycles if cycles else None,
            "graph_dot": graph_string,
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges()
        }
        
    except Exception as e:
        logger.error(f"Failed to build causal graph: {e}")
        return {"error": str(e)}
