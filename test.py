from postgres import Postgres
import private_data

db = Postgres(url=private_data.postgres_url)
s = ""
s += "SELECT"
s += " table_schema"
s += ", table_name"
s += " FROM information_schema.tables"
# s += " WHERE"
# s += " ("
# s += " table_schema = 'public'"
# s += " )"
s += " ORDER BY table_schema, table_name;"

with db.get_cursor() as cursor:
	cursor.execute(s)
	list_tables = cursor.fetchall()

for t_name_table in list_tables:
	print(str(t_name_table) + "\n")

SELECT table_schema, table_name FROM information_schema.tables ORDER BY table_schema, table_name;