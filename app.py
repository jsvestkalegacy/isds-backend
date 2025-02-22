import os
import psycopg2
from psycopg2 import sql
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from zeep import Client

# Načtení proměnných prostředí
load_dotenv()

# Konfigurace databáze z .env souboru
DB_NAME = os.getenv("DB_NAME", "isds_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Simulace API ISDS
SIMULATE_API = True
WSDL_URL = "https://ws1.mojedatovaschranka.cz/DS/DsManage"

if not SIMULATE_API:
    client = Client(WSDL_URL)
    print("✅ Připojeno k API ISDS")
else:
    print("⚠️ Simulace API ISDS – certifikát zatím není dostupný.")

# Připojení k databázi
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, 
            user=DB_USER, 
            password=DB_PASSWORD, 
            host=DB_HOST, 
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print("❌ Chyba při připojení k databázi:", e)
        return None

# Vytvoření tabulky zpráv
def create_tables():
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    datova_schranka_id VARCHAR(255) NOT NULL,
                    sender VARCHAR(255) NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    attachments TEXT,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Tabulky byly úspěšně vytvořeny.")
        except Exception as e:
            print("❌ Chyba při vytváření tabulek:", e)

# Vložení zprávy
def insert_message(message_id, datova_schranka_id, sender, subject, content, attachments):
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (message_id, datova_schranka_id, sender, subject, content, attachments)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING;
            ''', (message_id, datova_schranka_id, sender, subject, content, attachments))
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Zpráva úspěšně uložena.")
        except Exception as e:
            print("❌ Chyba při vkládání zprávy:", e)

# Načtení všech zpráv
def get_messages():
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM messages ORDER BY received_at DESC')
            messages = cursor.fetchall()
            cursor.close()
            conn.close()
            return messages
        except Exception as e:
            print("❌ Chyba při načítání zpráv:", e)
            return []

# Flask aplikace
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "✅ API běží správně!"

@app.route("/messages", methods=["GET"])
def get_all_messages():
    """API endpoint pro získání všech zpráv, s možností filtrování podle datové schránky"""
    schranka_id = request.args.get('datova_schranka_id')
    messages = get_messages()

    if schranka_id:
        messages = [msg for msg in messages if msg[2] == schranka_id]

    messages_list = [
        {
            "id": msg[0],
            "message_id": msg[1],
            "datova_schranka_id": msg[2],
            "sender": msg[3],
            "subject": msg[4],
            "content": msg[5],
            "attachments": msg[6],
            "received_at": msg[7].strftime("%Y-%m-%d %H:%M:%S") if msg[7] else None
        }
        for msg in messages
    ]

    return jsonify(messages_list)

# Vložení testovacích zpráv
def insert_test_messages():
    test_messages = [
        ("msg001", "d75dvaq", "Ministerstvo vnitra", "Potvrzení o přijetí", "Vaše zpráva byla přijata.", None),
        ("msg002", "vqqv5qf", "Finanční úřad", "Výzva k podání", "Nezapomeňte podat daňové přiznání.", None),
        ("msg003", "jqwcu54", "Česká pošta", "Oznámení o zásilce", "Vaše zásilka je připravena k vyzvednutí.", None)
    ]
    for msg in test_messages:
        insert_message(*msg)

# Hlavní spuštění aplikace
if __name__ == "__main__":
    create_tables()
    insert_test_messages()
    print("✅ Testovací zprávy byly přidány.")
    print("✅ Aplikace běží v režimu simulace API ISDS.")
    app.run(host="0.0.0.0", port=5000)