"""
seed_data.py — توليد بيانات تجريبية لمشروع TrustLayer AI
يُنشئ 50 استجابة متنوعة تغطي جميع مستويات الجودة والقواعد
"""

import sqlite3
import json
import uuid
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trustlayer.db")

# قيم الأسئلة المتاحة
MONTHLY_INCOME = ["less_than_3000", "from_3000_to_7000", "from_7001_to_15000", "above_15000"]
LUXURY_FREQ    = ["never", "once_per_year", "several_times_per_year", "monthly"]
INTERNET       = ["yes", "no"]
APP_EVAL       = ["excellent", "good", "average", "poor", "not_applicable"]
TV_USAGE       = ["yes", "no"]
TV_CHANNELS    = ["sports", "news", "entertainment", "cultural", "none"]
PURCHASE_FREQ  = ["once", "two_to_three", "four_to_six", "more_than_six"]
SPENDING       = ["less_than_50", "from_50_to_100", "from_100_to_300", "more_than_300"]
BRANDS         = ["nestle", "almarai", "nada", "other"]
REASONS        = ["price", "quality", "brand", "availability"]

def random_date(days_back=60):
    """تاريخ عشوائي خلال الـ 60 يوم الماضية"""
    delta = timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return (datetime.now() - delta).strftime("%Y-%m-%d %H:%M:%S")

def compute_confidence(answers, response_time):
    score = 100
    issues = []

    # R-01
    if answers["monthly_income"] == "less_than_3000" and answers["luxury_purchase_frequency"] in ["once_per_year", "several_times_per_year", "monthly"]:
        score -= 30
        issues.append(("logical_conflict", "income_vs_luxury_spending", "High", 30,
                        ["monthly_income", "luxury_purchase_frequency"],
                        "لاحظنا تعارضاً بين مستوى الدخل المصرح به ونمط شراء السلع الفاخرة.",
                        "الدخل الشهري المنخفض لا يتوافق منطقياً مع تكرار شراء السلع الفاخرة.",
                        "يرجى مراجعة بيانات الدخل أو تكرار شراء السلع الفاخرة."))

    # R-02
    if answers["internet_usage"] == "no" and answers["app_evaluation"] in ["excellent", "good", "average", "poor"]:
        score -= 15
        issues.append(("logical_conflict", "internet_usage_vs_app_evaluation", "Medium", 15,
                        ["internet_usage", "app_evaluation"],
                        "لاحظنا أنك ذكرت أنك لا تستخدم الإنترنت، لكنك قمت بتقييم تطبيقات الهاتف.",
                        "لا يمكن تقييم تطبيقات الهاتف بشكل منطقي إذا كانت إجابة استخدام الإنترنت هي لا.",
                        "يرجى مراجعة إجابة استخدام الإنترنت أو تقييم التطبيقات."))

    # R-03
    if answers["tv_usage"] == "no" and answers["favorite_tv_channels"] in ["sports", "news", "entertainment", "cultural"]:
        score -= 15
        issues.append(("logical_conflict", "tv_usage_vs_favorite_channels", "Medium", 15,
                        ["tv_usage", "favorite_tv_channels"],
                        "لاحظنا أنك ذكرت أنك لا تشاهد التلفاز، لكنك حددت قنوات تلفزيونية مفضلة.",
                        "لا يتوافق عدم مشاهدة التلفاز مع تحديد قنوات تلفزيونية مفضلة.",
                        "يرجى مراجعة إجابة مشاهدة التلفاز أو القنوات المفضلة."))

    # R-04
    if answers["purchase_frequency"] == "more_than_six" and answers["monthly_spending"] == "less_than_50":
        score -= 15
        issues.append(("logical_conflict", "purchase_vs_spending_consistency", "Medium", 15,
                        ["purchase_frequency", "monthly_spending"],
                        "لاحظنا تعارضاً بين عدد مرات الشراء ومستوى الإنفاق الشهري.",
                        "عدد مرات الشراء الشهري مرتفع بينما مستوى الإنفاق منخفض بشكل غير متوافق.",
                        "يرجى مراجعة عدد مرات الشراء أو قيمة الإنفاق الشهري."))

    # R-05
    if answers["brand_preference"] != answers["last_purchase"]:
        score -= 10
        issues.append(("logical_warning", "brand_preference_vs_last_purchase", "Low", 10,
                        ["brand_preference", "last_purchase"],
                        "لاحظنا اختلافاً بين العلامة التجارية المفضلة وآخر علامة تجارية تم شراؤها.",
                        "قد يكون هذا الاختلاف طبيعياً لكنه قد يشير إلى عدم اتساق في الإجابات.",
                        "يرجى التأكد من صحة العلامة التجارية المفضلة وآخر عملية شراء."))

    # R-06
    if response_time < 15:
        score -= 5
        issues.append(("behavioral_anomaly", "response_speed_behavior", "Low", 5,
                        ["response_time_seconds"],
                        "تم رصد سرعة غير طبيعية في تعبئة الاستبيان.",
                        "قد تشير سرعة الإجابة العالية جداً إلى عدم قراءة الأسئلة بعناية.",
                        "يرجى مراجعة الإجابات قبل الإرسال النهائي."))

    score = max(0, score)

    if score >= 90:
        quality = "High"
        status = "valid"
    elif score >= 70:
        quality = "Medium"
        status = "warning"
    else:
        quality = "Low"
        status = "invalid"

    return score, quality, status, issues


def build_answers(scenario):
    """بناء إجابات حسب السيناريو"""

    if scenario == "clean":
        # إجابة نظيفة بدون أي مشاكل
        income = random.choice(["from_3000_to_7000", "from_7001_to_15000", "above_15000"])
        brand = random.choice(BRANDS)
        return {
            "monthly_income": income,
            "luxury_purchase_frequency": "never" if income == "from_3000_to_7000" else random.choice(["never", "once_per_year"]),
            "internet_usage": "yes",
            "app_evaluation": random.choice(["excellent", "good", "average"]),
            "tv_usage": "yes",
            "favorite_tv_channels": random.choice(["sports", "news", "entertainment", "cultural"]),
            "purchase_frequency": random.choice(["two_to_three", "four_to_six"]),
            "monthly_spending": random.choice(["from_50_to_100", "from_100_to_300"]),
            "brand_preference": brand,
            "last_purchase": brand,
            "purchase_reason": random.choice(REASONS),
        }

    elif scenario == "r01":
        # R-01: دخل منخفض + شراء فاخر
        brand = random.choice(BRANDS)
        return {
            "monthly_income": "less_than_3000",
            "luxury_purchase_frequency": random.choice(["once_per_year", "several_times_per_year", "monthly"]),
            "internet_usage": "yes",
            "app_evaluation": random.choice(["good", "average"]),
            "tv_usage": "yes",
            "favorite_tv_channels": random.choice(["sports", "news"]),
            "purchase_frequency": random.choice(["two_to_three", "four_to_six"]),
            "monthly_spending": random.choice(["from_50_to_100", "from_100_to_300"]),
            "brand_preference": brand,
            "last_purchase": brand,
            "purchase_reason": random.choice(REASONS),
        }

    elif scenario == "r02":
        # R-02: لا إنترنت + تقييم تطبيقات
        brand = random.choice(BRANDS)
        return {
            "monthly_income": random.choice(["from_3000_to_7000", "from_7001_to_15000"]),
            "luxury_purchase_frequency": "never",
            "internet_usage": "no",
            "app_evaluation": random.choice(["good", "average", "poor"]),
            "tv_usage": "yes",
            "favorite_tv_channels": random.choice(["sports", "news"]),
            "purchase_frequency": random.choice(["two_to_three", "four_to_six"]),
            "monthly_spending": random.choice(["from_50_to_100", "from_100_to_300"]),
            "brand_preference": brand,
            "last_purchase": brand,
            "purchase_reason": random.choice(REASONS),
        }

    elif scenario == "r03":
        # R-03: لا تلفاز + قنوات مفضلة
        brand = random.choice(BRANDS)
        return {
            "monthly_income": random.choice(["from_3000_to_7000", "from_7001_to_15000"]),
            "luxury_purchase_frequency": "never",
            "internet_usage": "yes",
            "app_evaluation": random.choice(["good", "average"]),
            "tv_usage": "no",
            "favorite_tv_channels": random.choice(["sports", "news", "entertainment", "cultural"]),
            "purchase_frequency": random.choice(["two_to_three", "four_to_six"]),
            "monthly_spending": random.choice(["from_50_to_100", "from_100_to_300"]),
            "brand_preference": brand,
            "last_purchase": brand,
            "purchase_reason": random.choice(REASONS),
        }

    elif scenario == "r04":
        # R-04: شراء كثير + إنفاق قليل
        brand = random.choice(BRANDS)
        return {
            "monthly_income": random.choice(["from_3000_to_7000", "from_7001_to_15000"]),
            "luxury_purchase_frequency": "never",
            "internet_usage": "yes",
            "app_evaluation": random.choice(["good", "average"]),
            "tv_usage": "yes",
            "favorite_tv_channels": random.choice(["sports", "news"]),
            "purchase_frequency": "more_than_six",
            "monthly_spending": "less_than_50",
            "brand_preference": brand,
            "last_purchase": brand,
            "purchase_reason": random.choice(REASONS),
        }

    elif scenario == "r05":
        # R-05: علامة مفضلة ≠ آخر شراء
        brands = random.sample(BRANDS, 2)
        return {
            "monthly_income": random.choice(["from_3000_to_7000", "from_7001_to_15000"]),
            "luxury_purchase_frequency": "never",
            "internet_usage": "yes",
            "app_evaluation": random.choice(["good", "average"]),
            "tv_usage": "yes",
            "favorite_tv_channels": random.choice(["sports", "news"]),
            "purchase_frequency": random.choice(["two_to_three", "four_to_six"]),
            "monthly_spending": random.choice(["from_50_to_100", "from_100_to_300"]),
            "brand_preference": brands[0],
            "last_purchase": brands[1],
            "purchase_reason": random.choice(REASONS),
        }

    elif scenario == "multi":
        # متعددة المشاكل — low quality
        brands = random.sample(BRANDS, 2)
        return {
            "monthly_income": "less_than_3000",
            "luxury_purchase_frequency": random.choice(["several_times_per_year", "monthly"]),
            "internet_usage": "no",
            "app_evaluation": random.choice(["good", "average"]),
            "tv_usage": "no",
            "favorite_tv_channels": random.choice(["sports", "entertainment"]),
            "purchase_frequency": "more_than_six",
            "monthly_spending": "less_than_50",
            "brand_preference": brands[0],
            "last_purchase": brands[1],
            "purchase_reason": random.choice(REASONS),
        }

    else:
        # عشوائي
        brand_a = random.choice(BRANDS)
        brand_b = random.choice(BRANDS)
        return {
            "monthly_income": random.choice(MONTHLY_INCOME),
            "luxury_purchase_frequency": random.choice(LUXURY_FREQ),
            "internet_usage": random.choice(INTERNET),
            "app_evaluation": random.choice(APP_EVAL),
            "tv_usage": random.choice(TV_USAGE),
            "favorite_tv_channels": random.choice(TV_CHANNELS),
            "purchase_frequency": random.choice(PURCHASE_FREQ),
            "monthly_spending": random.choice(SPENDING),
            "brand_preference": brand_a,
            "last_purchase": brand_b,
            "purchase_reason": random.choice(REASONS),
        }


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # توزيع السيناريوهات: 250 استجابة
    scenarios = (
        ["clean"] * 90 +   # 36% — جودة عالية
        ["r01"] * 25 +     # R-01 فقط
        ["r02"] * 20 +     # R-02 فقط
        ["r03"] * 20 +     # R-03 فقط
        ["r04"] * 20 +     # R-04 فقط
        ["r05"] * 25 +     # R-05 فقط
        ["multi"] * 35 +   # متعددة — جودة منخفضة
        ["random"] * 15    # عشوائية
    )
    random.shuffle(scenarios)

    inserted = 0
    for scenario in scenarios:
        response_time = random.randint(8, 180)  # بعضها سريع جداً لتفعيل R-06
        if scenario in ["multi", "random"] and random.random() < 0.4:
            response_time = random.randint(5, 14)  # سريع جداً

        answers = build_answers(scenario)
        score, quality, status, issues = compute_confidence(answers, response_time)

        response_id = str(uuid.uuid4())
        submitted_at = random_date(60)
        confirmed = 1 if status == "valid" else (1 if random.random() < 0.4 else 0)

        cursor.execute("""
            INSERT INTO responses
            (response_id, source, answers_json, response_time_seconds,
             confidence_score, quality_level, validation_status, final_confirmed, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            response_id,
            "web_form",
            json.dumps(answers, ensure_ascii=False),
            response_time,
            score,
            quality,
            status,
            confirmed,
            submitted_at
        ))

        for (issue_type, rule_name, severity, deduction, field_names,
             message_ar, explanation_ar, action_ar) in issues:
            cursor.execute("""
                INSERT INTO validation_issues
                (issue_id, response_id, issue_type, rule_name, severity, deduction,
                 field_names_json, message_ar, explanation_ar, suggested_action_ar, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                response_id,
                issue_type,
                rule_name,
                severity,
                deduction,
                json.dumps(field_names),
                message_ar,
                explanation_ar,
                action_ar,
                submitted_at
            ))

        # إضافة correction_actions للاستجابات المؤكدة التي بها مشاكل
        if confirmed and issues and random.random() < 0.6:
            field = random.choice(issues[0][4])
            cursor.execute("""
                INSERT INTO correction_actions
                (action_id, response_id, field_name, previous_value, updated_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                response_id,
                field,
                "old_value",
                "corrected_value",
                submitted_at
            ))

        inserted += 1

    conn.commit()
    conn.close()
    print(f"تم إدخال {inserted} استجابة تجريبية بنجاح.")
    print(f"موقع قاعدة البيانات: {DB_PATH}")


if __name__ == "__main__":
    seed()
