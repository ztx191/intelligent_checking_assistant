from src.clients.mysql_client import MySQLClient
from mcp.types import TextContent
class ProcessNode:
    client = MySQLClient()
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
                return [TextContent(type="text", text=f"保单号{text}对应的保单类型为个单。界面选择个险保费批量结算功能")]
            else:
                return [TextContent(type="text", text=f"保单号{text}对应的保单类型为团单。界面选择团险保费批量结算功能。")]
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
                return [TextContent(type="text", text=f"保单号{text}对应的保单已经全部结算。无需再结算。")]
            else:
                sql = f"""select appno from  cn_water_yccd a where  appno  between '{l}' and '{r}' and optype not in('101','201') ;"""
                _res = cls.client.execute_query(sql)
                policies = [i['appno'] for i in _res]
                return [TextContent(type="text", text=f"保单号{text}对应的保单未全部结算。未结算的保单号为：{'，'.join(policies)}")]
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
        sql = f"""select count(1) resu from cn_water_yccd a where  appno  between '{l}' and '{r}' and optype='101';"""
        try:
            _res = cls.client.execute_query(sql)
            count = abs(int(r) - int(l))
            if _res[0]['resu'] == count:
                return [TextContent(type="text", text=f"保单号{text}对应的保单已经全部结算。无需再结算。")]
            else:
                sql = f"""select appno from  cn_water_yccd a where  appno  between '{l}' and '{r}' and optype not in('101','201') ;"""
                _res = cls.client.execute_query(sql)
                policies = [i['appno'] for i in _res]
                return [TextContent(type="text",
                                    text=f"保单号{text}对应的保单未全部结算。未结算的保单号为：{'，'.join(policies)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"执行查询时出错: {str(e)}")]
