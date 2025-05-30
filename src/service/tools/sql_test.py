import os

import uvicorn
from mcp.server.sse import SseServerTransport
from pymysql import connect, Error
from mcp.server import Server
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from dotenv import load_dotenv


def get_db_config():
    """从环境变量获取数据库配置信息
    返回:
        dict: 包含数据库连接所需的配置信息
        - host: 数据库主机地址
        - port: 数据库端口
        - user: 数据库用户名
        - password: 数据库密码
        - database: 数据库名称
    异常:
        ValueError: 当必需的配置信息缺失时抛出
    """

    # 加载.env文件
    load_dotenv(r"D:\intelligent_checking_assistant\.env")

    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
    }
    # print(config)
    if not all([config["user"], config["password"], config["database"]]):
        raise ValueError("缺少必需的数据库配置")

    return config


def execute_sql(query: str) -> list[TextContent]:
    """执行SQL查询语句
    参数:
        query (str): 要执行的SQL语句，支持多条语句以分号分隔
    返回:
        list[TextContent]: 包含查询结果的TextContent列表
        - 对于SELECT查询：返回CSV格式的结果，包含列名和数据
        - 对于SHOW TABLES：返回数据库中的所有表名
        - 对于其他查询：返回执行状态和影响行数
        - 多条语句的结果以"---"分隔
    异常:
        Error: 当数据库连接或查询执行失败时抛出
    """
    config = get_db_config()
    try:
        # PyMySQL 连接使用，将自动提交设置为False以支持事务
        with connect(**config, charset='utf8mb4') as conn:
            with conn.cursor() as cursor:
                statements = [stmt.strip() for stmt in query.split(";") if stmt.strip()]
                results = []

                for statement in statements:
                    try:
                        cursor.execute(statement)

                        # 检查语句是否返回了结果集 (SELECT, SHOW, EXPLAIN, etc.)
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()

                            # 将每一行的数据转换为字符串，特殊处理None值
                            formatted_rows = []
                            for row in rows:
                                formatted_row = [
                                    "NULL" if value is None else str(value)
                                    for value in row
                                ]
                                formatted_rows.append(",".join(formatted_row))

                            # 将列名和数据合并为CSV格式
                            results.append(
                                "\n".join([",".join(columns)] + formatted_rows)
                            )

                        # 如果语句没有返回结果集 (INSERT, UPDATE, DELETE, etc.)
                        else:
                            conn.commit()  # 只有在非查询语句时才提交
                            results.append(f"查询执行成功。影响行数: {cursor.rowcount}")

                    except Error as stmt_error:
                        # 单条语句执行出错时，记录错误并继续执行
                        results.append(
                            f"执行语句 '{statement}' 出错: {str(stmt_error)}"
                        )
                        # 可以在这里选择是否继续执行后续语句，目前是继续

                return [TextContent(type="text", text="\n---\n".join(results))]

    except Error as e:
        print(f"执行SQL '{query}' 时出错: {e}")
        return [TextContent(type="text", text=f"执行查询时出错: {str(e)}")]


def get_table_name(text: str) -> list[TextContent]:
    """根据表的中文注释搜索数据库中的表名
    参数:
        text (str): 要搜索的表中文注释关键词
    返回:
        list[TextContent]: 包含查询结果的TextContent列表
        - 返回匹配的表名、数据库名和表注释信息
        - 结果以CSV格式返回，包含列名和数据
    """
    config = get_db_config()
    sql = "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_COMMENT "
    sql += f"FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{config['database']}' AND TABLE_COMMENT LIKE '%{text}%';"
    return execute_sql(sql)


def get_table_desc(text: str) -> list[TextContent]:
    """获取指定表的字段结构信息
    参数:
        text (str): 要查询的表名，多个表名以逗号分隔
    返回:
        list[TextContent]: 包含查询结果的TextContent列表
        - 返回表的字段名、字段注释等信息
        - 结果按表名和字段顺序排序
        - 结果以CSV格式返回，包含列名和数据
    """
    config = get_db_config()
    # 将输入的表名按逗号分割成列表
    table_names = [name.strip() for name in text.split(",")]
    # 构建IN条件
    table_condition = "','".join(table_names)
    sql = "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT "
    sql += (
        f"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '{config['database']}' "
    )
    sql += f"AND TABLE_NAME IN ('{table_condition}') ORDER BY TABLE_NAME, ORDINAL_POSITION;"
    return execute_sql(sql)


def get_lock_tables() -> list[TextContent]:
    sql = """SELECT p2.`HOST`                                                    AS 被阻塞方host, \
                    p2.`USER`                                                    AS 被阻塞方用户, \
                    r.trx_id                                                     AS 被阻塞方事务id, \
                    r.trx_mysql_thread_id                                        AS 被阻塞方线程号, \
                    TIMESTAMPDIFF(SECOND, r.trx_wait_started, CURRENT_TIMESTAMP) AS 等待时间, \
                    r.trx_query                                                  AS 被阻塞的查询, \
                    l.OBJECT_NAME                                                AS 阻塞方锁住的表, \
                    m.LOCK_MODE                                                  AS 被阻塞方的锁模式, \
                    m.LOCK_TYPE AS '被阻塞方的锁类型(表锁还是行锁)', m.INDEX_NAME AS 被阻塞方锁住的索引, \
                    m.OBJECT_SCHEMA                                              AS 被阻塞方锁对象的数据库名, \
                    m.OBJECT_NAME                                                AS 被阻塞方锁对象的表名, \
                    m.LOCK_DATA                                                  AS 被阻塞方事务锁定记录的主键值, \
                    p.`HOST`                                                     AS 阻塞方主机, \
                    p.`USER`                                                     AS 阻塞方用户, \
                    b.trx_id                                                     AS 阻塞方事务id, \
                    b.trx_mysql_thread_id                                        AS 阻塞方线程号, \
                    b.trx_query                                                  AS 阻塞方查询, \
                    l.LOCK_MODE                                                  AS 阻塞方的锁模式, \
                    l.LOCK_TYPE AS '阻塞方的锁类型(表锁还是行锁)', l.INDEX_NAME AS 阻塞方锁住的索引, \
                    l.OBJECT_SCHEMA                                              AS 阻塞方锁对象的数据库名, \
                    l.OBJECT_NAME                                                AS 阻塞方锁对象的表名, \
                    l.LOCK_DATA                                                  AS 阻塞方事务锁定记录的主键值, \
                    IF(p.COMMAND = 'Sleep', CONCAT(p.TIME, ' 秒'), 0)            AS 阻塞方事务空闲的时间
             FROM performance_schema.data_lock_waits w
                      INNER JOIN performance_schema.data_locks l ON w.BLOCKING_ENGINE_LOCK_ID = l.ENGINE_LOCK_ID
                      INNER JOIN performance_schema.data_locks m ON w.REQUESTING_ENGINE_LOCK_ID = m.ENGINE_LOCK_ID
                      INNER JOIN information_schema.INNODB_TRX b ON b.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID
                      INNER JOIN information_schema.INNODB_TRX r ON r.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID
                      INNER JOIN information_schema.PROCESSLIST p ON p.ID = b.trx_mysql_thread_id
                      INNER JOIN information_schema.PROCESSLIST p2 ON p2.ID = r.trx_mysql_thread_id
             ORDER BY 等待时间 DESC;"""

    return execute_sql(sql)


# 初始化服务器
app = Server("operateMysql")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的MySQL工具
    返回:
        list[Tool]: 工具列表，当前仅包含execute_sql工具
    """
    return [
        Tool(
            name="execute_sql",
            description="在MySQL8.0数据库上执行SQL",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要执行的SQL语句"}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_table_name",
            description="根据表中文名搜索数据库中对应的表名",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要搜索的表中文名"}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="get_table_desc",
            description="根据表名搜索数据库中对应的表结构,支持多表查询",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要搜索的表名"}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="get_lock_tables",
            description="获取当前mysql服务器InnoDB 的行级锁",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "execute_sql":
        query = arguments.get("query")
        if not query:
            raise ValueError("缺少查询语句")
        return execute_sql(query)
    elif name == "get_table_name":
        text = arguments.get("text")
        if not text:
            raise ValueError("缺少表信息")
        return get_table_name(text)
    elif name == "get_table_desc":
        text = arguments.get("text")
        if not text:
            raise ValueError("缺少表信息")
        return get_table_desc(text)
    elif name == "get_lock_tables":
        return get_lock_tables()

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

