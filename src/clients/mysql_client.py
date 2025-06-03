import os
import pymysql
from pydantic import BaseModel
import datetime
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Union, Tuple
from contextlib import contextmanager


load_dotenv("../.env")


class MySQLModel(BaseModel):
    mysql_host: str = os.getenv("MYSQL_HOST")
    mysql_port: int = int(os.getenv("MYSQL_PORT"))
    mysql_user: str = os.getenv("MYSQL_USER")
    mysql_password: str = os.getenv("MYSQL_PASSWORD")
    mysql_database: str = os.getenv("MYSQL_DATABASE")
    mysql_charset: str = os.getenv("MYSQL_CHARSET")


class MySQLClient:
    def __init__(self, config: MySQLModel = None):
        self.config = config if config else MySQLModel()
        self.connection = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config.mysql_host,
                port=self.config.mysql_port,
                user=self.config.mysql_user,
                password=self.config.mysql_password,
                database=self.config.mysql_database,
                charset=self.config.mysql_charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            return self.connection
        except pymysql.Error as e:
            raise Exception(f"MySQL连接失败: {e}")

    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = self.connect() if not self.connection else self.connection
            yield conn
        finally:
            if conn and conn != self.connection:
                conn.close()

    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def _format_datetime(self, value):
        """格式化日期时间对象为字符串"""
        if isinstance(value, datetime.datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, datetime.date):
            return value.strftime('%Y-%m-%d')
        elif isinstance(value, datetime.time):
            return value.strftime('%H:%M:%S')
        return value

    def _process_row(self, row):
        """处理结果行中的日期时间类型"""
        if not row:
            return row
        return {k: self._format_datetime(v) for k, v in row.items()}

    def _process_results(self, results):
        """处理查询结果集中的日期时间类型"""
        if not results:
            return results
        return [self._process_row(row) for row in results]

    def execute_query(self, sql: str, params: Union[Dict, List, Tuple] = None) -> List[Dict[str, Any]]:
        """执行查询SQL语句并返回格式化后的结果"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return self._process_results(results)

    def execute_one(self, sql: str, params: Union[Dict, List, Tuple] = None) -> Optional[Dict[str, Any]]:
        """执行查询SQL语句并返回格式化后的单条结果"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return self._process_row(result)

    def execute(self, sql: str, params: Union[Dict, List, Tuple] = None) -> int:
        """
        执行非查询SQL语句（如INSERT, UPDATE, DELETE）

        Args:
            sql: SQL语句
            params: SQL参数

        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                rows = cursor.execute(sql, params)
                conn.commit()
                return rows

    def execute_many(self, sql: str, params_list: List[Union[Dict, List, Tuple]]) -> int:
        """
        批量执行SQL语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                rows = cursor.executemany(sql, params_list)
                conn.commit()
                return rows

    def execute_script(self, sql_script: str) -> None:
        """
        执行SQL脚本

        Args:
            sql_script: 包含多条SQL语句的脚本
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for statement in sql_script.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
                conn.commit()

    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            表是否存在
        """
        sql = """
              SELECT COUNT(*) as count
              FROM information_schema.tables
              WHERE table_schema = %s \
                AND table_name = %s \
              """
        with self.get_cursor() as cursor:
            cursor.execute(sql, (self.config.mysql_database, table_name))
            result = cursor.fetchone()
            return result['count'] > 0


if __name__ == '__main__':
    mysql_client = MySQLClient()
    mysql_client.connect()
    print(mysql_client.execute_query("select count(1) resu from  grpcon   where  gpolicyno between 200472556325167 and 200472556328407;"))