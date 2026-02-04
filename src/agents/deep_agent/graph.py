"""Deep Agent - 基于create_deep_agent的深度分析智能体"""

from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, SummarizationMiddleware, TodoListMiddleware, dynamic_prompt

from src.agents.common import BaseAgent, load_chat_model
from src.agents.common.middlewares import inject_attachment_context
from src.agents.common.tools import get_tavily_search

from .context import DeepContext
from .prompts import DEEP_PROMPT


def _get_research_sub_agent(search_tools: list) -> dict:
    """Get research sub-agent config with search tools."""
    return {
        "name": "research-agent",
        "description": ("Use search tools to research deeper questions. Write research results to topic research files."),
        "system_prompt": (
            "You are a focused researcher. Your job is to research based on the user's questions. "
            "Conduct thorough research, then reply to the user's questions with detailed answers. Only your final answer will be passed to the user. "
            "They won't know anything else except your final message, so your final report should be your final message! "
            "Save research results to topic research files in /sub_research/xxx.md. "
            "IMPORTANT: All research, todo lists, and reports MUST be in ENGLISH."
        ),
        "tools": search_tools,
    }


critique_sub_agent = {
    "name": "critique-agent",
    "description": "Used to critique the final report. Give this agent some information about how you want it to critique the report.",
    "system_prompt": (
        "You are a focused editor. Your task is to critique a report.\n\n"
        "You can find this report in `final_report.md`.\n\n"
        "You can find the question/topic for this report in `question.txt`.\n\n"
        "Users may ask you to critique specific aspects of the report. Please reply to users with detailed critiques, pointing out areas in the report that can be improved.\n\n"
        "If it helps you critique the report, you can use search tools to search for information\n\n"
        "Do not write to `final_report.md` yourself.\n\n"
        "Things to check:\n"
        "- Check if the headings for each section are appropriate\n"
        "- Check if the report is written like a paper or textbook - it should be text-based, not just a bullet point list!\n"
        "- Check if the report is comprehensive. If any paragraphs or sections are too short, or missing important details, point them out.\n"
        "- Check if the article covers key areas of the industry, ensures overall understanding, and doesn't miss important parts.\n"
        "- Check if the article deeply analyzes causes, impacts, and trends, providing valuable insights\n"
        "- Check if the article sticks to the research topic and directly answers the question\n"
        "- Check if the article is well-structured, fluent in language, and easy to understand.\n"
        "IMPORTANT: All critiques and feedback MUST be in ENGLISH."
    ),
}


@dynamic_prompt
def context_aware_prompt(request: ModelRequest) -> str:
    """从 runtime context 动态生成系统提示词"""
    return DEEP_PROMPT + "\n\n\n" + request.runtime.context.system_prompt


class DeepAgent(BaseAgent):
    name = "Deep Analysis Agent"
    description = "An intelligent agent with planning, deep analysis, and sub-agent collaboration capabilities, capable of handling complex multi-step tasks"
    context_schema = DeepContext
    capabilities = [
        "file_upload",
        "todo",
        "files",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graph = None
        self.checkpointer = None

    async def get_tools(self):
        """返回 Deep Agent 的专用工具"""
        tools = []
        tavily_search = get_tavily_search()
        if tavily_search:
            tools.append(tavily_search)

        # Assert that search tool is available for DeepAgent
        assert tools, (
            "DeepAgent requires at least one search tool. "
            "Please configure TAVILY_API_KEY environment variable to enable web search."
        )
        return tools

    async def get_graph(self, **kwargs):
        """构建 Deep Agent 的图"""
        if self.graph:
            return self.graph

        # 获取上下文配置
        context = self.context_schema.from_file(module_name=self.module_name)

        model = load_chat_model(context.model)
        sub_model = load_chat_model(context.subagents_model)
        tools = await self.get_tools()

        # Build subagents with search tools
        research_sub_agent = _get_research_sub_agent(tools)

        # 使用 create_deep_agent 创建深度智能体
        graph = create_agent(
            model=model,
            tools=tools,
            system_prompt=context.system_prompt,
            middleware=[
                context_aware_prompt,  # 动态系统提示词
                inject_attachment_context,  # 附件上下文注入
                TodoListMiddleware(),
                FilesystemMiddleware(),
                SubAgentMiddleware(
                    default_model=sub_model,
                    default_tools=tools,
                    subagents=[critique_sub_agent, research_sub_agent],
                    default_middleware=[
                        TodoListMiddleware(),  # 子智能体也有 todo 列表
                        FilesystemMiddleware(),  # 当前的两个文件系统是隔离的
                        SummarizationMiddleware(
                            model=sub_model,
                            trigger=("tokens", 110000),
                            keep=("messages", 10),
                            trim_tokens_to_summarize=None,
                        ),
                        PatchToolCallsMiddleware(),
                    ],
                    general_purpose_agent=True,
                ),
                SummarizationMiddleware(
                    model=model,
                    trigger=("tokens", 110000),
                    keep=("messages", 10),
                    trim_tokens_to_summarize=None,
                ),
                PatchToolCallsMiddleware(),
            ],
            checkpointer=await self._get_checkpointer(),
        )

        self.graph = graph
        return graph
