# War of Names — Admin Configuration & Game Data BRD
## Version 1.0 — Data-Driven Game Design

---

## 1. Purpose

This BRD defines how ALL game configuration, items, effects, settings, and content should be structured, stored, and managed. The goal: **every aspect of the game should be configurable through admin interfaces (Form + JSON) without code changes.**

This enables:
- Admins creating content via forms OR JSON
- LLM-generated content (items, questions, seasons) via JSON paste
- Rapid season setup from config files
- Game balance adjustments without deployments
- Multiple admins managing independent competitions

---

## 2. Current State Assessment

### What's Configurable (Working)
| Area | Endpoints | JSON Mode | Completeness |
|------|-----------|-----------|-------------|
| Items (create) | ✅ POST | ✅ Form+JSON | 85% — missing stackability, expiration, visibility |
| Items (edit) | ✅ PATCH | ✅ Form+JSON | 60% — PATCH only accepts name, desc, rarity, category |
| Item Effects (CRUD) | ✅ Full | ❌ Form only | 54% — 7 of 13 effect types implemented |
| Listings (create/edit) | ✅ POST/PATCH | ✅ Form+JSON | 70% — missing availability window, eligibility |
| Settings (10 keys) | ✅ Global + Competition | ❌ Form only | 80% — no season/cycle scope UI |
| Questions (CRUD) | ✅ Full | ✅ Form+JSON+Excel | 90% |
| Quiz Sessions | ✅ CRUD | ✅ Form | 85% — missing randomization |
| Seasons/Cycles | ✅ CRUD + lifecycle | ❌ Form only | 90% |
| Competition Config Export/Import | ✅ JSON | ✅ JSON | 80% |

### Critical Gaps
1. **Item PATCH doesn't accept ALL fields** — can't update usage_type, max_uses, stackability, expiration, visibility, effects via single PATCH
2. **6 effect types exist in enum but have NO backend handler** — creating them silently fails at runtime
3. **Listing availability window not exposed** — available_from/until exist in model but not in API
4. **Listing eligibility rules not configurable** — JSONB field exists but not exposed
5. **Settings scoping** — cascade supports season/cycle but admin UI only shows global/competition

---

## 3. Item System Architecture

### 3.1 Item Definition (Complete Schema)

Every item MUST support these fields via both Form and JSON:

```json
{
  "name": "string (required, unique per competition)",
  "description": "string (optional)",
  "rarity": "common | rare | epic | legendary | mythic",
  "category": "weapon | defense | special",
  "usage_type": "consumable | non_consumable | time_limited | persistent",
  "max_uses": "integer | null (null = unlimited)",
  "is_stackable": "boolean (default false) — can player hold multiple?",
  "expires_after_minutes": "integer | null (null = never expires)",
  "visibility": "visible | hidden",
  "status": "draft | active | disabled | archived",
  "effects": [ /* array of ItemEffect objects */ ]
}
```

### 3.2 Effect System (Complete Schema)

Each effect MUST support:

```json
{
  "effect_type": "string (required) — see Effect Type Reference",
  "parameters": "dict (required) — type-specific params",
  "description": "string — Arabic description shown to players",
  "target_scope": "self | target | all",
  "trigger_on": "activation | next_attack | next_defense | on_hit | passive",
  "duration_minutes": "integer | null (null = permanent/one-shot)",
  "is_stackable": "boolean (default false)",
  "order_index": "integer (execution priority, lower = first)"
}
```

### 3.3 Effect Type Reference

#### Implemented (7 types — backend handlers exist):

| Type | Parameters | Description | Example |
|------|-----------|-------------|---------|
| `ratio_modifier` | `{modifier: 0.1-10.0}` | Multiplies attack reward/penalty | 1.5 = +50% reward |
| `fixed_bonus` | `{amount: 1-50000}` | Grants flat points | +200 points |
| `loss_reduction` | `{reduction: 0.01-1.0}` | Reduces attack penalty by % | 0.5 = -50% loss |
| `action_prevention` | `{action: "attack"}` | Blocks actions for duration | Shield for 1 hour |
| `state_change` | `{state: "protection", value: "full\|partial\|none"}` | Changes player state | Grant full protection |
| `negative_effect` | `{sub_type: "deduct_points\|remove_protection", amount?: N}` | Debuff target | -100 points to enemy |
| `allow_alias_change` | `{}` | Grants alias change permission | One-time use |

#### Not Implemented (6 types — enum defined, NO handler):

| Type | Intended Use | Status |
|------|-------------|--------|
| `grant_item` | Give another item when used | ❌ Block creation until implemented |
| `grant_box` | Give loot box when used | ❌ Block creation until implemented |
| `modify_distribution` | Change reward distribution | ❌ Block creation until implemented |
| `time_limited_effect` | Apply effect for fixed time | ❌ Block creation until implemented |
| `cycle_effect` | Effect lasts one cycle | ❌ Block creation until implemented |
| `season_effect` | Effect lasts one season | ❌ Block creation until implemented |

**REQUIREMENT:** Admin API must REJECT creation of unimplemented effect types with clear Arabic error: "نوع التأثير غير مدعوم حالياً"

### 3.4 Trigger System

| Trigger | When Effect Activates | Use Case |
|---------|----------------------|----------|
| `activation` | Immediately on item use | Points, protection, alias change |
| `next_attack` | Player's next successful attack | Attack multiplier |
| `next_defense` | Player's next received attack | Defense shield |
| `on_hit` | Every time player is hit (while active) | Passive defense |
| `passive` | Always active while item is held | Ongoing buff |

### 3.5 Stacking Rules

- **Same effect type from same item:** NOT stackable (duplicate prevention)
- **Same effect type from different items:** Stackable if `is_stackable: true`
- **Different effect types:** Always combinable
- **Stacking mode:** Additive for fixed bonuses, multiplicative for ratios

---

## 4. Store Listing Configuration

### 4.1 Listing Schema (Complete)

```json
{
  "item_definition_id": "UUID (required) — or item_name for JSON import",
  "competition_id": "UUID (auto from context)",
  "price": "integer > 0 (required)",
  "max_per_participant": "integer | null (purchase limit per player)",
  "total_stock": "integer | null (total available, null = unlimited)",
  "status": "active | hidden | expired | sold_out",
  "available_from": "ISO datetime | null (null = immediately)",
  "available_until": "ISO datetime | null (null = never expires)",
  "eligibility_rules": {
    "min_balance": "integer | null (minimum points to purchase)",
    "min_rank": "integer | null (leaderboard position)",
    "required_cycle_status": "active | null",
    "excluded_bankrupt": "boolean (default true)"
  }
}
```

### 4.2 Missing API Support (to implement)

- **PATCH listing:** Add `available_from`, `available_until`, `eligibility_rules` to update schema
- **POST listing:** Add `available_from`, `available_until`, `eligibility_rules` to create schema
- **Frontend JSON template:** Include all fields with Arabic docs

---

## 5. Settings Configuration

### 5.1 Current Settings (10 keys)

| Key | Type | Default | Category | Description |
|-----|------|---------|----------|-------------|
| `attack_enabled` | BOOLEAN | false | attack | Enable/disable attacks |
| `attack_base_reward` | INTEGER | 500 | attack | Base points for successful attack |
| `attack_decay_factor` | DECIMAL | 0.8 | attack | Reward decay per stage (0.8 = 20% less each time) |
| `attack_base_penalty` | INTEGER | 100 | attack | Points lost on failed attack |
| `attack_max_per_cycle` | INTEGER | 3 | attack | Max successful attacks on same target per cycle |
| `score_initial_balance` | INTEGER | 1000 | score | Starting points for new members |
| `score_bankruptcy_threshold` | INTEGER | 0 | score | Balance at which bankruptcy triggers |
| `quiz_default_duration` | INTEGER | 30 | quiz | Default answer duration (seconds) |
| `store_max_inventory` | INTEGER | 10 | store | Max items player can hold |
| `protection_full_attack_count` | INTEGER | 3 | protection | Attacks before full protection |

### 5.2 Missing Settings (to add)

| Key | Type | Default | Category | Description |
|-----|------|---------|----------|-------------|
| `attack_self_penalty_on_fail` | BOOLEAN | true | attack | Should failed attacks cost points? |
| `attack_cooldown_seconds` | INTEGER | 5 | attack | Cooldown between attacks |
| `protection_partial_reduction` | DECIMAL | 0.5 | protection | Partial protection reduction % |
| `protection_duration_hours` | INTEGER | 24 | protection | How long full protection lasts |
| `bankruptcy_recovery_balance` | INTEGER | 500 | score | Balance granted when bankruptcy lifted at cycle start |
| `quiz_max_sessions_per_cycle` | INTEGER | 5 | quiz | Max quiz sessions per cycle |
| `store_purchase_cooldown_minutes` | INTEGER | 0 | store | Cooldown between purchases |
| `identity_reveal_on_bankruptcy` | BOOLEAN | true | identity | Show real name when bankrupt? |
| `season_auto_advance_cycles` | BOOLEAN | false | season | Auto-start next cycle when current ends? |

### 5.3 Settings Scoping Requirement

Admin UI must support ALL 4 levels:
1. **Global** — Platform-wide defaults
2. **Competition** — Per-competition overrides
3. **Season** — Per-season overrides (NOT currently exposed)
4. **Cycle** — Per-cycle overrides (NOT currently exposed)

---

## 6. JSON Configuration Format

### 6.1 Full Competition Config (Export/Import)

```json
{
  "version": "1.0",
  "competition": {
    "name": "موسم الحرب الكبرى",
    "description": "الموسم الثالث — أقوى المنافسات"
  },
  "settings": {
    "attack_enabled": true,
    "attack_base_reward": 600,
    "attack_decay_factor": 0.75,
    "attack_base_penalty": 150,
    "attack_max_per_cycle": 5,
    "score_initial_balance": 1500,
    "score_bankruptcy_threshold": -500,
    "store_max_inventory": 15,
    "protection_full_attack_count": 4
  },
  "items": [
    {
      "name": "درع التيتانيوم",
      "description": "درع متقدم يحمي من 3 هجمات قادمة",
      "rarity": "legendary",
      "category": "defense",
      "usage_type": "consumable",
      "max_uses": 1,
      "effects": [
        {
          "effect_type": "loss_reduction",
          "parameters": {"reduction": 0.75},
          "target_scope": "self",
          "trigger_on": "next_defense",
          "duration_minutes": 4320,
          "description": "تقليل الخسارة 75% لمدة 3 أيام"
        }
      ]
    }
  ],
  "store_listings": [
    {
      "item_name": "درع التيتانيوم",
      "price": 500,
      "max_per_participant": 1,
      "total_stock": 3
    }
  ],
  "questions": [
    {
      "group_name": "أسئلة الموسم الثالث",
      "questions": [
        {
          "prompt": "...",
          "question_type": "multiple_choice",
          "options": {"choices": ["أ","ب","ج","د"], "correct": "أ"},
          "correct_answer": {"answer": "أ"},
          "score_value": 10,
          "difficulty": "medium"
        }
      ]
    }
  ]
}
```

### 6.2 Template Documentation Standard

All JSON templates MUST include `_` prefixed instruction fields that are auto-stripped before API submission:

```json
{
  "_تعليمات": "احذف الحقول التي تبدأ بـ _ قبل الإرسال",
  "field": "value",
  "_الخيارات_المتاحة": "option1 | option2 | option3",
  "_شرح": "توضيح باللغة العربية"
}
```

The frontend `parseJsonInput()` utility automatically strips these before API calls.

### 6.3 LLM Prompt Template

When an admin wants to use an LLM to generate items:

```
أنشئ 10 عناصر لمنافسة حرب الأسماء بصيغة JSON.
المتطلبات:
- كل عنصر يحتاج: name, description, rarity, category, usage_type, effects
- الندرة: common, rare, epic, legendary, mythic (توزيع متوازن)
- الفئات: weapon (هجوم), defense (دفاع), special (خاص)
- أنواع التأثير المتاحة: ratio_modifier, fixed_bonus, loss_reduction, action_prevention, state_change, negative_effect, allow_alias_change
- كل تأثير يحتاج: effect_type, parameters, description, target_scope (self/target), trigger_on (activation/next_attack/next_defense)
- الأسماء والأوصاف باللغة العربية
- أرجع مصفوفة JSON فقط بدون تعليقات
```

---

## 7. Backend Changes Required

### 7.1 Priority 1 — Fix Item PATCH

Current PATCH only accepts `name, description, rarity, category`. MUST accept ALL fields:
- `usage_type`, `max_uses`, `is_stackable`, `expires_after_minutes`, `visibility`, `status`

### 7.2 Priority 2 — Block Unimplemented Effect Types

Add validation in effect creation endpoint:
```python
IMPLEMENTED_EFFECTS = {
    "ratio_modifier", "fixed_bonus", "loss_reduction",
    "action_prevention", "state_change", "negative_effect",
    "allow_alias_change"
}
if body.effect_type not in IMPLEMENTED_EFFECTS:
    raise HTTPException(400, "نوع التأثير غير مدعوم حالياً")
```

### 7.3 Priority 3 — Expose Listing Fields

Add to listing create/update: `available_from`, `available_until`, `eligibility_rules`

### 7.4 Priority 4 — Add Missing Settings

Seed the 9 new settings defined in section 5.2.

### 7.5 Priority 5 — Season/Cycle Settings UI

Add admin endpoints for season/cycle-level setting overrides.

---

## 8. Frontend Changes Required

### 8.1 Item Edit JSON — Pre-fill ALL Fields

When editing an item in JSON mode, ALL fields including effects must be pre-filled. Currently working. ✅

### 8.2 Effect Management in JSON

When creating items via JSON, effects should be created as part of the same request. The backend `POST /api/admin/store/items` should optionally accept an `effects` array and create them in the same transaction.

### 8.3 Settings JSON Mode

Add JSON toggle to AdminSettingsPage and AdminPlatformSettingsPage for bulk settings update.

---

## 9. Validation Rules

### Item Validation
- `name` required, 2-150 chars
- `rarity` must be valid enum
- `category` must be one of: weapon, defense, special
- `usage_type` must be valid enum
- `max_uses` must be > 0 if set
- `expires_after_minutes` must be > 0 if set
- `effects` array: each effect must pass effect validation

### Effect Validation
- `effect_type` must be in IMPLEMENTED_EFFECTS set
- `parameters` must match expected schema for the effect type
- `target_scope` must be valid for the effect type (e.g., negative_effect requires "target")
- `duration_minutes` required for time-based effects
- `trigger_on` must be valid for the effect type

### Listing Validation
- `price` must be > 0
- `total_stock` must be > 0 if set
- `max_per_participant` must be > 0 if set
- `available_from` must be before `available_until`
- Item must exist and be active

### Question Validation
- `prompt` required, non-empty
- `question_type` must be valid enum
- `options.choices` must have 2+ items
- `options.correct` must be in choices
- `correct_answer.answer` must match `options.correct`
- `score_value` must be > 0

---

## 10. Migration Path

### Phase 1 (Immediate)
1. Fix item PATCH to accept all fields
2. Block unimplemented effect types
3. Add missing fields to listing endpoints
4. Update JSON templates to reflect actual API capabilities

### Phase 2 (Next Sprint)
1. Seed missing settings (section 5.2)
2. Add season/cycle-level settings endpoints
3. Add inline effects creation in item POST
4. Add settings JSON mode to admin UI

### Phase 3 (Future)
1. Implement remaining effect types (grant_item, grant_box, etc.)
2. Add effect interaction/conflict detection
3. Add config versioning with rollback
4. Add preview/test mode for config changes

---

## References

- Industry Research: `docs/Research - Admin Config, Items & Game Settings - Industry Patterns.md`
- Main BRD: `docs/War of Names - Main - BRD - V1.0.md` (sections 12.8, 12.16)
- Compliance BRD: `docs/War of Names - Compliance & Regulations BRD - V1.0.md`
- Current Implementation: Backend `modules/store/`, `modules/settings/`, `modules/admin/`
