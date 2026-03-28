# Phase 3: Platform Settings — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete platform settings infrastructure — add missing BRD settings, enforce maintenance mode, externalize hardcoded platform names, and add type/allowed_values validation on all setting writes.

**Architecture:** Settings are stored in `setting_definitions` (schema) + `setting_values` (data) with a cascade resolver (cycle → season → competition → global → default). This phase adds 4 new settings from the BRD, wires maintenance mode into the middleware, replaces every hardcoded "حرب الأسماء" with dynamic lookups, and adds server-side validation to the admin settings endpoints. All changes are backend-only (Python/FastAPI).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, PostgreSQL JSONB

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/core/seed.py` | Modify | Add 4 missing BRD settings + `allowed_values` on relevant definitions |
| `backend/app/core/middleware.py` | Modify | Add `invalidate_maintenance_cache()` export |
| `backend/app/main.py` | Modify | Expand `/api/public/branding` with new fields |
| `backend/app/modules/landing/router.py` | Modify | Replace hardcoded "حرب الأسماء" with dynamic setting lookup |
| `backend/app/modules/settings/service.py` | Modify | Add `validate_setting_value()` function |
| `backend/app/modules/admin/router.py` | Modify | Wire validation + audit trail into settings endpoints |

---

## Task 1: Add missing BRD settings to seed

**Files:**
- Modify: `backend/app/core/seed.py`

The BRD specifies 4 settings not yet seeded: `platform_logo_url`, `google_ads_id`, `ad_consent_required`, `og_image_url`.

- [ ] **Step 1: Add stable UUIDs for the 4 new settings**

In `seed.py`, add to the `SETTING_IDS` dict (after `google_analytics_id`):

```python
    "platform_logo_url": uuid.UUID("00000000-0000-0000-0000-000000000066"),
    "google_ads_id": uuid.UUID("00000000-0000-0000-0000-000000000067"),
    "ad_consent_required": uuid.UUID("00000000-0000-0000-0000-000000000068"),
    "og_image_url": uuid.UUID("00000000-0000-0000-0000-000000000069"),
```

- [ ] **Step 2: Add seed definitions for the 4 new settings**

Append to `settings_data` list inside `_seed_settings()`, after the `google_analytics_id` entry:

```python
        {
            "id": SETTING_IDS["platform_logo_url"],
            "key": "platform_logo_url",
            "category": "branding",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "/assets/logo.png"},
            "description": "رابط شعار المنصة",
        },
        {
            "id": SETTING_IDS["google_ads_id"],
            "key": "google_ads_id",
            "category": "analytics",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": ""},
            "description": "معرّف Google Ads (مثال: AW-XXXXXXXXX)",
        },
        {
            "id": SETTING_IDS["ad_consent_required"],
            "key": "ad_consent_required",
            "category": "privacy",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "إظهار بانر الموافقة على الإعلانات/ملفات تعريف الارتباط",
        },
        {
            "id": SETTING_IDS["og_image_url"],
            "key": "og_image_url",
            "category": "seo",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "/assets/og-image.png"},
            "description": "صورة Open Graph الافتراضية للمشاركة",
        },
```

- [ ] **Step 3: Add `allowed_values` to relevant existing seed definitions**

Update these entries in `settings_data` to include `allowed_values`:

For `attack_decay_factor`: add `"allowed_values": {"min": 0, "max": 1}`
For `protection_partial_reduction`: add `"allowed_values": {"min": 0, "max": 1}`
For `attack_cooldown_seconds`: add `"allowed_values": {"min": 0, "max": 3600}`
For `attack_max_per_cycle`: add `"allowed_values": {"min": 1, "max": 100}`
For `quiz_default_duration`: add `"allowed_values": {"min": 5, "max": 300}`
For `store_max_inventory`: add `"allowed_values": {"min": 1, "max": 100}`
For `protection_full_attack_count`: add `"allowed_values": {"min": 1, "max": 50}`
For `protection_duration_hours`: add `"allowed_values": {"min": 1, "max": 168}`
For `score_initial_balance`: add `"allowed_values": {"min": 0, "max": 1000000}`
For `attack_base_reward`: add `"allowed_values": {"min": 0, "max": 100000}`
For `attack_base_penalty`: add `"allowed_values": {"min": 0, "max": 100000}`

Note: `allowed_values` uses `{"min": X, "max": Y}` for numeric ranges and `{"options": [...]}` for enum-like strings. Boolean settings don't need `allowed_values`.

- [ ] **Step 4: Rebuild Docker and verify seed runs without errors**

```bash
docker compose up --build -d && docker compose logs -f backend --tail=50
```

Expected: Settings seeded successfully, no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/seed.py
git commit -m "feat(settings): seed 4 missing BRD settings + allowed_values constraints"
```

---

## Task 2: Maintenance mode cache invalidation

**Files:**
- Modify: `backend/app/core/middleware.py`
- Modify: `backend/app/modules/admin/router.py`

When an admin toggles `maintenance_mode`, the 30-second cache means there's a delay before it takes effect. Add an explicit cache invalidation call.

- [ ] **Step 1: Add cache invalidation function to middleware.py**

Add after the `get_maintenance_message` function in `middleware.py`:

```python
def invalidate_maintenance_cache() -> None:
    """Force the next request to reload maintenance settings from DB."""
    global _maintenance_cache_expires_at
    _maintenance_cache_expires_at = 0.0
```

- [ ] **Step 2: Wire invalidation into admin settings update endpoint**

In `backend/app/modules/admin/router.py`, inside the `update_setting` function (around line 2763, after `await session.commit()`), add:

```python
        # Invalidate maintenance cache if maintenance_mode was changed
        if setting_key in ("maintenance_mode", "maintenance_message"):
            from app.core.middleware import invalidate_maintenance_cache
            invalidate_maintenance_cache()
```

- [ ] **Step 3: Add audit trail to global settings update**

The global `PATCH /settings/{key}` endpoint currently has no audit trail (the competition-scoped one does). Add it. In the `update_setting` function, capture `old_value` before the upsert and write audit after commit:

Before the upsert block:
```python
        old_value = sv.value if sv else None
```

After `await session.commit()`:
```python
        from app.modules.audit.service import write_audit
        await write_audit(
            session,
            actor_id=admin.id,
            subject_type="setting",
            subject_id=defn.id,
            event_type="setting_updated",
            summary=f"تحديث إعداد عام: {setting_key}",
            before_state={"value": old_value},
            after_state={"value": body.value},
        )
        await session.commit()
```

Note: This requires a second commit since audit is written after the setting commit. Alternatively, move the audit write before the first commit so both happen atomically.

- [ ] **Step 4: Rebuild Docker and test maintenance toggle**

```bash
docker compose up --build -d
# Toggle maintenance on:
curl -X PATCH http://localhost:8000/api/admin/settings/maintenance_mode \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"value": {"v": true}}'
# Verify blocked:
curl http://localhost:8000/api/game-info
# Expected: 503 with maintenance message
# Verify admin still works:
curl http://localhost:8000/api/admin/dashboard -H "Authorization: Bearer <TOKEN>"
# Expected: 200
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/middleware.py backend/app/modules/admin/router.py
git commit -m "feat(maintenance): cache invalidation on toggle + audit trail for global settings"
```

---

## Task 3: Expand public branding API

**Files:**
- Modify: `backend/app/main.py`

Add `platform_logo_url`, `og_image_url`, `registration_enabled`, and `ad_consent_required` to the public branding response.

- [ ] **Step 1: Update the `/api/public/branding` endpoint**

Replace the current `get_public_branding` function in `main.py`:

```python
@app.get("/api/public/branding")
async def get_public_branding():
    """Public endpoint for platform branding (no auth required)."""
    from app.modules.settings.service import get_settings_batch

    keys = [
        "platform_name", "platform_description", "platform_logo_url",
        "og_image_url", "maintenance_mode", "registration_enabled",
        "ad_consent_required", "google_analytics_id", "google_ads_id",
    ]
    async with async_session() as session:
        vals = await get_settings_batch(session, keys)

    return {
        "name": vals.get("platform_name") or "حرب الأسماء",
        "description": vals.get("platform_description") or "",
        "logo_url": vals.get("platform_logo_url") or "/assets/logo.png",
        "og_image_url": vals.get("og_image_url") or "/assets/og-image.png",
        "maintenance": bool(vals.get("maintenance_mode")),
        "registration_enabled": vals.get("registration_enabled", True),
        "ad_consent_required": vals.get("ad_consent_required", True),
        "google_analytics_id": vals.get("google_analytics_id") or "",
        "google_ads_id": vals.get("google_ads_id") or "",
    }
```

- [ ] **Step 2: Rebuild and test**

```bash
docker compose up --build -d
curl http://localhost:8000/api/public/branding | python -m json.tool
```

Expected: All 9 fields returned with correct defaults.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(branding): expand public branding API with logo, OG image, analytics IDs"
```

---

## Task 4: Externalize hardcoded "حرب الأسماء" in landing router

**Files:**
- Modify: `backend/app/modules/landing/router.py`

Replace all hardcoded "حرب الأسماء" with dynamic `platform_name` from settings.

- [ ] **Step 1: Add a helper to fetch platform name**

At the top of `landing/router.py` (after imports), add:

```python
async def _get_platform_name() -> str:
    """Fetch platform_name from settings (with fallback)."""
    from app.modules.settings.service import get_setting
    async with async_session() as session:
        name = await get_setting(session, "platform_name")
    return name or "حرب الأسماء"
```

- [ ] **Step 2: Update `_build_invite_preview_html` to accept platform_name parameter**

Change the function signature and body:

```python
def _build_invite_preview_html(competition_name: str | None, token: str, platform_name: str) -> str:
    """Build minimal HTML with OG meta tags for social media bot crawlers."""
    if competition_name:
        title = f"انضم لمنافسة {competition_name} — {platform_name}"
        description = f"لقد تمت دعوتك للانضمام إلى منافسة {competition_name} في {platform_name}!"
        og_title = f"انضم لمنافسة {competition_name} — {platform_name}"
        twitter_title = f"انضم لمنافسة {competition_name}"
        redirect_url = f"/invite/{token}"
    else:
        title = f"{platform_name} — أقوى منافسة عربية"
        description = "اكشف الأقنعة وهاجم الخصوم في أقوى منافسة عربية!"
        og_title = f"{platform_name} — أقوى منافسة عربية"
        twitter_title = platform_name
        redirect_url = "/invite/{token}".format(token=token) if token else "/"
    # ... rest of template unchanged
```

- [ ] **Step 3: Update callers to pass platform_name**

In `invite_preview_html`:
```python
    platform_name = await _get_platform_name()
    return HTMLResponse(content=_build_invite_preview_html(competition_name, token, platform_name))
```

In `landing_preview_html`, replace the hardcoded strings similarly:
```python
    platform_name = await _get_platform_name()
    if competition_name:
        title = f"انضم لمنافسة {competition_name} — {platform_name}"
        description = f"لقد تمت دعوتك للانضمام إلى منافسة {competition_name} في {platform_name}!"
        twitter_title = f"انضم لمنافسة {competition_name}"
    else:
        title = f"{platform_name} — أقوى منافسة عربية"
        description = "اكشف الأقنعة وهاجم الخصوم في أقوى منافسة عربية!"
        twitter_title = platform_name
```

- [ ] **Step 4: Rebuild and test OG preview**

```bash
docker compose up --build -d
curl http://localhost:8000/api/invite-preview/WAR2026
# Expected: HTML with "حرب الأسماء" (from setting, not hardcoded)
curl http://localhost:8000/api/landing-preview/test
# Expected: Same — platform name from settings
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/landing/router.py
git commit -m "feat(branding): externalize platform name in landing/invite OG previews"
```

---

## Task 5: Settings validation engine

**Files:**
- Modify: `backend/app/modules/settings/service.py`

Add a `validate_setting_value()` function that enforces `data_type` and `allowed_values`.

- [ ] **Step 1: Add the validation function**

Append to `service.py`:

```python
from app.core.enums import SettingDataType


def validate_setting_value(defn: "SettingDefinition", value: dict) -> str | None:
    """Validate a setting value against its definition.

    Args:
        defn: The SettingDefinition row.
        value: The JSONB value dict (e.g. {"v": 42}).

    Returns:
        None if valid, or an Arabic error message string if invalid.
    """
    if not isinstance(value, dict) or "v" not in value:
        return "القيمة يجب أن تكون بصيغة {\"v\": ...}"

    v = value["v"]

    # ── Type check ──
    if defn.data_type == SettingDataType.INTEGER:
        if not isinstance(v, int) or isinstance(v, bool):
            return f"الإعداد {defn.key} يتطلب قيمة عددية صحيحة"
    elif defn.data_type == SettingDataType.DECIMAL:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return f"الإعداد {defn.key} يتطلب قيمة رقمية"
    elif defn.data_type == SettingDataType.BOOLEAN:
        if not isinstance(v, bool):
            return f"الإعداد {defn.key} يتطلب قيمة منطقية (true/false)"
    elif defn.data_type == SettingDataType.STRING:
        if not isinstance(v, str):
            return f"الإعداد {defn.key} يتطلب قيمة نصية"
    elif defn.data_type == SettingDataType.JSON:
        pass  # Any JSON-serializable value is fine

    # ── allowed_values check ──
    if defn.allowed_values:
        av = defn.allowed_values

        # Range check: {"min": X, "max": Y}
        if "min" in av and isinstance(v, (int, float)):
            if v < av["min"]:
                return f"القيمة يجب أن تكون {av['min']} على الأقل"
        if "max" in av and isinstance(v, (int, float)):
            if v > av["max"]:
                return f"القيمة يجب ألا تتجاوز {av['max']}"

        # Options check: {"options": ["a", "b", "c"]}
        if "options" in av:
            if v not in av["options"]:
                options_str = "، ".join(str(o) for o in av["options"])
                return f"القيمة يجب أن تكون إحدى: {options_str}"

    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/modules/settings/service.py
git commit -m "feat(settings): add validate_setting_value for type + allowed_values enforcement"
```

---

## Task 6: Wire validation into admin settings endpoints

**Files:**
- Modify: `backend/app/modules/admin/router.py`

- [ ] **Step 1: Add validation to global settings update**

In the `update_setting` function (around line 2738, after loading `defn`), add:

```python
        from app.modules.settings.service import validate_setting_value
        error = validate_setting_value(defn, body.value)
        if error:
            raise HTTPException(status_code=422, detail=error)
```

- [ ] **Step 2: Add validation to competition-scoped settings update**

In the `update_competition_setting` function (around line 3655, after loading `defn`), add the same validation:

```python
        from app.modules.settings.service import validate_setting_value
        error = validate_setting_value(defn, body.value)
        if error:
            raise HTTPException(status_code=422, detail=error)
```

- [ ] **Step 3: Rebuild and test validation**

```bash
docker compose up --build -d
# Test type rejection:
curl -X PATCH http://localhost:8000/api/admin/settings/attack_base_reward \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"value": {"v": "not_a_number"}}'
# Expected: 422 "الإعداد attack_base_reward يتطلب قيمة عددية صحيحة"

# Test range rejection:
curl -X PATCH http://localhost:8000/api/admin/settings/attack_decay_factor \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"value": {"v": 5.0}}'
# Expected: 422 "القيمة يجب ألا تتجاوز 1"

# Test valid update:
curl -X PATCH http://localhost:8000/api/admin/settings/attack_base_reward \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"value": {"v": 600}}'
# Expected: 200
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/admin/router.py
git commit -m "feat(settings): enforce type + allowed_values validation on admin settings updates"
```

---

## Task 7: Final verification

- [ ] **Step 1: Rebuild Docker from scratch**

```bash
docker compose down -v && docker compose up --build -d
```

- [ ] **Step 2: Verify all settings seeded**

```bash
curl http://localhost:8000/api/admin/settings -H "Authorization: Bearer <TOKEN>" | python -m json.tool | grep '"key"'
```

Expected: All 25 settings listed (19 existing + 6 platform from Sprint 1 branch changes + 4 new from this plan = but some overlap, total should be ~29 unique keys).

- [ ] **Step 3: Verify branding endpoint**

```bash
curl http://localhost:8000/api/public/branding | python -m json.tool
```

Expected: 9 fields with correct defaults.

- [ ] **Step 4: Verify maintenance mode flow**

Toggle on → verify 503 → toggle off → verify 200.

- [ ] **Step 5: Verify validation rejects bad values**

Send wrong types and out-of-range values to settings endpoint → verify 422 responses.

- [ ] **Step 6: Verify audit trail**

Check `/api/admin/audit` for setting_updated events after toggling settings.

- [ ] **Step 7: Final commit (if any cleanup needed)**

```bash
git add -A && git commit -m "chore: Phase 3 final cleanup"
```
