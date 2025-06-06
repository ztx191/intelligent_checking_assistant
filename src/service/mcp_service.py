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
    """列出可用的工具
    """
    return [
        Tool(
            name="query_summary",
            description="该工具第一个调用，从用户输入中提取报错系统名称、问题描述和相关字段信息，用于分析和处理系统报错问题。",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_name": {"type": "string",
                                    "description": "报错系统的名称，例如：'寿险合作业务接入平台'、'OA系统'等"},
                    "description": {"type": "string", "description": "报错问题的主要描述，简明扼要地概括问题本质"},
                    "values": {"type": "object",
                               "description": "与报错相关的有用字段，包括但不限于保单号、产品名称、产品代码、业务员代码、网点代码、保费金额等。字段名保持原样(包括中文字段名)。对于表示范围的字段（如'保单号：200472556325167-200472556328407'），应拆分为两个字段，例如'保单号Begin'和'保单号End'（如'保单号Begin: 200472556325167'和'保单号End: 200472556328407'）。检测任何使用连字符、至、到等表示范围的值并进行适当拆分。"}
                },
                "required": ["system_name", "description", "values"]
            }
        ),
        Tool(
            name="get_table_desc",
            description="获取指定表的字段结构信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "要查询的表的名称，需要查询的表名称来源于query_summary返回的系统涉及的可查询资源中的表名称。"}
                },
                "required": ["table_name"]
            },
        ),
        Tool(
            name="get_sql_database_resource",
            description="根据工具get_table_desc获取的表字段信息和用户问题，分析解决问题的步骤，并生成符合MySQL 8.0语法的SQL查询",
            inputSchema={
                "type": "object",
                "properties": {
                    "step": {"type": "string", "description": "解决问题的详细分析步骤，包括思路和解决方案的逻辑推导过程"},
                    "sql": {"type": "string", "description": "符合MySQL 8.0语法的可执行SQL查询语句"}
                },
                "required": ["step"]
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "query_summary":
        system_name = arguments.get("system_name")
        description = arguments.get("description")
        values = arguments.get("values")
        if not description and not values:
            raise ValueError("缺少输入语句")
        return ProcessNode().query_summary(system_name, description, values)
    elif name == "get_table_desc":
        table_name = arguments.get("table_name")
        if not table_name:
            raise ValueError("缺少表名称")
        return ProcessNode.get_table_desc(table_name)
    elif name == "get_sql_database_resource":
        step = arguments.get("step")
        sql = arguments.get("sql")
        if not step and not sql:
            raise ValueError("缺少输入语句")
        return ProcessNode.get_sql_database_resource(sql, step)
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