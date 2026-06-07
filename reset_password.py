import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_pw = pwd_context.hash("admin123")

conn = sqlite3.connect("db/sitegpt.db")
conn.execute("UPDATE users SET password_hash = ? WHERE email = 'admin@botbro.com'", (hashed_pw,))
conn.commit()
conn.close()
print("Password reset to admin123")
