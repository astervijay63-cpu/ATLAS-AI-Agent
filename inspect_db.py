import sqlite3
conn = sqlite3.connect(r'D:\AGENTIC AI VIT\zip_extract\-EMR-Natural-Language-Query-Interface-main\emr_local.db')
cur = conn.cursor()
print(cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
for (name,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print('TABLE', name)
    print(cur.execute(f'PRAGMA table_info({name})').fetchall())
    print('---')
