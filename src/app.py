"""
Oros CRM API — Customer Relationship Management Service
A simple Flask API that connects to PostgreSQL, Redis, and Kafka.
"""
import os
import json
import logging
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import redis

app = Flask(__name__)
CORS(app)

SERVICE_NAME = os.getenv("SERVICE_NAME", "crm-api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(SERVICE_NAME)


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)


def get_redis():
    return redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def init_db():
    """Create tables if they don't exist."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(20),
                company VARCHAR(200),
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.warning(f"DB init skipped: {e}")


# ── Routes ──────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    checks = {
        "service": SERVICE_NAME,
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        conn = get_db()
        conn.cursor().execute("SELECT 1")
        conn.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        checks["status"] = "degraded"
    try:
        get_redis().ping()
        checks["cache"] = "ok"
    except Exception as e:
        checks["cache"] = f"error: {str(e)}"

    return jsonify(checks), 200 if checks["status"] == "ok" else 503


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "endpoints": ["/health", "/api/v1/contacts"]
    })


@app.route("/api/v1/contacts", methods=["GET"])
def list_contacts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts ORDER BY created_at DESC LIMIT 50")
    contacts = cur.fetchall()
    conn.close()
    return jsonify(contacts)


@app.route("/api/v1/contacts", methods=["POST"])
def create_contact():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("first_name"):
        return jsonify({"error": "first_name and email are required"}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO contacts (first_name, last_name, email, phone, company)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (data["first_name"], data.get("last_name", ""),
             data["email"], data.get("phone"), data.get("company"))
        )
        contact = cur.fetchone()
        conn.commit()
        conn.close()
        return jsonify(contact), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        return jsonify({"error": "Email already exists"}), 409


@app.route("/api/v1/contacts/<int:contact_id>", methods=["GET"])
def get_contact(contact_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    contact = cur.fetchone()
    conn.close()
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact)


@app.route("/api/v1/contacts/<int:contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE id = %s RETURNING id", (contact_id,))
    deleted = cur.fetchone()
    conn.commit()
    conn.close()
    if not deleted:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"message": "Contact deleted"}), 200


# ── Startup ─────────────────────────────────
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
