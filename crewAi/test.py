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
            backstory="if the question is releavnat to  use the tools use the tools or answer directly. and for using the webextracting tools go through all the websites for the maixium information",
            tools=mcp_tools,  # Pass the loaded tools to your agent
            reasoning=False,
            inject_date=True,
            code_execution_mode="safe",
            llm=llm,
            verbose=True,
            max_retry_limit=2
        )

        agent_Task = Task(
            description="evaluate the question USER_QUESTION:<>{question}</> and explain the answer to the user always use seper tool before extract_web_content tool and only take the links from the serper tool dont use your imaginated links",
            agent=my_agent,
            output_file="answer.md",
            expected_output="give me the answer in the detailed format only markdown format and need everything in deails"
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