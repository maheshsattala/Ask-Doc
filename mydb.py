import mysql.connector

database = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Mahesh@1862'
)

#   prepare a cursor object
cursorObject = database.cursor()

#   Create a database
cursorObject.execute("CREATE DATABASE ask_doc_db")

print("DB CREATED!")
