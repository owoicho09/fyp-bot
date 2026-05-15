print("[supabase_service.py] Loading Supabase service...")

import json
from datetime import datetime, timezone
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

print("[supabase_service.py] Connecting to Supabase...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("[supabase_service.py] Supabase client ready.")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json_field(value) -> list | dict:
    """Safely parse a JSON field that might come back as string or object."""
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    return []


# ─── USER OPERATIONS ──────────────────────────────────────────────────────────

def get_or_create_user(
    telegram_id: int,
    first_name: str = None,
    username: str = None,
) -> dict:
    print(f"[supabase] get_or_create_user: telegram_id={telegram_id}")
    result = (
        supabase.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    if result.data:
        print(f"[supabase] Existing user found: {telegram_id}")
        return result.data[0]

    print(f"[supabase] Creating new user: {telegram_id}")
    insert = (
        supabase.table("users")
        .insert({
            "telegram_id": telegram_id,
            "first_name":  first_name,
            "username":    username,
        })
        .execute()
    )
    print(f"[supabase] New user created: {telegram_id}")
    return insert.data[0]


def get_user(telegram_id: int) -> dict | None:
    print(f"[supabase] get_user: {telegram_id}")
    result = (
        supabase.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    return result.data[0] if result.data else None


def update_user(telegram_id: int, data: dict) -> dict:
    print(f"[supabase] update_user: {telegram_id} | fields={list(data.keys())}")
    result = (
        supabase.table("users")
        .update(data)
        .eq("telegram_id", telegram_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def is_subscribed(telegram_id: int) -> bool:
    print(f"[supabase] is_subscribed check: {telegram_id}")
    user = get_user(telegram_id)
    if not user:
        return False
    if user.get("subscription_status") != "active":
        return False
    expires = user.get("subscription_expires_at")
    if expires:
        try:
            expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if expires_dt < datetime.now(timezone.utc):
                print(f"[supabase] Subscription expired for {telegram_id}")
                update_user(telegram_id, {"subscription_status": "expired"})
                return False
        except Exception as e:
            print(f"[supabase] Error parsing expiry date: {e}")
            return False
    print(f"[supabase] User {telegram_id} is subscribed.")
    return True


# ─── PROJECT OPERATIONS ───────────────────────────────────────────────────────

def get_active_project(telegram_id: int) -> dict | None:
    print(f"[supabase] get_active_project: {telegram_id}")
    result = (
        supabase.table("projects")
        .select("*")
        .eq("telegram_id", telegram_id)
        .eq("status", "in_progress")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def create_project(telegram_id: int, brief: dict) -> dict:
    print(f"[supabase] create_project: {telegram_id}")
    existing = get_active_project(telegram_id)
    if existing:
        print(f"[supabase] Abandoning old project {existing['id']} for {telegram_id}")
        supabase.table("projects").update(
            {"status": "abandoned"}
        ).eq("id", existing["id"]).execute()

    # Pull user fields so project record is self-contained
    user = get_user(telegram_id) or {}

    result = (
        supabase.table("projects")
        .insert({
            "telegram_id":         telegram_id,
            "topic":               brief.get("topic", ""),
            "research_question":   brief.get("research_question", ""),
            "population":          brief.get("population", ""),
            "time_frame":          brief.get("time_frame", ""),
            "research_type":       brief.get("research_type", ""),
            "citation_style":      brief.get("citation_style", ""),
            "objectives":          json.dumps(brief.get("objectives", [])),
            "hypotheses":          json.dumps(brief.get("hypotheses", [])),
            "turnitin":            brief.get("turnitin", False),
            "supervisor_context":  brief.get("supervisor_context", ""),
            "nigerian_context":    brief.get("nigerian_context", ""),
            "student_background":  brief.get("student_background", ""),
            "department":          brief.get("department", "") or user.get("department", ""),
            "university":          brief.get("university", "") or user.get("university", ""),
            "academic_level":      brief.get("academic_level", "") or user.get("academic_level", "bsc"),
            "faculty":             brief.get("faculty", "") or user.get("faculty", ""),
            "chapter_format":      brief.get("chapter_format", ""),

            "citation_year_from": brief.get("citation_year_from", 2019),
            "chapter_format": brief.get("chapter_format", ""),

            "chapters_completed":  0,
            "verified_references": json.dumps([]),
            "status":              "in_progress",
        })
        .execute()
    )
    print(f"[supabase] Project created: {result.data[0]['id']} for {telegram_id}")
    return result.data[0]



def update_project(telegram_id: int, data: dict) -> dict:
    print(f"[supabase] update_project: {telegram_id} | fields={list(data.keys())}")
    project = get_active_project(telegram_id)
    if not project:
        print(f"[supabase] WARNING: No active project for {telegram_id}")
        return {}
    result = (
        supabase.table("projects")
        .update(data)
        .eq("id", project["id"])
        .execute()
    )
    return result.data[0] if result.data else {}


def save_chapter_content(
    telegram_id: int,
    chapter_number: int,
    content: str,
) -> dict:
    print(f"[supabase] save_chapter_content: {telegram_id} ch{chapter_number}")
    project = get_active_project(telegram_id)
    if not project:
        print(f"[supabase] ERROR: No active project for {telegram_id}")
        return {}
    return update_project(telegram_id, {
        f"chapter_{chapter_number}_content": content,
        "chapters_completed": max(
            project.get("chapters_completed", 0),
            chapter_number
        ),
        "current_chapter": chapter_number,
    })


def add_verified_reference(telegram_id: int, reference: dict) -> None:
    print(f"[supabase] add_verified_reference: {telegram_id}")
    project = get_active_project(telegram_id)
    if not project:
        return
    refs = _parse_json_field(project.get("verified_references", []))
    # Avoid duplicate DOIs
    existing_dois = {r.get("doi") for r in refs if r.get("doi")}
    if reference.get("doi") and reference["doi"] in existing_dois:
        print(f"[supabase] Duplicate DOI skipped: {reference['doi']}")
        return
    refs.append(reference)
    update_project(telegram_id, {"verified_references": json.dumps(refs)})
    print(f"[supabase] Reference added. Total: {len(refs)}")


def get_verified_references(telegram_id: int) -> list:
    print(f"[supabase] get_verified_references: {telegram_id}")
    project = get_active_project(telegram_id)
    if not project:
        return []
    return _parse_json_field(project.get("verified_references", []))


# ─── SESSION OPERATIONS ───────────────────────────────────────────────────────

def get_session(telegram_id: int) -> dict | None:
    print(f"[supabase] get_session: {telegram_id}")
    result = (
        supabase.table("sessions")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_session(
    telegram_id: int,
    state: str,
    temp_data: dict = None,
) -> dict:
    print(f"[supabase] upsert_session: {telegram_id} | state={state}")
    result = (
        supabase.table("sessions")
        .upsert(
            {
                "telegram_id": telegram_id,
                "state":       state,
                "temp_data":   json.dumps(temp_data or {}),
            },
            on_conflict="telegram_id",
        )
        .execute()
    )
    return result.data[0] if result.data else {}


def clear_session(telegram_id: int) -> None:
    print(f"[supabase] clear_session: {telegram_id}")
    upsert_session(telegram_id, "idle", {})

# ─── ADMIN / STATS ────────────────────────────────────────────────────────────

def get_total_users() -> int:
    print("[supabase] get_total_users")
    result = supabase.table("users").select("id", count="exact").execute()
    return result.count or 0


def get_total_paid_users() -> int:
    print("[supabase] get_total_paid_users")
    result = (
        supabase.table("users")
        .select("id", count="exact")
        .eq("subscription_status", "active")
        .execute()
    )
    return result.count or 0


def get_total_projects() -> int:
    print("[supabase] get_total_projects")
    result = supabase.table("projects").select("id", count="exact").execute()
    return result.count or 0


print("[supabase_service.py] All functions loaded.")