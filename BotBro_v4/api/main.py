from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
import os
import sqlite3
import uuid
from crawler.scraper import Scraper, FacebookScraper
from crawler.vectorizer import vectorize_content
import asyncio
import json
from typing import Optional
import base64

# Security Config
SECRET_KEY = "SUPER_SECRET_interactai_KEY" # In production, use env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401, detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    conn = sqlite3.connect(DB_PATH)
    user = conn.execute(
        "SELECT id, email, plan, is_admin FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    if user is None:
        raise credentials_exception
    return {
        "id": user[0],
        "email": user[1],
        "plan": user[2] or "Hobby",
        "is_admin": bool(user[3])
    }

async def require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

app = FastAPI()

# Enable CORS for the widget and dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "db", "sitegpt.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE,
                  password_hash TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS bots 
                 (bot_id TEXT PRIMARY KEY, 
                  url TEXT, 
                  facebook_url TEXT, 
                  status TEXT, 
                  suggested_questions TEXT, 
                  primary_color TEXT DEFAULT '#00d2ff',
                  secondary_color TEXT DEFAULT '#6366f1',
                  bot_name TEXT DEFAULT 'Site Assistant',
                  business_name TEXT,
                  welcome_msg TEXT DEFAULT "Hi! I've learned your site content. Test me here!",
                  avatar_url TEXT,
                  lead_capture_enabled INTEGER DEFAULT 0,
                  owner_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS leads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bot_id TEXT,
                  contact_info TEXT,
                  last_message TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  bot_id TEXT,
                  role TEXT,
                  content TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (session_id TEXT PRIMARY KEY,
                  bot_id TEXT,
                  summary TEXT,
                  intent TEXT,
                  sentiment TEXT,
                  is_lead INTEGER DEFAULT 0,
                  lead_score INTEGER,
                  transcript TEXT,
                  ended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id TEXT PRIMARY KEY,
                  bot_id TEXT,
                  session_id TEXT,
                  customer_name TEXT,
                  customer_phone TEXT,
                  customer_email TEXT,
                  delivery_address TEXT,
                  items TEXT,
                  total TEXT,
                  status TEXT DEFAULT 'pending',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # bKash Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS bkash_payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  plan TEXT,
                  amount REAL,
                  bkash_txn_id TEXT UNIQUE,
                  status TEXT DEFAULT 'pending',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Migration: Add columns if they don't exist
    columns = [
        ("suggested_questions", "TEXT"),
        ("primary_color", "TEXT DEFAULT '#00d2ff'"),
        ("secondary_color", "TEXT DEFAULT '#6366f1'"),
        ("bot_name", "TEXT DEFAULT 'Site Assistant'"),
        ("business_name", "TEXT"),
        ("welcome_msg", "TEXT DEFAULT \"Hi! I've learned your site content. Test me here!\""),
        ("avatar_url", "TEXT"),
        ("lead_capture_enabled", "INTEGER DEFAULT 0"),
        ("owner_id", "INTEGER")
    ]
    for col_name, col_type in columns:
        try:
            c.execute(f"ALTER TABLE bots ADD COLUMN {col_name} {col_type}")
        except:
            pass

    # User Migrations
    user_migrations = [
        "ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'Free'",
        "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
    ]
    for migration in user_migrations:
        try:
            c.execute(migration)
        except:
            pass

    # Seed admin account
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@editians.com")
    existing_admin = c.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
    if existing_admin:
        c.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (ADMIN_EMAIL,))

    # Add site_summary column to bots if missing
    try:
        c.execute("ALTER TABLE bots ADD COLUMN site_summary TEXT")
        c.execute("ALTER TABLE bots ADD COLUMN site_summary_bn TEXT")
    except:
        pass

    conn.commit()
    conn.close()

init_db()

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBiXT5dyBsgPDmd8dsbUi_WINJs_XE1iho")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')

# Initialize ChromaDB client
client = chromadb.PersistentClient(path="chroma_db")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

class BotCreateRequest(BaseModel):
    url: str
    facebook_url: Optional[str] = None

class QueryRequest(BaseModel):
    bot_id: str
    query: str
    session_id: str = "default_session"
    image_base64: Optional[str] = None

class SessionEndRequest(BaseModel):
    session_id: str

class TrainRequest(BaseModel):
    bot_id: str
    text: str

async def run_pipeline(bot_id: str, url: str, facebook_url: str = None):
    try:
        content_items = []
        
        # 1. Scraping Website
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE bots SET status = 'reading_pages' WHERE bot_id = ?", (bot_id,))
        conn.commit()
        
        scraper = Scraper()
        await scraper.start()
        try:
            # Give the scraper a generous timeout — multi-page crawl takes longer
            web_text = await asyncio.wait_for(scraper.scrape_url(url), timeout=120)
        except asyncio.TimeoutError:
            print(f"Scraper timed out for {bot_id}, proceeding with partial content")
            web_text = None
        finally:
            try:
                await scraper.stop()
            except:
                pass
        
        if web_text:
            content_items.append({"text": web_text, "source_type": "website"})
            conn.execute("UPDATE bots SET status = 'pages_scraped' WHERE bot_id = ?", (bot_id,))
            conn.commit()

        # 2. Scraping Facebook (if provided)
        if facebook_url:
            conn.execute("UPDATE bots SET status = 'reading_facebook' WHERE bot_id = ?", (bot_id,))
            conn.commit()
            
            fb_scraper = FacebookScraper()
            await fb_scraper.start()
            try:
                fb_text = await asyncio.wait_for(fb_scraper.scrape_page(facebook_url), timeout=60)
            except asyncio.TimeoutError:
                fb_text = None
            finally:
                try:
                    await fb_scraper.stop()
                except:
                    pass
            
            if fb_text:
                content_items.append({"text": fb_text, "source_type": "facebook"})

        if not content_items:
            raise Exception("No content scraped from any source")

        # 3. Update status to 'vectorizing'
        conn.execute("UPDATE bots SET status = 'vectorizing' WHERE bot_id = ?", (bot_id,))
        conn.commit()

        # 4. Vectorize
        vectorize_content(content_items, collection_name=bot_id)

        # 5. Extract Business Name + Generate Site Summary
        combined_text = "\n\n".join([item['text'][:6000] for item in content_items])
        row = conn.execute("SELECT business_name, site_summary FROM bots WHERE bot_id = ?", (bot_id,)).fetchone()

        biz_name_extracted = row[0] if row else None
        if not biz_name_extracted:
            try:
                name_prompt = f"Extract ONLY the official business name from this website content. Return just the name, nothing else.\nContent:\n{combined_text[:2000]}"
                res = model.generate_content(name_prompt)
                biz_name_extracted = res.text.strip()[:100]
                conn.execute("UPDATE bots SET business_name = ? WHERE bot_id = ?", (biz_name_extracted, bot_id))
                conn.commit()
            except Exception as e:
                print(f"Name extraction error: {e}")

        # 5b. AI-powered Product Catalog Extraction
        # Use Gemini to intelligently extract ALL products/services with names and prices
        try:
            conn.execute("UPDATE bots SET status = 'extracting products' WHERE bot_id = ?", (bot_id,))
            conn.commit()
            
            catalog_prompt = f"""You are analyzing website content to extract a complete, structured product/service catalog.

Extract ALL products, services, menu items, packages, or offerings mentioned. For each item include:
- Name/model (exact as listed)
- Price (if mentioned)
- Key features or description (brief)

Format as a clean list. If prices aren't mentioned, just list names and descriptions.
If there are no specific products (e.g., it's a blog), say "NO_PRODUCTS".

Website content:
{combined_text[:8000]}

PRODUCT/SERVICE CATALOG:"""
            
            catalog_res = model.generate_content(catalog_prompt)
            catalog_text = catalog_res.text.strip()
            
            if catalog_text and "NO_PRODUCTS" not in catalog_text and len(catalog_text) > 50:
                # Store catalog in DB
                try:
                    conn.execute("ALTER TABLE bots ADD COLUMN product_catalog TEXT")
                except:
                    pass
                conn.execute("UPDATE bots SET product_catalog = ? WHERE bot_id = ?", (catalog_text, bot_id))
                conn.commit()
                
                # Add catalog as high-priority chunks to vector store (with 5x weight)
                from crawler.vectorizer import vectorize_content as vc
                catalog_items = [{"text": f"COMPLETE PRODUCT & SERVICE CATALOG:\n{catalog_text}", "source_type": "product_catalog"}]
                
                # Add directly to the existing collection 5 times for strong retrieval
                import chromadb as cdb
                from chromadb.utils import embedding_functions as ef
                chroma_client = cdb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_db"))
                sent_ef = ef.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
                collection = chroma_client.get_or_create_collection(name=bot_id, embedding_function=sent_ef)
                
                catalog_chunk = f"COMPLETE PRODUCT & SERVICE CATALOG:\n{catalog_text}"
                for i in range(5):
                    collection.add(
                        documents=[catalog_chunk],
                        metadatas=[{"source": "product_catalog", "type": "product", "priority": "high", "copy": i}],
                        ids=[f"ai_catalog_{i}_{os.urandom(4).hex()}"]
                    )
                print(f"Product catalog extracted and stored for {bot_id}: {len(catalog_text)} chars")
        except Exception as e:
            print(f"Product catalog extraction error (non-fatal): {e}")

        # 6. Generate Site Summary (English + Bangla)
        if not (row and row[1]):
            try:
                summary_prompt = f"""You are a business analyst. Read this website content and write a clear, engaging summary in 3-4 sentences covering: what this business does, their main products/services, and their unique value proposition.

Website content:
{combined_text[:5000]}

Write a professional, human-friendly summary in English:"""
                summary_res = model.generate_content(summary_prompt)
                summary_en = summary_res.text.strip()

                # Translate to Bangla
                bn_prompt = f"Translate this business summary to fluent, natural Bengali (Bangla). Keep it professional and engaging:\n\n{summary_en}"
                bn_res = model.generate_content(bn_prompt)
                summary_bn = bn_res.text.strip()

                conn.execute(
                    "UPDATE bots SET site_summary = ?, site_summary_bn = ? WHERE bot_id = ?",
                    (summary_en, summary_bn, bot_id)
                )
                conn.commit()
                print(f"Summary generated for {bot_id}")
            except Exception as e:
                print(f"Summary generation error: {e}")

        # 7. Done
        conn.execute("UPDATE bots SET status = 'ready' WHERE bot_id = ?", (bot_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Pipeline error for {bot_id}: {e}")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE bots SET status = 'error' WHERE bot_id = ?", (bot_id,))
        conn.commit()
        conn.close()

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (user.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = get_password_hash(user.password)
    cursor = conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (user.email, hashed_pw))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "email": user.email}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute(
        "SELECT email, password_hash, is_admin, plan FROM users WHERE email = ?",
        (form_data.username,)
    ).fetchone()
    conn.close()
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={
        "sub": user[0],
        "is_admin": bool(user[2]),
        "plan": user[3] or "Hobby"
    })
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ─────────────────────────────────────────────────────────
# BKASH PAYMENT ENDPOINTS
# ─────────────────────────────────────────────────────────

class BkashPaymentRequest(BaseModel):
    plan: str
    amount: float
    bkash_txn_id: str

@app.post("/bkash-payment")
async def submit_bkash_payment(request: BkashPaymentRequest, current_user: dict = Depends(get_current_user)):
    valid_plans = ["Basic", "Pro"]
    if request.plan not in valid_plans:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if not request.bkash_txn_id or len(request.bkash_txn_id) < 6:
        raise HTTPException(status_code=400, detail="Invalid Transaction ID")
    conn = sqlite3.connect(DB_PATH)
    # Check for duplicate TXN ID
    existing = conn.execute(
        "SELECT id FROM bkash_payments WHERE bkash_txn_id = ?", (request.bkash_txn_id,)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="This Transaction ID has already been submitted")
    conn.execute(
        "INSERT INTO bkash_payments (user_id, plan, amount, bkash_txn_id, status) VALUES (?, ?, ?, ?, 'pending')",
        (current_user["id"], request.plan, request.amount, request.bkash_txn_id)
    )
    conn.commit()
    conn.close()
    return {"status": "pending", "message": "Payment submitted. Awaiting admin verification (within 1 hour)."}

@app.get("/my-payments")
async def get_my_payments(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, plan, amount, bkash_txn_id, status, created_at FROM bkash_payments WHERE user_id = ? ORDER BY created_at DESC",
        (current_user["id"],)
    ).fetchall()
    conn.close()
    return [{
        "id": r[0], "plan": r[1], "amount": r[2],
        "bkash_txn_id": r[3], "status": r[4], "created_at": r[5]
    } for r in rows]

# ─────────────────────────────────────────────────────────
# ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    conn = sqlite3.connect(DB_PATH)
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_bots = conn.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM bkash_payments WHERE status = 'pending'").fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM bkash_payments WHERE status = 'approved'").fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "total_bots": total_bots,
        "pending_payments": pending,
        "approved_payments": approved
    }

@app.get("/admin/users")
async def admin_get_users(admin: dict = Depends(require_admin)):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT u.id, u.email, u.plan, u.is_admin, u.created_at, COUNT(b.bot_id) as bot_count "
        "FROM users u LEFT JOIN bots b ON b.owner_id = u.id GROUP BY u.id ORDER BY u.id DESC"
    ).fetchall()
    conn.close()
    return [{
        "id": r[0], "email": r[1], "plan": r[2] or "Hobby",
        "is_admin": bool(r[3]), "created_at": r[4], "bot_count": r[5]
    } for r in rows]

@app.get("/admin/bots")
async def admin_get_bots(admin: dict = Depends(require_admin)):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT b.bot_id, b.url, b.status, b.created_at, u.email "
        "FROM bots b LEFT JOIN users u ON u.id = b.owner_id ORDER BY b.created_at DESC"
    ).fetchall()
    conn.close()
    return [{
        "bot_id": r[0], "url": r[1], "status": r[2],
        "created_at": r[3], "owner_email": r[4]
    } for r in rows]

@app.get("/admin/payments")
async def admin_get_payments(status: Optional[str] = None, admin: dict = Depends(require_admin)):
    conn = sqlite3.connect(DB_PATH)
    query = (
        "SELECT p.id, p.plan, p.amount, p.bkash_txn_id, p.status, p.created_at, u.email "
        "FROM bkash_payments p LEFT JOIN users u ON u.id = p.user_id "
    )
    if status:
        query += f"WHERE p.status = '{status}' "
    query += "ORDER BY p.created_at DESC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [{
        "id": r[0], "plan": r[1], "amount": r[2], "bkash_txn_id": r[3],
        "status": r[4], "created_at": r[5], "user_email": r[6]
    } for r in rows]

@app.post("/admin/approve-payment/{payment_id}")
async def admin_approve_payment(payment_id: int, admin: dict = Depends(require_admin)):
    conn = sqlite3.connect(DB_PATH)
    payment = conn.execute(
        "SELECT user_id, plan FROM bkash_payments WHERE id = ? AND status = 'pending'",
        (payment_id,)
    ).fetchone()
    if not payment:
        conn.close()
        raise HTTPException(status_code=404, detail="Payment not found or already processed")
    user_id, plan = payment
    conn.execute("UPDATE bkash_payments SET status = 'approved' WHERE id = ?", (payment_id,))
    conn.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, user_id))
    conn.commit()
    conn.close()
    return {"status": "approved", "message": f"Payment approved. User plan set to {plan}."}

@app.post("/admin/reject-payment/{payment_id}")
async def admin_reject_payment(payment_id: int, admin: dict = Depends(require_admin)):
    conn = sqlite3.connect(DB_PATH)
    payment = conn.execute(
        "SELECT id FROM bkash_payments WHERE id = ? AND status = 'pending'",
        (payment_id,)
    ).fetchone()
    if not payment:
        conn.close()
        raise HTTPException(status_code=404, detail="Payment not found or already processed")
    conn.execute("UPDATE bkash_payments SET status = 'rejected' WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()
    return {"status": "rejected"}

@app.post("/create-bot")
async def create_bot(request: BotCreateRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    # Plan-based bot limits
    PLAN_LIMITS = {"Free": 1, "Basic": 3, "Pro": 99999}
    user_plan = current_user.get("plan", "Free")
    max_bots = PLAN_LIMITS.get(user_plan, 1)

    conn = sqlite3.connect(DB_PATH)
    current_count = conn.execute("SELECT COUNT(*) FROM bots WHERE owner_id = ?", (current_user["id"],)).fetchone()[0]
    if current_count >= max_bots:
        conn.close()
        raise HTTPException(
            status_code=403,
            detail=f"Your {user_plan} plan allows {max_bots} bot(s). You currently have {current_count}. Please upgrade your plan."
        )

    bot_id = str(uuid.uuid4())[:8]
    conn.execute("INSERT INTO bots (bot_id, url, facebook_url, status, owner_id) VALUES (?, ?, ?, ?, ?)",
                 (bot_id, request.url, request.facebook_url, 'pending', current_user["id"]))
    conn.commit()
    conn.close()

    background_tasks.add_task(run_pipeline, bot_id, request.url, request.facebook_url)

    return {
        "bot_id": bot_id,
        "status": "pending",
        "embed_code": f'<script src="https://botbro.editians.com/widget.js" data-bot-id="{bot_id}"></script>'
    }

@app.get("/bots")
async def get_bots(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT bot_id, url, facebook_url, status, bot_name, business_name, primary_color, created_at FROM bots WHERE owner_id = ? ORDER BY created_at DESC",
        (current_user["id"],)
    )
    bots = []
    for r in cursor.fetchall():
        bots.append({
            "bot_id": r[0], "url": r[1], "facebook_url": r[2], "status": r[3],
            "bot_name": r[4] or "My Bot", "business_name": r[5] or "",
            "primary_color": r[6] or "#00d2ff", "created_at": r[7]
        })
    conn.close()
    return bots


@app.get("/bot-status/{bot_id}")
async def get_bot_status(bot_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT status FROM bots WHERE bot_id = ?", (bot_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"bot_id": bot_id, "status": row[0]}

@app.post("/query")
async def query_bot(request: QueryRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            """
            SELECT b.status, b.business_name, b.bot_name, b.welcome_msg, b.lead_capture_enabled, u.plan, u.id
            FROM bots b
            LEFT JOIN users u ON b.owner_id = u.id
            WHERE b.bot_id = ?
            """,
            (request.bot_id,)
        ).fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Bot not found")

        bot_status, raw_biz, bot_name, welcome_msg, lead_capture_enabled, user_plan, owner_id = row
        user_plan = user_plan or "Free"

        # Quota check
        MESSAGE_LIMITS = {"Free": 10, "Basic": 1000, "Pro": 999999999}
        monthly_limit = MESSAGE_LIMITS.get(user_plan, 10)
        
        if owner_id:
            usage = conn.execute(
                """
                SELECT COUNT(*) FROM messages m 
                JOIN bots b ON m.bot_id = b.bot_id 
                WHERE b.owner_id = ? AND m.role = 'user' 
                AND strftime('%Y-%m', m.created_at) = strftime('%Y-%m', 'now')
                """, (owner_id,)
            ).fetchone()[0]
            
            if usage >= monthly_limit:
                conn.close()
                return {"answer": "This bot has reached its monthly conversation limit. Please ask the website owner to upgrade their plan."}

        # Log user message
        conn.execute(
            "INSERT INTO messages (session_id, bot_id, role, content) VALUES (?, ?, 'user', ?)",
            (request.session_id, request.bot_id, request.query)
        )
        conn.commit()

        if bot_status != 'ready':
            conn.close()
            return {"answer": "I'm still getting ready — just give me a moment and I'll be all set to help you! ⚡"}

        # Clean business name
        biz_name = raw_biz if raw_biz and "does not contain" not in raw_biz and "error" not in raw_biz.lower() else "our business"
        bot_name = bot_name or "Assistant"
        lead_capture = bool(lead_capture_enabled)

        # Pull last 8 messages for memory (4 exchanges)
        history_rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? AND bot_id = ? "
            "AND role IN ('user','bot') ORDER BY created_at ASC",
            (request.session_id, request.bot_id)
        ).fetchall()
        conn.close()

        # Build conversation history string (exclude the message we just inserted)
        history_msgs = history_rows[:-1]  # exclude last user msg we just added
        history_str = ""
        if len(history_msgs) > 1:
            pairs = history_msgs[-8:]  # last 4 pairs
            history_str = "\n".join(
                f"{'Customer' if r[0]=='user' else bot_name}: {r[1][:300]}"
                for r in pairs
            )

        # Retrieve relevant context from vector store — use more results for product coverage
        collection = client.get_or_create_collection(
            name=request.bot_id,
            embedding_function=sentence_transformer_ef
        )
        
        # Primary query: what the user actually asked
        results = collection.query(query_texts=[request.query], n_results=12)
        context_docs = results['documents'][0] if results['documents'] else []
        
        # Secondary query: pull specific items for any service/product query across all domains
        product_keywords = [
            'product', 'buy', 'price', 'cost', 'recommend', 'suggest', 'show',
            'available', 'want', 'need', 'looking', 'shop', 'order', 'which', 'what',
            'collection', 'shoe', 'cloth', 'item', 'model', 'stock', 'doctor', 'physician',
            'specialist', 'appointment', 'headache', 'pain', 'fever', 'sick', 'treatment',
            'consult', 'schedule', 'chamber', 'clinic', 'course', 'class', 'batch', 'fee',
            'admission', 'enroll', 'room', 'book', 'reserve', 'flat', 'rent', 'menu',
            'food', 'dish', 'meal', 'eat', 'serve', 'service', 'package', 'offer', 'deal',
            'how much', 'tell me', 'show me', 'list', 'any',
        ]
        query_lower = request.query.lower()
        # Be permissive — almost all specific questions benefit from product/service retrieval
        is_product_query = any(kw in query_lower for kw in product_keywords) or len(request.query.split()) >= 3
        
        if is_product_query:
            # Also fetch product-specific chunks
            product_results = collection.query(
                query_texts=[f"product catalog items {request.query}"], 
                n_results=8,
                where={"type": "product"} if any(m.get('type') == 'product' for m in (results['metadatas'][0] if results.get('metadatas') else [])) else None
            )
            if product_results['documents']:
                product_docs = product_results['documents'][0]
                # Merge unique docs
                existing = set(context_docs)
                for doc in product_docs:
                    if doc not in existing:
                        context_docs.append(doc)
                        existing.add(doc)
        
        context = "\n---\n".join(context_docs) if context_docs else "No specific information found."

        # Extract what we already know about this user from history
        known_info = ""
        if history_str:
            info_prompt = f"From this conversation, list any user details already mentioned (name, phone, email, location, interest). Be brief, bullet points only. If nothing mentioned, say 'none'.\n\nConversation:\n{history_str}"
            try:
                info_res = model.generate_content(info_prompt)
                known = info_res.text.strip()
                if known.lower() != 'none':
                    known_info = known
            except:
                pass

        lead_instruction = ""
        if lead_capture:
            lead_instruction = "\n\u2022 LEAD CAPTURE: If the user shows interest in buying, booking, or getting more info, naturally ask for their name and phone number to arrange follow-up. Do this ONLY ONCE per conversation.\n\u2022 If you already know their name or phone from history, use it and DO NOT ask again."

        # Auto-detect business domain for domain-specific intelligence
        context_lower = context.lower()
        domain_rules = ""
        
        if any(w in context_lower for w in ['doctor', 'hospital', 'clinic', 'physician', 'specialist', 'appointment', 'patient', 'medical', 'health', 'treatment', 'surgery', 'consultation', 'chamber']):
            domain_rules = """
HEALTHCARE DOMAIN RULES:
\u2022 When a patient mentions any symptom or health concern, FIRST acknowledge with empathy, then suggest the RIGHT SPECIALIST by their exact name from the knowledge base
\u2022 Always mention the doctor's: full name, specialization, availability/schedule (days + times), chamber/room if available
\u2022 Format: \"\ud83d\udc68\u200d\u2695\ufe0f Dr. [Name] \u2014 [Specialization] \u2014 Available: [Schedule]\"
\u2022 Symptom matching: headache \u2192 neurologist, chest pain \u2192 cardiologist, skin problem \u2192 dermatologist, child sick \u2192 pediatrician
\u2022 After recommending a doctor, offer to help book an appointment
\u2022 Always reassure the patient \u2014 be extra empathetic
\u2022 Never diagnose \u2014 say \"Please consult our doctor for proper diagnosis\""""

        elif any(w in context_lower for w in ['menu', 'food', 'restaurant', 'dish', 'cuisine', 'meal', 'burger', 'pizza', 'biryani', 'curry', 'order food']):
            domain_rules = """
RESTAURANT DOMAIN RULES:
\u2022 Name SPECIFIC dishes with prices when asked about food
\u2022 Suggest based on customer preference (spicy, sweet, light, filling)
\u2022 Always mention price and combo deals
\u2022 Recommend bestsellers when customer is undecided
\u2022 If delivery available, mention delivery time"""

        elif any(w in context_lower for w in ['shoe', 'footwear', 'sandal', 'sneaker', 'cloth', 'dress', 'shirt', 'pant', 'fashion', 'collection', 'brand', 'size', 'fabric']):
            domain_rules = """
FASHION/RETAIL DOMAIN RULES:
\u2022 Always recommend SPECIFIC product names/models with prices and sizes
\u2022 Ask ONE clarifying question if needed: occasion, size, budget, style
\u2022 Mention key features: material, comfort, durability
\u2022 Suggest complementary items naturally (upsell)"""

        elif any(w in context_lower for w in ['course', 'class', 'student', 'learn', 'training', 'batch', 'admission', 'school', 'college', 'certificate', 'exam']):
            domain_rules = """
EDUCATION DOMAIN RULES:
\u2022 Recommend SPECIFIC courses with duration, fees, and batch schedule
\u2022 Mention instructor names and their qualifications if available
\u2022 Highlight outcomes: certificates, skills, career opportunities
\u2022 Create gentle urgency about upcoming batch starts or deadlines"""

        elif any(w in context_lower for w in ['apartment', 'flat', 'property', 'real estate', 'rent', 'plot', 'house', 'building', 'sqft', 'bedroom']):
            domain_rules = """
REAL ESTATE DOMAIN RULES:
\u2022 Recommend SPECIFIC properties with size, location, price/rent
\u2022 Ask about: budget, preferred area, size needed, purpose
\u2022 Offer to arrange a site visit \u2014 key conversion step
\u2022 Be professional and trustworthy"""

        elif any(w in context_lower for w in ['hotel', 'room', 'suite', 'check-in', 'booking', 'resort', 'guest', 'accommodation', 'breakfast']):
            domain_rules = """
HOSPITALITY DOMAIN RULES:
\u2022 Recommend SPECIFIC room types with pricing and amenities
\u2022 Ask about: dates, number of guests, budget
\u2022 Highlight special packages or deals
\u2022 Offer to check availability"""

        system_prompt = f"""You are {bot_name}, the expert AI assistant for {biz_name}. You have deep knowledge of everything this business offers and genuinely care about helping every visitor.

YOUR CORE MISSION:
Be the most helpful, specific, and knowledgeable assistant possible. Never be vague. Always give concrete answers drawn from the knowledge base \u2014 names, prices, schedules, availability.
{domain_rules}
UNIVERSAL RULES (apply to all domains):
\u2022 When someone asks about products, services, doctors, courses \u2014 ALWAYS name 2-5 SPECIFIC items from the knowledge base
\u2022 NEVER say \"we have many options\" without first giving specific information
\u2022 ALWAYS include price/cost if available in the knowledge base \u2014 it builds trust
\u2022 Identify the customer's specific need FIRST, then match it to specific offerings
\u2022 Ask EXACTLY ONE clarifying question when needed \u2014 then give specific recommendations
\u2022 SOCIAL PROOF: \"This is very popular\" or \"Customers love this for...\"
\u2022 SOFT CLOSE: After recommending, invite the next step

PERSONALITY:
• Keep responses EXTREMELY SHORT and precise (1-3 brief sentences maximum).
• Use simple, conversational language so anyone can understand easily.
• Use bullet points for easy readability if recommending multiple items, but limit to 2-3 items.
• Warm, confident, genuinely enthusiastic — like the best employee at this business
• Match the customer's language (Bangla reply for Bangla, English for English)
• Use 1-2 relevant emojis per response — never excessive

ABSOLUTE RULES:
\u2022 NEVER attempt to add items to a cart, handle checkout, or ask for payment. You do not have access to the user's cart.
\u2022 Instead of checkout, provide a clickable link and image so the user can order it themselves.
\u2022 CRITICAL: With EVERY product recommendation, you MUST provide an image and a link if available in the knowledge base, formatted exactly as: [![Product Name](image_url)](link_url). Do not skip the image.
\u2022 NEVER claim to be an AI, chatbot, or robot
\u2022 NEVER reveal Bot Bro or any underlying technology
\u2022 ONLY use information from the KNOWLEDGE BASE \u2014 never invent names, prices, or schedules
\u2022 If info isn't in the knowledge base: \"Let me connect you with our team for that \u2014 could I take your name and number?\"
\u2022 NEVER repeat questions already answered{lead_instruction}

KNOWLEDGE BASE for {biz_name}:
{context}"""

        # Build the full prompt
        full_prompt = ""
        if history_str:
            full_prompt += f"[CONVERSATION HISTORY]:\n{history_str}\n\n"
        if known_info:
            full_prompt += f"[WHAT I KNOW ABOUT THIS CUSTOMER]: {known_info}\n\n"
        
        # Give the AI a clear signal about what the customer wants
        if is_product_query:
            full_prompt += f"[CUSTOMER IS ASKING ABOUT PRODUCTS/SERVICES — name specific items from the knowledge base]\n"
        
        full_prompt += f"[CUSTOMER MESSAGE]: {request.query}\n\n"
        full_prompt += (
            f"[YOUR RESPONSE as {bot_name}]: "
            f"(Be specific — name actual products/services. Be warm and sales-focused. "
            f"If listing products, use a brief bullet format with name, benefit, price. "
            f"Never be vague. Based ONLY on the knowledge base above.)"
        )

        # Remove any stray surrogates that might crash the protobuf encoder
        system_prompt = "".join(c for c in system_prompt if not (0xD800 <= ord(c) <= 0xDFFF))
        full_prompt = "".join(c for c in full_prompt if not (0xD800 <= ord(c) <= 0xDFFF))

        bot_model = genai.GenerativeModel(
            model_name='gemini-3.1-flash-lite',
            system_instruction=system_prompt
        )
        
        if request.image_base64:
            contents = [full_prompt]
            try:
                # Strip data:image/...;base64, prefix if present
                base64_data = request.image_base64.split(",")[-1]
                image_data = base64.b64decode(base64_data)
                contents.append({
                    "mime_type": "image/jpeg",
                    "data": image_data
                })
                response = bot_model.generate_content(contents)
            except Exception as e:
                print(f"Error processing image: {e}")
                response = bot_model.generate_content(full_prompt)
        else:
            response = bot_model.generate_content(full_prompt)
            
        answer = response.text.strip()

        # Remove any AI-revealing phrases that might slip through
        sanitize = [
            ("As an AI", "As your assistant"),
            ("as an AI", "as your assistant"),
            ("I am an AI", "I'm here to help"),
            ("I'm an AI", "I'm here to help"),
            ("language model", "assistant"),
            ("large language model", "assistant"),
            ("ChatGPT", bot_name),
            ("Gemini", bot_name),
            ("GPT", bot_name),
            ("Bot Bro", bot_name),
            ("I cannot provide", "Let me find that for you"),
            ("I don't have access", "For the most up-to-date details"),
            ("I'm not able to", "Let me help you with"),
        ]
        for bad, good in sanitize:
            answer = answer.replace(bad, good)

        # Log bot response
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO messages (session_id, bot_id, role, content) VALUES (?, ?, 'bot', ?)",
            (request.session_id, request.bot_id, answer)
        )
        conn.commit()
        conn.close()

        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ─── SITE SUMMARY ───

@app.get("/bot-summary/{bot_id}")
async def get_bot_summary(bot_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT site_summary, site_summary_bn, business_name, status FROM bots WHERE bot_id = ?",
        (bot_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {
        "bot_id": bot_id,
        "status": row[3],
        "summary_en": row[0] or "",
        "summary_bn": row[1] or "",
        "business_name": row[2] or ""
    }

class TranslateRequest(BaseModel):
    text: str
    target_lang: str  # "en" or "bn"

@app.post("/translate")
async def translate_text(request: TranslateRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    try:
        if request.target_lang == "bn":
            prompt = f"Translate this to fluent, natural Bangla (Bengali). Keep it professional:\n\n{request.text}"
        else:
            prompt = f"Translate this to fluent, natural English. Keep it professional:\n\n{request.text}"
        res = model.generate_content(prompt)
        return {"translated": res.text.strip(), "target_lang": request.target_lang}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── HOMEPAGE BOT (Aria) ───
ARIA_KNOWLEDGE = """You are Aria, the friendly AI assistant for InteractAI — Bangladesh's leading AI chatbot SaaS platform.

ABOUT INTERACTAI:
• InteractAI lets any business turn their website into a 24/7 AI chatbot in under 60 seconds
• No coding required — just enter your URL and we train the AI on your site content automatically
• The chatbot widget is embedded with a single line of code: <script src="https://interactai.io/widget.js" data-bot-id="YOUR_ID"></script>
• Works on any platform: WordPress, Shopify, custom HTML, Wix, etc.

PRICING (BDT - Bangladeshi Taka):
• Hobby Plan: ৳0/month — FREE forever. 1 bot, 50 pages, 100 messages/month
• Pro Plan: ৳3,200/month (~$29 USD) — 5 bots, unlimited pages, 2,000 messages, lead capture, remove branding
• Agency Plan: ৳10,900/month (~$99 USD) — 20 bots, unlimited everything, 10,000 messages, API access, white-label

PAYMENT:
• We accept bKash payment — Bangladesh's most popular mobile payment
• bKash number: 01302450710
• How: Send money via bKash → submit your Transaction ID in the dashboard → we activate within 1 hour
• WhatsApp for support: +8801302450710

HOW TO INTEGRATE:
1. Sign up at interactai.io/signup
2. Enter your website URL — AI trains in 60 seconds
3. Copy the embed code from your dashboard
4. Paste it in your website's <head> or footer
5. Done! Your AI bot is live.

FEATURES:
• 24/7 automated customer support
• Smart lead capture (collects name, phone, email within chat)
• Order capture — customers can place orders through chat
• Full customization: colors, bot name, welcome message, avatar
• Conversation memory — bot remembers within a session
• Multilingual: responds in Bangla and English
• Analytics dashboard: leads, orders, conversations
• Facebook page scraping (optional)

COMPANY:
• Based in Dhaka, Bangladesh 🇧🇩
• Support email: support@interactai.io
• WhatsApp: +8801302450710
• Payment: bKash 01302450710
"""

class HomepageQueryRequest(BaseModel):
    query: str
    session_id: str = "homepage"

@app.post("/homepage-query")
async def homepage_query(request: HomepageQueryRequest):
    try:
        aria_system = f"""{ARIA_KNOWLEDGE}

YOUR PERSONALITY AS ARIA:
• You are warm, enthusiastic, and genuinely helpful
• You speak like a friendly expert who loves what they do
• You give concise, clear answers — 2-4 sentences unless more detail is genuinely needed
• You use 1-2 relevant emojis occasionally to feel human and friendly
• If asked about pricing, always mention bKash and BDT amounts
• Guide users toward signing up or contacting via WhatsApp
• Respond in the same language as the user (Bangla if they write Bangla)
• NEVER say you are AI/chatbot/language model"""

        aria_model = genai.GenerativeModel(
            model_name='gemini-3.1-flash-lite',
            system_instruction=aria_system
        )
        response = aria_model.generate_content(request.query)
        answer = response.text.strip()
        return {"answer": answer, "bot_name": "Aria"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/train-manual")
async def train_manual(request: TrainRequest):
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
            
        collection = client.get_or_create_collection(
            name=request.bot_id,
            embedding_function=sentence_transformer_ef
        )
        
        # Split into chunks of ~500 chars for semantic relevance
        chunks = [request.text[i:i+500] for i in range(0, len(request.text), 500)]
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"manual_{uuid.uuid4().hex[:8]}_{i}"
            collection.upsert(
                documents=[chunk],
                ids=[chunk_id],
                metadatas=[{"source": "manual"}]
            )
            
        return {"status": "success", "chunks_added": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/suggested-questions/{bot_id}")
async def get_suggested_questions(bot_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT suggested_questions FROM bots WHERE bot_id = ?", (bot_id,)).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if row[0]:
        questions = json.loads(row[0])[:3] # Limit to 3
        conn.close()
        return {"bot_id": bot_id, "questions": questions}
    
    # Generate new questions
    questions = await generate_questions(bot_id)
    questions = questions[:3] # Ensure max 3
    conn.execute("UPDATE bots SET suggested_questions = ? WHERE bot_id = ?", (json.dumps(questions), bot_id))
    conn.commit()
    conn.close()
    return {"bot_id": bot_id, "questions": questions}

@app.post("/refresh-suggestions/{bot_id}")
async def refresh_suggestions(bot_id: str):
    questions = await generate_questions(bot_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE bots SET suggested_questions = ? WHERE bot_id = ?", (json.dumps(questions), bot_id))
    conn.commit()
    conn.close()
    return {"bot_id": bot_id, "questions": questions}

class SettingsRequest(BaseModel):
    primary_color: str
    secondary_color: str = "#6366f1"
    bot_name: str
    business_name: str = None
    welcome_msg: str
    avatar_url: str = None
    lead_capture_enabled: bool = False

class LeadSubmission(BaseModel):
    name: str = None
    phone: str = None
    contact_info: str = None
    last_message: str = None
    session_id: str = None

@app.get("/bot-settings/{bot_id}")
async def get_bot_settings(bot_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT primary_color, secondary_color, bot_name, business_name, welcome_msg, avatar_url, lead_capture_enabled FROM bots WHERE bot_id = ?", (bot_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {
        "primary_color": row[0],
        "secondary_color": row[1],
        "bot_name": row[2],
        "business_name": row[3],
        "welcome_msg": row[4],
        "avatar_url": row[5],
        "lead_capture_enabled": bool(row[6])
    }

@app.post("/bot-settings/{bot_id}")
async def update_bot_settings(bot_id: str, settings: SettingsRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""UPDATE bots SET primary_color = ?, secondary_color = ?, bot_name = ?, business_name = ?, welcome_msg = ?, avatar_url = ?, lead_capture_enabled = ? 
                    WHERE bot_id = ?""", 
                 (settings.primary_color, settings.secondary_color, settings.bot_name, settings.business_name, settings.welcome_msg, settings.avatar_url, int(settings.lead_capture_enabled), bot_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/submit-lead/{bot_id}")
async def submit_lead(bot_id: str, lead: LeadSubmission):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO leads (bot_id, contact_info, last_message) VALUES (?, ?, ?)",
                 (bot_id, lead.contact_info, lead.last_message))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/all-leads")
async def get_all_leads(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    # Get all leads from this user's bots with contact info
    cursor = conn.execute("""
        SELECT l.id, l.bot_id, l.contact_info, l.last_message, l.created_at, b.bot_name
        FROM leads l
        JOIN bots b ON l.bot_id = b.bot_id
        WHERE b.owner_id = ?
        ORDER BY l.created_at DESC
    """, (current_user["id"],))
    leads = []
    for r in cursor.fetchall():
        leads.append({
            "id": r[0],
            "bot_id": r[1],
            "contact_info": r[2],
            "last_message": r[3],
            "created_at": r[4],
            "bot_name": r[5] or "My Bot"
        })
    conn.close()
    return leads

@app.get("/all-orders")
async def get_all_orders(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT order_id, bot_id, customer_name, customer_phone, customer_email, items, total, status, created_at
        FROM orders
        WHERE bot_id IN (SELECT bot_id FROM bots WHERE owner_id = ?)
        ORDER BY created_at DESC
    """, (current_user["id"],))
    orders = []
    for r in cursor.fetchall():
        orders.append({
            "order_id": r[0], "bot_id": r[1], "customer_name": r[2],
            "customer_phone": r[3], "customer_email": r[4],
            "items": r[5], "total": r[6], "status": r[7], "created_at": r[8]
        })
    conn.close()
    return orders

class OrderStatusUpdate(BaseModel):
    status: str

@app.post("/order-status/{order_id}")
async def update_order_status(order_id: str, request: OrderStatusUpdate, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE orders SET status = ? WHERE order_id = ?", (request.status, order_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/bot/{bot_id}/end-session")
async def end_session(bot_id: str, request: SessionEndRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        # Fetch messages
        cursor = conn.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC", (request.session_id,))
        messages = cursor.fetchall()
        
        if not messages:
            conn.close()
            return {"success": False, "error": "No messages found for session"}
            
        transcript = "\n".join([f"{m[0]}: {m[1]}" for m in messages])
        
        prompt = f"""
        Analyze this customer conversation and return a JSON object with exactly these fields:
        {{
          "summary": "2-3 sentence plain English summary of what the customer wanted",
          "intent": "browsing|inquiry|complaint|order|lead",
          "sentiment": "positive|neutral|negative",
          "key_info_captured": {{
            "name": "if mentioned or null",
            "phone": "if mentioned or null", 
            "email": "if mentioned or null",
            "order_items": ["list if any ordered"],
            "order_total": "total if calculable or null"
          }},
          "is_lead": true or false,
          "lead_score": 1 to 10
        }}
        Conversation:
        {transcript}
        """
        
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_json)
        
        # Save Conversation
        conn.execute("""
            INSERT INTO conversations (session_id, bot_id, summary, intent, sentiment, is_lead, lead_score, transcript)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
            summary=excluded.summary, intent=excluded.intent, sentiment=excluded.sentiment, 
            is_lead=excluded.is_lead, lead_score=excluded.lead_score, transcript=excluded.transcript
        """, (request.session_id, bot_id, data['summary'], data['intent'], data['sentiment'], 
              1 if data['is_lead'] else 0, data['lead_score'], transcript))
        
        # Upsert Lead if info found
        info = data['key_info_captured']
        if info['email'] or info['phone']:
            contact = info['email'] or info['phone']
            conn.execute("""
                INSERT INTO leads (bot_id, contact_info, last_message)
                VALUES (?, ?, ?)
            """, (bot_id, contact, data['summary']))
            
        # Create Order if items found
        if info['order_items'] and data['intent'] == 'order':
            order_id = f"ORD-{str(uuid.uuid4())[:6].upper()}"
            conn.execute("""
                INSERT INTO orders (order_id, bot_id, session_id, customer_name, customer_phone, customer_email, items, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, bot_id, request.session_id, info['name'], info['phone'], info['email'], 
                  json.dumps(info['order_items']), info['order_total']))

        conn.commit()
        conn.close()
        return {"success": True, "data": data}
    except Exception as e:
        print(f"Error ending session: {e}")
        return {"success": False, "error": str(e)}

async def generate_questions(bot_id: str):
    try:
        collection = client.get_or_create_collection(name=bot_id, embedding_function=sentence_transformer_ef)
        
        # Get some context from website and FB
        web_res = collection.get(where={"source": "website"}, limit=5)
        fb_res = collection.get(where={"source": "facebook"}, limit=5)
        
        context = "\n".join(web_res['documents'] + fb_res['documents'])
        
        prompt = f"""
        CONTEXT: {context}
        TASK: Based on the context above, generate the 3 most likely questions a customer would ask this business.
        Include questions about specific details if found (like offers, address, or services).
        FORMAT: Return ONLY a JSON list of strings.
        Example: ["What are your hours?", "Do you have a lunch menu?"]
        """
        
        response = model.generate_content(prompt)
        # Clean response text in case of markdown blocks
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        questions = json.loads(clean_text)
        return questions[:3]
    except Exception as e:
        print(f"Error generating questions: {e}")
        return ["What services do you offer?", "Where are you located?", "How can I contact you?"]

@app.delete("/bot/{bot_id}")
async def delete_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    # Check ownership
    bot = conn.execute("SELECT owner_id FROM bots WHERE bot_id = ?", (bot_id,)).fetchone()
    if not bot or bot[0] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to delete this bot")
    
    conn.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
    conn.commit()
    conn.close()
    
    # Try to delete from ChromaDB
    try:
        client.delete_collection(name=bot_id)
    except:
        pass
        
    return {"status": "success"}

class UpgradeRequest(BaseModel):
    plan: str

@app.post("/upgrade-plan")
async def upgrade_plan(request: UpgradeRequest, current_user: dict = Depends(get_current_user)):
    valid_plans = ["Hobby", "Pro", "Agency"]
    if request.plan not in valid_plans:
        raise HTTPException(status_code=400, detail="Invalid plan selected.")
        
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET plan = ? WHERE id = ?", (request.plan, current_user["id"]))
    conn.commit()
    conn.close()
    return {"status": "success", "new_plan": request.plan}

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
