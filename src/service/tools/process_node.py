import json
from typing import Optional
from src.clients.llm_client import LLMService
from src.clients.mysql_client import MySQLClient
from mcp.types import TextContent


from src.prompts.sop import SYSTEM_PROMPT


class ProcessNode:
    client = MySQLClient()
    llm_client = LLMService()
    with open(r"..\data_source\system_database.json", "r", encoding="utf-8") as f:
        system_roster = json.load(f)

    @classmethod
    def query_summary(cls, system_name: str, description: str, values: dict) -> list[TextContent]:
        """
        从用户输入中提取报错系统名称、问题描述和相关字段信息，用于分析和处理系统报错问题
        优化：能够重复调用直到获取正确字段，或者多次未获取到不再调用后续工具
        :param system_name: 报错系统的名称，例如：'寿险合作业务接入平台'、'OA系统'等
        :param description: 报错问题的主要描述，简明扼要地概括问题本质
        :param values: 与报错相关的有用字段，包括但不限于保单号、产品名称、产品代码、业务员代码、网点代码、保费金额等。字段名保持原样(包括中文字段名)
        :return:
        """
        if not system_name:
            return [TextContent(type="text", text="未发现报错系统名称，请输入出现问题的报错系统名称。")]
        elif system_name not in list(cls.system_roster.keys()):
            return [TextContent(type="text", text=f"系统名称：{system_name}未正确识别，请检查系统名称是否输入正确，或者该系统不在系统列表中。")]
        else:
            text_list = list()
            for k, v in cls.system_roster[system_name].items():
                text_list.append(f"{k}: {v['description']}")
            text_list  = '\n'.join(text_list)
            return [TextContent(type="text", text=f"报错系统为：{system_name}，问题描述为：{description}，问题涉及的相关字段为：{values}。" +
                                                  f"系统包含的资源为：{text_list}")]

    @classmethod
    def summary_pipeline(cls, problem: str) -> list[TextContent]:
        """
        根据用户的问题描述检索已有的sop生成解决用户问题的pipeline
        :param problem: 用户的问题描述
        """
        query = f"问题描述为：{problem}"
        _res = cls.llm_client.chat(SYSTEM_PROMPT, query)
        # _res = json.loads(_res)
        pipeline = _res
        return [TextContent(type="text", text=f"根据问题描述获取的可以参考的内容为：\n{pipeline}。\n参考获取内容，总结解决步骤，调用工具。" +
                                              "注意：不用返回该工具的结果！")]

    @classmethod
    def dismantle_step(cls, step) -> list[TextContent]:
        """
        从上下文中提取解决问题的步骤
        :param step: 解决问题的步骤
        :return:
        """
        return [TextContent(type="text", text=f"根据问题描述获取的详细步骤为：\n{step}\n根据上面提到的步骤，调用可以使用的工具。" +
                            "注意：输出该工具结果")]

    @classmethod
    def load_system(cls, url: str, operate: str, values: dict):
        """
        有关浏览器进入系统，系统相关操作
        :param operate: 操作
        :param url: url
        :param values: 相关参数
        :return:
        """
        return [TextContent(type="text", text=f"进入系统成功，开始进行下一步操作")]

    @classmethod
    def get_logging_info(cls, logging_name: str) -> list[TextContent]:
        pass



    @classmethod
    def get_table_desc(cls, table_name: str) -> list[TextContent]:
        """
        获取指定表的字段结构信息
        :param table_name: 要查询的表的名称，需要查询的表名称来源于query_summary返回的系统涉及的可查询资源中的表名称。
        :return:
        """
        sql = "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT "
        sql += (
            f"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '{cls.client.config.mysql_database}' "
        )
        sql += f"AND TABLE_NAME IN ('{table_name}') ORDER BY TABLE_NAME, ORDINAL_POSITION;"
        _res = cls.client.execute_query(sql)
        return [TextContent(type="text", text=f"表结构信息为：\n{json.dumps(_res['message'], ensure_ascii=False)}")]


    @classmethod
    def get_sql_database_resource(cls, sql: str) -> list[TextContent]:
        """
        根据表结构信息和用户问题，分析解决问题的步骤，并生成符合MySQL 8.0语法的SQL查询
        :param sql: 符合MySQL 8.0语法的可执行SQL查询语句
        :return:
        """
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        results = []
        for statement in statements:
            _res = cls.client.execute_query(statement)
            results.append(f"{statement}的执行结果为：{_res['message']}")
        results = "\n".join(results)
        return [TextContent(type="text", text=f"SQL结果执行为：\n{results}")]

    @classmethod
    def finally_summary(cls, problem: str, reason: str, step: str, solution: str, rules: Optional[str]) -> list[TextContent]:
        """
        汇总
        :param problem: 问题
        :param reason: 原因
        :param step: 步骤
        :param solution: 解决方方案
        :param rules: 系统规则
        :return:
        """
        if rules:
            res = f"""
            | 问题现象 | 原因分析 | 解决步骤 | 解决方案 | 系统规则 |
            |:-------:|:-------:|:-------:|:-------:|:-------:|
            | {problem} | {reason} | {step} | {solution} | {solution} |
            """
        else:
            res = f"""
            | 问题现象 | 原因分析 | 解决步骤 | 解决方案 |
            |:-------:|:-------:|:-------:|:-------:|
            | {problem} | {reason} | {step} | {solution} |
            """
        return [TextContent(type="text", text=res)]
    @classmethod
    def check_id_occupation(cls, text: str) -> list[TextContent]:
        """
        证件号占用问题。判断证件号是否被其他客户使用，在系统中被是否被占用
        :param text: 证件号
        :return:
        """
        cls.client.connect()
        sql = f"""select card_no, customer_name from t_customercenter_customer where certno={text};"""
        try:
            _res = cls.client.execute_query(sql)
            if  _res:
                return [TextContent(type="text", text=f"查询结果存在记录，该证件号码{text}对应的客户信息存在，客户姓名为：{_res[0]['customer_name']}")]
            else:
                return [TextContent(type="text", text=f"没有证件号{text}的相关信息，或者在该证件号在系统中未被占用。")]
        except  Exception as e:
            return [TextContent(type="text", text=f"执行查询时出错: {str(e)}")]

    @classmethod
    def judgment_policy_type(cls, text: str) -> list[TextContent]:
        """
        交费报错，无可结算单问题。判断保单是团单还是个单
        :param text: 保单号。若有多个保单号，用英文逗号隔开
        :return:
        """
        cls.client.connect()
        if len(text.split(",")) > 1:
            l, r = text.split(",")
            sql = f"""select count(1) resu from  grpcon  where gpolicyno between '{l}' and '{r}';"""
        else:
            sql = f"""select count(1) resu from  grpcon  where gpolicyno = '{text}';"""

        try:
            _res = cls.client.execute_query(sql)
            if  _res[0]['resu'] == 0:
                return [TextContent(type="text", text=f"保单号{text}对应的保单类型为个单。界面选择个险保费批量结算功能。"
                                                      f"保费结算分个单和团单且个单团单对应不同的结算功能，您是否是在个单上结算？"
                                    )]
            else:
                return [TextContent(type="text", text=f"保单号{text}对应的保单类型为团单。界面选择团险保费批量结算功能。"
                                                      f"保费结算分个单和团单且个单团单对应不同的结算功能，您是否在团单上结算？"
                                    )]
        except Exception as e:
            return [TextContent(type="text", text=f"执行查询时出错: {str(e)}")]

    @classmethod
    def judgment_policy_finally(cls, text: str) -> list[TextContent]:
        """
        判断保单是否已经全部结算，已经结算的保单无需再结算；返回未结算的保单
        :param text: 保单号。若有多个保单号，用英文逗号隔开
        :return:
        """
        cls.client.connect()
        if len(text.split(",")) > 1:
            l, r = text.split(",")
        else:
            l, r = text, text
        sql = f"""select count(1) resu from cn_water_yccd a where  appno  between '{l}' and '{r}' and optype='101';"""
        try:
            _res = cls.client.execute_query(sql)
            count = abs(int(r) - int(l))
            if  _res[0]['resu'] == count:
                return [TextContent(type="text", text=f"保单号{text}对应的保单已经全部结算，已结算不允许二次结算，所以无需再结算。")]
            else:
                sql = f"""select appno from  cn_water_yccd a where  appno  between '{l}' and '{r}' and optype not in('101','201') ;"""
                _res = cls.client.execute_query(sql)
                if _res:
                    policies = [i['appno'] for i in _res]
                    return [TextContent(type="text", text=f"保单号{text}对应的保单未全部结算。未结算的保单号为：{'，'.join(policies)}")]
                else:
                    return [TextContent(type="text", text=f"保单号{text}对应的保单中无未结算保单。存在其他问题，等后续检查。")]
        except Exception as e:
            return [TextContent(type="text", text=f"执行查询时出错: {str(e)}")]

    @classmethod
    def judgment_policy_status(cls, text: str) -> list[TextContent]:
        """
        判断保单是否已经撤单
        :param text: 保单号。若有多个保单号，用英文逗号隔开
        :return:
        """
        cls.client.connect()
        if len(text.split(",")) > 1:
            l, r = text.split(",")
        else:
            l, r = text, text
        sql = f"""select count(1) resu  from  cn_water_yccd a where  appno  between '{l}' and '{r}' and optype='201' and subamt>0;"""
        try:
            _res = cls.client.execute_query(sql)
            count = abs(int(r) - int(l))
            if _res[0]['resu'] == count:
                return [TextContent(type="text", text=f"保单号{text}对应的保单已经全部撤单。已撤单的不在结算范围，所以无需再结算。")]
            else:
                sql = f"""select appno from  cn_water_yccd a where  appno  between '{l}' and '{r}' and optype not in('101','201') ;"""
                _res = cls.client.execute_query(sql)
                if _res:
                    policies = [i['appno'] for i in _res]
                    return [TextContent(type="text",
                                        text=f"保单号{text}对应的保单未全部结算。未结算的保单号为：{'，'.join(policies)}")]
                else:
                    return [TextContent(type="text", text=f"保单号{text}对应的保单中无未结算保单。存在其他问题，等后续检查。")]
        except Exception as e:
            return [TextContent(type="text", text=f"执行查询时出错: {str(e)}")]