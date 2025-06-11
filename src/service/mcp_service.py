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
            description="从用户输入中提取报错系统名称、问题描述和相关字段信息，用于分析和处理系统报错问题。若没有检查错误再次检查",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_name": {"type": "string",
                                    "description": "报错系统的名称，例如：'寿险合作业务接入平台'、'OA'等若名称中没有系统就不用带系统"},
                    "description": {"type": "string", "description": "报错问题的主要描述，简明扼要地概括问题本质"},
                    "values": {"type": "object",
                               "description": "与报错相关的有用字段，包括但不限于保单号、产品名称、产品代码、业务员代码、网点代码、保费金额等。字段名保持原样(包括中文字段名)。对于表示范围的字段（如'保单号：200472556325167-200472556328407'），应拆分为两个字段，例如'保单号Begin'和'保单号End'（如'保单号Begin: 200472556325167'和'保单号End: 200472556328407'）。检测任何使用连字符、至、到等表示范围的值并进行适当拆分。"}
                },
                "required": ["system_name", "description", "values"]
            }
        ),
        Tool(
            name="summary_pipeline",
            description="用户问题参考方案查询工具，根据用户的问题描述获取对应的参考内容，该工具返回的内容不一定能完全解决问题，是参考。",
            inputSchema={
                "type": "object",
                "properties": {
                    "problem": {"type": "string",
                                    "description": "用户的问题描述"}
                },
                "required": ["problem"]
            }
        ),
        Tool(
            name="dismantle_step",
            description="步骤总结工具，调用该工具前，你需要输出开始执行下面步骤：调用该工具返回结果，然后输出按照这个步骤内容：步骤内容，调用操作工具。"
                        "该工具用途为从summary_pipeline工具中的参考结果结合用户当前问题总结出解决问题的步骤,一次总结一步并打印输出该步骤，"
                        "然后进行该步骤的相关操作，调用相关操作的工具，这个工具和操作工具相互绑定，总结一个步骤，然后执行相关操作。",
            inputSchema={
                "type": "object",
                "properties": {
                    "step": {"type": "string",
                                "description": "解决问题的步骤，参考用户问题和summary_pipeline工具中的参考结果总结出来，不是直接提取，一次总结一步"}
                },
                "required": ["step"]
            }
        ),
        Tool(
            name="load_system",
            description="操作工具，浏览器进入系统相关操作",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string",
                             "description": "url地址"},
                    "operate": {"type": "string",
                             "description": "在该url界面需要进行的操作"},
                    "values": {"type": "string",
                             "description": "操作需要的相关参数"}

                },
                "required": ["url", "operate", "values"]
            }
        ),
        Tool(
            name="get_table_desc",
            description="需要进行sql数据库操作时，获取指定表的字段结构信息工具，为后续get_sql_database_resource工具提供分析上下文",
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
            description="操作工具，sql数据库查询检测工具，若dismantle_step工具中提取的步骤需要查询sql数据库，"
                        "则根据工具get_table_desc获取的表字段信息和相关步骤并生成符合MySQL 8.0语法的SQL查询。",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "符合MySQL 8.0语法的可执行SQL查询语句，多个sql语句用;隔开"}
                },
                "required": ["sql"]
            },
        ),
        Tool(
            name="finally_summary",
            description="方案汇总，获取用户问题描述，汇总get_sql_database_resource的内容，提取总结出造成该问题的原因；"
                        "查询解决该问题的步骤；"
                        "解决该问题的方案",
            inputSchema={
                "type": "object",
                "properties": {
                    "problem": {"type": "string", "description": "用户提出的问题"},
                    "reason": {"type": "string", "description": "造成该问题的原因"},
                    "step": {"type": "string", "description": "查询解决该问题的步骤，包含步骤，若该步骤有相关资源查询则加上该步骤对应的查询语句及结果"},
                    "solution": {"type": "string", "description": "解决用户问题的方案"},
                    "rules": {"type": "string", "description": "解决用户问题的方案对应的规则"}
                },
                "required": ["problem", "reason", "step", "solution"]
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
    elif name == "summary_pipeline":
        problem = arguments.get("problem")
        if not problem:
            raise ValueError("缺少输入语句")
        return ProcessNode.summary_pipeline(problem)
    elif name == "dismantle_step":
        step = arguments.get("step")
        if not step:
            raise ValueError("缺少输入语句")
        return ProcessNode.dismantle_step(step)
    elif name == "load_system":
        url = arguments.get("url")
        operate = arguments.get("operate")
        values = arguments.get("values")
        if not url and not operate and not values:
            raise ValueError("缺少输入语句")
        return ProcessNode.load_system(url, operate, values)
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
        return ProcessNode.get_sql_database_resource(sql)
    elif name == "finally_summary":
        problem = arguments.get("problem")
        reason = arguments.get("reason")
        step = arguments.get("step")
        solution = arguments.get("solution")
        rules = arguments.get("rules")
        if not problem and not reason and not step and not solution:
            raise ValueError("缺少输入语句")
        return ProcessNode.finally_summary(problem, reason, step, solution, rules)
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