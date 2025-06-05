import json

from src.clients.mysql_client import MySQLClient
from mcp.types import TextContent
class ProcessNode:
    client = MySQLClient()
    with open(r"..\data_source\system_database.json", "r", encoding="utf-8") as f:
        system_roster = json.load(f)

    @classmethod
    def query_summary(cls, system_name: str, description: str, values: dict):
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
            """
            伪代码，查找描述是否能匹配已有sop，后续实现
            if description like sops:
                get sop
                return [TextContent(type="text", text=f"报错系统为：{system_name}，请根据已有的{sop}方案进行检查")]
            else:
            """
            text_list = list()
            for k, v in cls.system_roster[system_name].items():
                text_list.append(f"{k}: {v['description']}")
            return [TextContent(type="text", text=f"报错系统为：{system_name}，问题描述为：{description}，问题涉及的相关字段为：{values}。"
                                                  + "该系统涉及的可查询资源有：\n{}".format('\n'.join(text_list)))]
        # return [TextContent(type="text", text=f"报错系统为：{system_name}，问题描述为：{description}，相关字段为：{values}")]

    @classmethod
    def get_table_desc(cls, ):
        pass

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