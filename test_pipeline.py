import asyncio
import sqlite3
from api.main import run_pipeline, init_db

init_db()
conn = sqlite3.connect("db/sitegpt.db")
conn.execute("INSERT OR REPLACE INTO bots (bot_id, owner_id, url) VALUES ('test_bot_mirone', 1, 'https://mironebd.com')")
conn.commit()
conn.close()

asyncio.run(run_pipeline('test_bot_mirone', 'https://mironebd.com'))
