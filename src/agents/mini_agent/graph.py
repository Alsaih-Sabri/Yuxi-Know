from langchain.agents import create_agent

from src.agents.common import BaseAgent, load_chat_model
from src.agents.common.tools import get_tools_from_context


class MiniAgent(BaseAgent):
    name = "Agent Demo"
    description = "An example agent based on built-in tools"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get_graph(self, **kwargs):
        if self.graph:
            return self.graph

        context = self.context_schema.from_file(module_name=self.module_name)

        # 创建 MiniAgent
        graph = create_agent(
            model=load_chat_model(context.model),
            system_prompt=context.system_prompt,
            tools=await get_tools_from_context(context),
            checkpointer=await self._get_checkpointer(),
        )

        self.graph = graph
        return graph
