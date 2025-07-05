from langgraph.graph import StateGraph, END 
from langgraph.checkpoint.memory import MemorySaver 
from agents.project_analyzer import run as analyze_project
from agents.trend_aggregator import run as aggregate_trends
from agents.comparison_agent import run as compare_projects
from agents.fact_checker import run as fact_check
from agents.summarize_agent import run as summarize_project

class CrossPublicationInsightOrchestrator:
    def __init__(self):
        self.memory = MemorySaver()
        self.graph = StateGraph(dict)

        self.graph.add_node("analyze", analyze_project)
        self.graph.add_node("aggregate", aggregate_trends)
        self.graph.add_node("compare", compare_projects)
        self.graph.add_node("fact_check", fact_check)
        self.graph.add_node("summarize", summarize_project)


        self.graph.set_entry_point("analyze")
        self.graph.add_edge("analyze", "fact_check")
        self.graph.add_edge("aggregate", "compare")
        self.graph.add_edge("compare", "summarize")
        self.graph.add_edge("summarize", END)

        self.executor = self.graph.compile(checkpointer=self.memory)
    
    def run(self, input_data: dict, config: dict = None):
        if config:
            return self.executor.invoke(input_data, config=config)
        else:
            return self.executor.invoke(input_data)