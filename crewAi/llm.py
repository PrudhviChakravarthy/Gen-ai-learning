from crewai import  LLM

llm=LLM(model="openai/gemma3:4b", base_url="http://localhost:11434/v1", temperature=0, top_p=0.94, api_key="fake")
