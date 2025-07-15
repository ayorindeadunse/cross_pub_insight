from langgraph.graph import StateGraph, END 
from langgraph.checkpoint.memory import MemorySaver 
from agents.project_analyzer import run as analyze_project
from agents.trend_aggregator import run as aggregate_trends
from agents.comparison_agent import run as compare_projects
from agents.fact_checker import run as fact_check
from agents.summarize_agent import run as summarize_project
from agents.aggregate_query_agent import run as aggregate_query_run

from utils.config_loader import load_config
from tools.hitl_intervention import review_before_summary

class CrossPublicationInsightOrchestrator:
    def __init__(self, user_query: str = ""):
        self.memory = MemorySaver()
        self.graph = StateGraph(dict)

        self.graph.add_node("analyze", analyze_project)
        self.graph.add_node("aggregate", aggregate_trends)
        self.graph.add_node("compare", compare_projects)
        self.graph.add_node("fact_check", fact_check)
        self.graph.add_node("summarize", summarize_project)


        if user_query:
            self.graph.add_node("aggregate_query", aggregate_query_run)
        
        self.graph.set_entry_point("analyze")
        self.graph.add_edge("analyze", "fact_check")
        self.graph.add_edge("fact_check", "aggregate")
        self.graph.add_edge("aggregate", "compare")

        if user_query:
            self.graph.add_edge("compare", "aggregate_query")
            self.graph.add_edge("aggregate_query", "summarize")
        else:
            self.graph.add_edge("compare", "summarize")
        
        self.graph.add_edge("summarize", END)
        self.executor = self.graph.compile(checkpointer=self.memory)
    
    def run(self, input_data: dict, config: dict = None):
        result = self.executor.invoke(input_data, config=config) if config else self.executor.invoke(input_data)
        
        # HITL before summarization
        cfg = load_config()
        hitl_enabled = cfg.get("hitl", {}).get("enabled", False)

        if config and "hitl_override" in config:
            hitl_enabled = config["hitl_override"].get("enabled", hitl_enabled)
        
        if hitl_enabled and cfg["hitl"].get("step") == "pre-summary":
            result = review_before_summary(result)
        
        return result
        