import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()

# Выполнение запроса SQL для выборки всех записей из таблицы expenses
cursor.execute("SELECT * FROM expenses")

# Получение результатов запроса
rows = cursor.fetchall()

# Вывод результатов или выполнение других операций
for row in rows:
    print(row)

# Закрытие соединения с базой данных
conn.close()
