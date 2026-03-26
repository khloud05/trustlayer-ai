import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trustlayer.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            response_id TEXT PRIMARY KEY,
            source TEXT,
            answers_json TEXT,
            response_time_seconds INTEGER,
            confidence_score INTEGER,
            quality_level TEXT,
            validation_status TEXT,
            final_confirmed BOOLEAN DEFAULT 0,
            submitted_at DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation_issues (
            issue_id TEXT PRIMARY KEY,
            response_id TEXT,
            issue_type TEXT,
            rule_name TEXT,
            severity TEXT,
            deduction INTEGER,
            field_names_json TEXT,
            message_ar TEXT,
            explanation_ar TEXT,
            suggested_action_ar TEXT,
            detected_at DATETIME,
            FOREIGN KEY (response_id) REFERENCES responses(response_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS correction_actions (
            action_id TEXT PRIMARY KEY,
            response_id TEXT,
            field_name TEXT,
            previous_value TEXT,
            updated_value TEXT,
            timestamp DATETIME,
            FOREIGN KEY (response_id) REFERENCES responses(response_id)
        )
    """)

    conn.commit()
    conn.close()
