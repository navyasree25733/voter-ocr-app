import os
import mysql.connector

def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST", "localhost"),
        user=os.getenv("MYSQLUSER", "root"),
        password=os.getenv("MYSQLPASSWORD", "123456789@"),
        database=os.getenv("MYSQLDATABASE", "voter_ocr_db"),
        port=int(os.getenv("MYSQLPORT", 3306))
    )


# # import mysql.connector

# # def get_db():
# #     return mysql.connector.connect(
# #         host="localhost",
# #         user="root",
# #         password="123456789@",        # 🔴 change
# #         database="voter_ocr_db"
# #     )
# import os
# import mysql.connector

# def get_db():
#     return mysql.connector.connect(
#         host=os.getenv("DB_HOST"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         database=os.getenv("DB_NAME"),
#         port=int(os.getenv("DB_PORT", 3306))
#     )
