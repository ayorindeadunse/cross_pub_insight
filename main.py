from agents.project_analyzer import ProjectAnalyzerAgent

agent = ProjectAnalyzerAgent(llm_type="local")
analysis = agent.analyze_project("path/to/repository")
print(analysis)