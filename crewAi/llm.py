from crewai import  LLM

llm=LLM(model="ollama/gemma3:4b", base_url="http://localhost:11434", temperature=0, top_p=0.94)
