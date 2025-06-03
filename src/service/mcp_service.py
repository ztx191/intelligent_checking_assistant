import uvicorn
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from src.service.tools.process_node import ProcessNode

# 初始化服务器
app = Server("operateMysql")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的MySQL工具
    返回:
        list[Tool]: 工具列表，当前仅包含check_id_occupation工具
    """
    return [
        Tool(
            name="check_id_occupation",
            description="判断证件号在系统中被是否被占用",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "证件号"}
                },
                "required": ["query"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "check_id_occupation":
        query = arguments.get("query")
        if not query:
            raise ValueError("缺少输入语句")
        return ProcessNode().check_id_occupation(query)

    raise ValueError(f"未知的工具: {name}")


sse = SseServerTransport("/messages/")


# Handler for SSE connections
async def handle_sse(request):
    async with sse.connect_sse(
            request.scope, request.receive, request._send
    ) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


# Create Starlette app with routes
starlette_app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=9000)