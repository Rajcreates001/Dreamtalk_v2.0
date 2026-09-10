"""Auto-seed demo users + identity profiles on backend startup."""

import hashlib
import os
import uuid
import json
import logging

logger = logging.getLogger("dreamtalk.seed")

DEMO_USERS = [
    {
        "email": "demo@dreamtalk.ai",
        "password": "demo1234",
        "full_name": "Alex Demo",
        "role": "personal",
    },
    {
        "email": "health@dreamtalk.ai",
        "password": "demo1234",
        "full_name": "Dr. Sarah Demo",
        "role": "healthcare",
    },
    {
        "email": "business@dreamtalk.ai",
        "password": "demo1234",
        "full_name": "Raj Business",
        "role": "business",
    },
]


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + key.hex()


async def auto_seed(pool):
    """Create demo users if they don't exist."""
    for u in DEMO_USERS:
        existing = await pool.fetchrow("SELECT id FROM users WHERE email = $1", u["email"])
        if existing:
            continue

        user_id = str(uuid.uuid4())
        pw_hash = _hash_password(u["password"])

        await pool.execute(
            """INSERT INTO users (id, email, password_hash, full_name, role, is_verified, is_active, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, TRUE, TRUE, NOW(), NOW())""",
            user_id, u["email"], pw_hash, u["full_name"], u["role"],
        )

        await pool.execute(
            """INSERT INTO subscriptions (id, user_id, tier, status, current_period_start, current_period_end)
               VALUES ($1, $2, 'free', 'active', NOW(), NOW() + INTERVAL '100 years')""",
            str(uuid.uuid4()), user_id,
        )

        await pool.execute(
            """INSERT INTO user_settings (id, user_id) VALUES ($1, $2)""",
            str(uuid.uuid4()), user_id,
        )

        logger.info("Seeded demo user: %s (role: %s)", u["email"], u["role"])


async def auto_seed_identities(pool):
    """Create identity profiles for existing custom digital humans that lack one."""
    rows = await pool.fetch(
        """SELECT cdh.id, cdh.user_id
           FROM custom_digital_humans cdh
           LEFT JOIN identity_profiles ip ON ip.custom_dh_id = cdh.id
           WHERE ip.id IS NULL""",
    )
    for r in rows:
        identity_id = str(uuid.uuid4())
        now_str = "NOW()"
        default_appearance = json.dumps({
            "face_embedding": [], "face_mesh": [], "head_pose": {},
            "expression_library": {}, "hair_model": {}, "skin_profile": {},
            "eye_profile": {}, "mouth_profile": {}, "landmarks": [],
            "identity_vector": [], "quality_score": 0.0,
            "capture_type": "default", "source_media": [],
            "reconstructed_3d_mesh_url": None, "blendshapes": {},
        })
        default_voice = json.dumps({
            "voice_embedding": [], "voice_samples": [],
            "speaking_style": "conversational", "accent": "neutral",
            "language": "en", "pitch_range": {}, "rhythm_profile": {},
            "pause_pattern": {}, "cloned_voice_id": None,
        })
        default_personality = json.dumps({
            "big_five": {
                "openness": 0.5, "conscientiousness": 0.5,
                "extraversion": 0.5, "agreeableness": 0.5,
                "neuroticism": 0.3,
            },
            "communication_style": "neutral", "humor": 0.4,
            "professionalism": 0.7, "empathy": 0.7,
            "leadership": 0.5, "creativity": 0.5, "patience": 0.7,
        })
        default_evolution = json.dumps({
            "version": "1.0.0", "previous_versions": [],
            "last_evolved": None, "evolution_count": 0,
            "interaction_count": 0,
        })
        default_behavior = json.dumps({
            "greeting_style": "formal", "response_length": "medium",
            "interruption_tolerance": 0.3, "small_talk_affinity": 0.6,
        })

        await pool.execute(
            """INSERT INTO identity_profiles
               (id, user_id, custom_dh_id, identity_version, appearance, voice,
                personality, knowledge, memory, evolution, behavior,
                created_at, updated_at)
               VALUES ($1, $2, $3, '1.0.0',
                       $4::jsonb, $5::jsonb, $6::jsonb,
                       '{}'::jsonb, '{}'::jsonb, $7::jsonb, $8::jsonb,
                       NOW(), NOW())""",
            identity_id, r["user_id"], r["id"],
            default_appearance, default_voice, default_personality,
            default_evolution, default_behavior,
        )
        logger.info("Seeded identity profile for custom_dh: %s", r["id"])


async def auto_seed_digital_twins(pool):
    """Create digital_twins for demo users if they don't exist."""
    for u in DEMO_USERS:
        user_row = await pool.fetchrow("SELECT id FROM users WHERE email = $1", u["email"])
        if not user_row:
            continue
        user_id = user_row["id"]

        existing = await pool.fetchrow(
            "SELECT id FROM digital_twins WHERE user_id = $1", user_id,
        )
        if existing:
            continue

        twin_id = str(uuid.uuid4())
        role = u["role"] if u["role"] in ("personal", "healthcare", "business") else "personal"

        if role == "healthcare":
            personality = json.dumps({
                "empathy": 0.85, "professionalism": 0.9, "humor": 0.3,
                "creativity": 0.4, "confidence": 0.8, "patience": 0.85,
                "friendliness": 0.7, "leadership": 0.6, "curiosity": 0.7,
                "formality": 0.7, "optimism": 0.7, "emotional_stability": 0.85,
                "communication_style": "professional_warm",
                "response_length_preference": "medium",
                "small_talk_affinity": 0.3, "interruption_tolerance": 0.2,
                "topic_change_style": "smooth",
            })
        elif role == "business":
            personality = json.dumps({
                "empathy": 0.5, "professionalism": 0.9, "humor": 0.3,
                "creativity": 0.5, "confidence": 0.8, "patience": 0.7,
                "friendliness": 0.6, "leadership": 0.75, "curiosity": 0.7,
                "formality": 0.7, "optimism": 0.7, "emotional_stability": 0.8,
                "communication_style": "professional",
                "response_length_preference": "medium",
                "small_talk_affinity": 0.4, "interruption_tolerance": 0.3,
                "topic_change_style": "smooth",
            })
        else:
            personality = json.dumps({
                "empathy": 0.6, "professionalism": 0.5, "humor": 0.6,
                "creativity": 0.6, "confidence": 0.6, "patience": 0.7,
                "friendliness": 0.8, "leadership": 0.4, "curiosity": 0.7,
                "formality": 0.3, "optimism": 0.7, "emotional_stability": 0.6,
                "communication_style": "casual",
                "response_length_preference": "medium",
                "small_talk_affinity": 0.7, "interruption_tolerance": 0.4,
                "topic_change_style": "natural",
            })

        await pool.execute(
            """INSERT INTO digital_twins
               (id, user_id, name, description, category, role, status,
                personality_data, personality_status, twin_version, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7,
                       $8::jsonb, 'complete', '1.0.0', NOW(), NOW())""",
            twin_id, user_id,
            f"{u['full_name']}'s Twin",
            f"Digital twin for {u['full_name']}",
            role, role, "published",
            personality,
        )
        logger.info("Seeded digital twin for user: %s (role: %s)", u["email"], role)


async def auto_seed_organizations(pool):
    """Create demo organizations + departments + employees for healthcare and business users."""
    for u in DEMO_USERS:
        if u["role"] not in ("healthcare", "business"):
            continue

        user_row = await pool.fetchrow("SELECT id FROM users WHERE email = $1", u["email"])
        if not user_row:
            continue
        user_id = user_row["id"]

        existing_org = await pool.fetchrow(
            "SELECT id FROM organizations WHERE created_by = $1", user_id,
        )
        if existing_org:
            continue

        org_id = str(uuid.uuid4())
        org_name = "Apollo Research Hospital" if u["role"] == "healthcare" else "DreamCorp Enterprises"
        org_type = "healthcare" if u["role"] == "healthcare" else "business"

        await pool.execute(
            """INSERT INTO organizations (id, name, org_type, description, industry, created_by, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())""",
            org_id, org_name, org_type,
            f"Demo {org_type} organization for {u['full_name']}",
            "Healthcare" if org_type == "healthcare" else "Technology",
            user_id,
        )

        # Create departments
        dept_names = ["Cardiology", "Neurology", "Pediatrics"] if org_type == "healthcare" \
            else ["Engineering", "Sales", "HR", "Support"]
        for dept_name in dept_names:
            dept_id = str(uuid.uuid4())
            await pool.execute(
                """INSERT INTO departments (id, org_id, name, description, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, NOW(), NOW())""",
                dept_id, org_id, dept_name, f"{dept_name} department",
            )

        # Create digital employees
        twin = await pool.fetchrow(
            "SELECT id FROM digital_twins WHERE user_id = $1 LIMIT 1", user_id,
        )
        twin_id = str(twin["id"]) if twin else None

        emp_names = ["Dr. John", "Dr. Sarah", "Dr. Raj"] if org_type == "healthcare" \
            else ["Alex CEO", "Priya HR", "Raj Sales"]
        emp_titles = ["Cardiologist", "Neurologist", "Pediatrician"] if org_type == "healthcare" \
            else ["CEO Clone", "HR Manager Clone", "Sales Representative"]

        for i, (ename, etitle) in enumerate(zip(emp_names, emp_titles)):
            dept = await pool.fetchrow(
                "SELECT id FROM departments WHERE org_id = $1 ORDER BY name LIMIT 1 OFFSET $2",
                org_id, min(i, len(dept_names) - 1),
            )
            emp_id = str(uuid.uuid4())
            await pool.execute(
                """INSERT INTO digital_employees
                   (id, org_id, department_id, twin_id, name, title, role, level, status, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())""",
                emp_id, org_id, str(dept["id"]) if dept else None, twin_id,
                ename, etitle, etitle.lower().replace(" ", "_"), "senior",
                "available",
            )

        logger.info("Seeded organization: %s with digital workforce", org_name)
