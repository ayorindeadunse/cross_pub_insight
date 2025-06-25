"""
Trend Aggregator Agent

This agent receives the analysis output from the Project Analyzer
and scans it for meaningful patterns, such as technology mentions,
frameworks used, and architecture components. This is the "map-reduce"
step that allows the system to identify trends across multiple projects.

Future enhancements may use embedding similarity, LLM-assisted classification,
or keyword extraction tools for more robust results.
"""

from collections import Counter

def extract_trends(analysis_text: str) -> dict:
    """
    Heuristically extract trend indicators from the analysis text.

    Arg:
        analysis_text (str): The natural language description of a project.

    Returns:
        dict: Dictionary of boolean flags or extracted items.
    """
    lowered = analysis_text.lower()

    return {
        "mentions_langgraph": "langgraph" in lowered,
        "mentions_langchain": "langchain" in lowered,
        "mentions_crewai":"crewai" in lowered,
        "mentions_vector_db":any(k in lowered for k in ["vector db", "embedding", "faiss", "chromadb", "weaviate"]),
        "mentions_rag": "rag" in lowered or "retrieval-augmented" in lowered,
        "mentions_llama": "llama" in lowered,
        "mentions_openai": "openai" in lowered or "gpt" in lowered,
    }

def format_trend_summary(trends: dict) -> str:
    """
    Format the trend dictionary into a readable string summary.

    Args:
        trends (dict)" A dictionary of trend booleans.
    
    Returns:
        str: A human-readable trend summary.
    """
    summary_lines = [
        f"LangGraph Mentioned: {trends['mentions_langgraph']}",
        f"LangChain mentioned: {trends['mentions_langchain']}",
        f"Crewai Mentioned: {trends['mentions_crewai']}",
        f"Vector DB Mentioned: {trends['mentions_vector_db']}",
        f"RAG Mentioned: {trends['mentions_rag']}",
        f"Llama Mentioned: {trends['mentions_llama']}",
        f"OpenAI Mentioned: {trends['mentions_openai']}",
    ]
    return "\n".join(summary_lines)

def run(state: dict) -> dict:
   """
   Entry point for the Trend Aggregator node in LangGraph.

   Args:
       state (dict): The current state dict passed through the graph.

   Returns:
        dict: Updated state with 'aggregated_trends' field.
    """
   analysis = state.get("analysis_result", "")
   if not analysis:
       return {
           **state,
           "aggregated_trends": "No analysis found to extract trends from.", 
        }
   trends = extract_trends(analysis)
   trend_summary = format_trend_summary(trends)

   return {
       **state,
       "aggregated_trends": trend_summary,
   }