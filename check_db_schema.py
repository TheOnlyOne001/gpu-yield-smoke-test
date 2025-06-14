import psycopg2

# Connect to database
conn = psycopg2.connect('postgresql://postgres:password@localhost:5432/gpu_yield_db')
cur = conn.cursor()

# Get table names
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
tables = cur.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

# Check for user-related tables
for table in tables:
    table_name = table[0]
    if 'user' in table_name.lower():
        print(f'\nColumns in {table_name}:')
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';")
        columns = cur.fetchall()
        for column in columns:
            print(f'  {column[0]}')

conn.close()
