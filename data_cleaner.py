"""
data_cleaner.py — Dataset cleaning analysis for TrustLayer AI
Identifies duplicates, suspicious, and invalid responses without modifying the DB.
"""

from database import get_connection


def get_cleaning_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    # ── Total responses ────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) as cnt FROM responses")
    total = cursor.fetchone()["cnt"]

    if total == 0:
        conn.close()
        return {
            "original_count": 0,
            "removed_duplicates": 0,
            "removed_suspicious": 0,
            "total_removed": 0,
            "final_clean": 0,
            "high_before": 0, "medium_before": 0, "low_before": 0,
            "high_after": 0,  "medium_after": 0,  "low_after": 0,
        }

    # ── Duplicate detection ────────────────────────────────────
    # Keep the first-submitted occurrence of each unique answers_json.
    # All other occurrences are duplicates.
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM responses
        WHERE response_id NOT IN (
            SELECT MIN(response_id) FROM responses GROUP BY answers_json
        )
    """)
    dup_count = cursor.fetchone()["cnt"]

    # Collect duplicate IDs for overlap removal below
    cursor.execute("""
        SELECT response_id FROM responses
        WHERE response_id NOT IN (
            SELECT MIN(response_id) FROM responses GROUP BY answers_json
        )
    """)
    duplicate_ids = {row["response_id"] for row in cursor.fetchall()}

    # ── Suspicious / invalid detection ────────────────────────
    # Criteria (applied only to non-duplicate rows):
    #   • Impossibly fast response (< 5 seconds)
    #   • Extremely low confidence score (< 30) — multiple serious violations
    cursor.execute("""
        SELECT response_id FROM responses
        WHERE response_id IN (
            SELECT MIN(response_id) FROM responses GROUP BY answers_json
        )
        AND (response_time_seconds < 5 OR confidence_score < 30)
    """)
    suspicious_ids = {row["response_id"] for row in cursor.fetchall()}
    susp_count = len(suspicious_ids)

    all_removed = duplicate_ids | suspicious_ids
    total_removed = len(all_removed)
    final_clean = max(0, total - total_removed)

    # ── Quality breakdown before cleaning ─────────────────────
    cursor.execute("""
        SELECT quality_level, COUNT(*) as cnt FROM responses
        GROUP BY quality_level
    """)
    before_rows = {row["quality_level"]: row["cnt"] for row in cursor.fetchall()}

    # ── Quality breakdown after cleaning ──────────────────────
    # Removed rows are the "worst" Low quality ones (score < 30) + duplicates
    # Re-query keeping only clean IDs
    if all_removed:
        placeholders = ",".join("?" * len(all_removed))
        cursor.execute(f"""
            SELECT quality_level, COUNT(*) as cnt FROM responses
            WHERE response_id NOT IN ({placeholders})
            GROUP BY quality_level
        """, list(all_removed))
    else:
        cursor.execute("""
            SELECT quality_level, COUNT(*) as cnt FROM responses
            GROUP BY quality_level
        """)
    after_rows = {row["quality_level"]: row["cnt"] for row in cursor.fetchall()}

    conn.close()

    return {
        "original_count":    total,
        "removed_duplicates": dup_count,
        "removed_suspicious": susp_count,
        "total_removed":      total_removed,
        "final_clean":        final_clean,
        # Quality distribution before
        "high_before":   before_rows.get("High", 0),
        "medium_before": before_rows.get("Medium", 0),
        "low_before":    before_rows.get("Low", 0),
        # Quality distribution after
        "high_after":    after_rows.get("High", 0),
        "medium_after":  after_rows.get("Medium", 0),
        "low_after":     after_rows.get("Low", 0),
    }
