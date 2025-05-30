import pymysql

# 建立数据库连接
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='12345',
    charset='utf8mb4'
)

try:
    # 创建游标对象
    cursor = connection.cursor()

    # 创建数据库
    cursor.execute("CREATE DATABASE IF NOT EXISTS batchread")
    cursor.execute("USE batchread")

    # 创建客户中心表
    create_table_sql = """
                       CREATE TABLE IF NOT EXISTS T_CUSTOMERCENTER_CUSTOMER \
                       ( \
                           card_no \
                           VARCHAR \
                       ( \
                           50 \
                       ) PRIMARY KEY,
                           customer_name VARCHAR \
                       ( \
                           100 \
                       ) NOT NULL,
                           certno VARCHAR \
                       ( \
                           18 \
                       ) NOT NULL,
                           create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                           ) \
                       """
    cursor.execute(create_table_sql)

    # 准备插入20条数据
    customer_data = [
        ('C00001', '张雨涵', '410185199003317654'),
        ('C00002', '李四', '410185199107223698'),
        ('C00003', '王五', '410185199205165478'),
        ('C00004', '赵六', '410185199308127856'),
        ('C00005', '钱七', '410185199409183265'),
        ('C00006', '孙八', '410185199510297412'),
        ('C00007', '周九', '410185199611305698'),
        ('C00008', '吴十', '410185199712314587'),
        ('C00009', '郑十一', '410185199801235689'),
        ('C00010', '王十二', '410185199902146398'),
        ('C00011', '刘一', '410185199003257412'),
        ('C00012', '陈二', '410185199104168523'),
        ('C00013', '杨三', '410185199205279856'),
        ('C00014', '黄四', '410185199306184569'),
        ('C00015', '周五', '410185199407193574'),
        ('C00016', '吴六', '410185199508204563'),
        ('C00017', '郑七', '410185199609213698'),
        ('C00018', '王八', '410185199710224785'),
        ('C00019', '冯九', '410185199811237845'),
        ('C00020', '陈十', '410185199912246398')
    ]

    # 插入数据
    insert_sql = "INSERT INTO T_CUSTOMERCENTER_CUSTOMER (card_no, customer_name, certno) VALUES (%s, %s, %s)"
    cursor.executemany(insert_sql, customer_data)

    # 提交事务
    connection.commit()

    # 验证插入的数据
    cursor.execute("SELECT card_no, customer_name FROM T_CUSTOMERCENTER_CUSTOMER WHERE certno='410185199003317654'")
    result = cursor.fetchone()
    if result:
        print(f"查询结果 - 客户号: {result[0]}, 客户名称: {result[1]}")

    print("数据库创建成功，表创建成功，20条数据插入成功！")

except Exception as e:
    print(f"发生错误: {e}")
    connection.rollback()

finally:
    # 关闭游标和连接
    cursor.close()
    connection.close()
