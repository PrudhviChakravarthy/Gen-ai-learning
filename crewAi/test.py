import warnings
from crewai import Agent, Crew, Task
from crewai_tools import MCPServerAdapter
from llm import llm
from pydantic import PydanticDeprecatedSince20, PydanticDeprecationWarning

warnings.filterwarnings("ignore",category=PydanticDeprecationWarning)
server_params = {
    "url": "http://localhost:8000/sse",
}

def main():
    with MCPServerAdapter(server_params) as mcp_tools:
        print(f"Available tools: {[tool.name for tool in mcp_tools]}")

        my_agent = Agent(
            role="MCP Tool User",
            goal="Utilize tools and give the appropriate answer",
            backstory="if the question is releavnat to  use the tools use the tools or answer directly.",
            tools=mcp_tools,  # Pass the loaded tools to your agent
            reasoning=False,
            llm=llm,
            verbose=True,
            max_retry_limit=2
        )

        agent_Task = Task(
            description="evaluate the question {question} and explain the answer to the user",
            agent=my_agent,
            output_file="answer.md",
            expected_output="give me the answer in the detailed format"
        )

        my_Crew = Crew(
            agents=[my_agent],
            tasks=[agent_Task],
            verbose=True
        )

        text = str(input("Please input your question: "))
        my_Crew.kickoff(inputs={"question":text})  # Ensure await if kickoff is async

if __name__ == "__main__":
     main()  # Properly run the async function