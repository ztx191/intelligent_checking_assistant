import uvicorn
from fastapi import FastAPI, Request
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent
from src.service.tools.process_node import ProcessNode

# 初始化服务器
app = Server("operateMysql")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的MySQL工具
    返回:
        list[Tool]: 工具列表，包含多个MySQL操作工具
    """
    return [
        Tool(
            name="query_summary",
            description="该工具第一个调用，从用户输入中提取报错系统名称、问题描述和相关字段信息，用于分析和处理系统报错问题。",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_name": {"type": "string", "description": "报错系统的名称，例如：'寿险合作业务接入平台'、'OA系统'等"},
                    "description": {"type": "string", "description": "报错问题的主要描述，简明扼要地概括问题本质"},
                    "values": {"type": "object", "description": "与报错相关的有用字段，包括但不限于保单号、产品名称、产品代码、业务员代码、网点代码、保费金额等。字段名保持原样(包括中文字段名)"}
                },
                "required": ["system_name", "description", "values"],
            },
        ),
        Tool(
            name="check_id_occupation",
            description="判断证件号在系统中被是否被占用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "证件号"}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="judgment_policy_type",
            description="判断保单是团单还是个单。请提取出完整的，工具所需要的参数，如果有多个，则用英文逗号隔开。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string",
                             "description": "一个或多个保单号。多个保单号用英文逗号分隔。例如：'12345678'或'12345678,87654321'。若为保单号范围，请用英文逗号分隔起始和结束保单号，如'10000001,10000010'。"}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="judgment_policy_finally",
            description="判断保单是否已经全部结算，请提取出完整的，工具所需要的参数，如果有多个，则用英文逗号隔开。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string",
                             "description": "一个或多个保单号。多个保单号用英文逗号分隔。例如：'12345678'或'12345678,87654321'。若为保单号范围，请用英文逗号分隔起始和结束保单号，如'10000001,10000010'。"}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="judgment_policy_status",
            description="判断保单是否已经撤单，请提取出完整的，工具所需要的参数，如果有多个，则用英文逗号隔开。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string",
                             "description": "一个或多个保单号。多个保单号用英文逗号分隔。例如：'12345678'或'12345678,87654321'。若为保单号范围，请用英文逗号分隔起始和结束保单号，如'10000001,10000010'。"}
                },
                "required": ["text"],
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
    elif name == "judgment_policy_type":
        query = arguments.get("text")
        if not query:
            raise ValueError("缺少输入语句")
        return ProcessNode().judgment_policy_type(query)
    elif name == "judgment_policy_finally":
        query = arguments.get("text")
        if not query:
            raise ValueError("缺少输入语句")
        return ProcessNode().judgment_policy_finally(query)
    elif name == "judgment_policy_status":
        query = arguments.get("text")
        if not query:
            raise ValueError("缺少输入语句")
        return ProcessNode().judgment_policy_status(query)
    elif name == "query_summary":
        system_name = arguments.get("system_name")
        description = arguments.get("description")
        values = arguments.get("values")
        if not description and not values:
            raise ValueError("缺少输入语句")
        return ProcessNode().query_summary(system_name, description, values)
    else:
        raise ValueError(f"未知的工具: {name}")


# 创建SSE传输
sse = SseServerTransport("/messages/")

# 创建FastAPI应用
fastapi_app = FastAPI(debug=True)


@fastapi_app.get("/sse")
async def handle_sse(request: Request):
    """处理SSE连接"""
    async with sse.connect_sse(
            request.scope, request.receive, request._send
    ) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

@fastapi_app.get("/")
async def root():
    return "API IS RUNNING"


# 挂载SSE消息处理路由
fastapi_app.mount("/messages", sse.handle_post_message)

if __name__ == "__main__":
    uvicorn.run("mcp_service:fastapi_app", host="0.0.0.0", port=9000, reload=True)
    # print(ProcessNode.system_roster)