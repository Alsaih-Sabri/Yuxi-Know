from langchain.agents import create_agent
from langchain.tools import tool

from src import config
from src.agents.common import load_chat_model
from src.agents.common.tools import calculator

calc_agent = create_agent(
    model=load_chat_model(config.default_model),
    tools=[calculator],
    system_prompt="You can use the calculator tool to handle various mathematical calculation tasks. Only return the calculation result, no additional explanation needed.",
)


@tool(name_or_callable="calc_agent_tool", description="Perform calculation tasks. Input is a mathematical expression or description, output is the calculation result.")
async def calc_agent_tool(description: str) -> str:
    """CalcAgent Tool - Use sub-agent CalcAgent for calculation tasks"""
    response = await calc_agent.ainvoke({"messages": [("user", description)]})
    return response["messages"][-1].content
