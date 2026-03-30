"""
Effect type configuration — validation rules, required fields, and Arabic summaries.

This module is the single source of truth for:
  - Which effect types are supported
  - What parameters each type requires
  - How to validate those parameters
  - How to generate a human-readable Arabic summary
  - Which trigger modes are allowed per effect type

Trigger modes:
  - "activation"    — fires immediately when item is used (instant or timed)
  - "next_success"  — fires on the player's next successful attack
  - "next_failure"  — fires on the player's next failed attack
  - "next_defense"  — fires when the player is attacked successfully
"""

from app.core.enums import EffectType

# ── Trigger mode labels ──────────────────────────────────────────────────

TRIGGER_LABELS = {
    "activation": "فوري (عند الاستخدام)",
    "next_success": "عند نجاح الهجوم التالي",
    "next_failure": "عند فشل الهجوم التالي",
    "next_defense": "عند تلقي هجوم ناجح",
}

# ── Effect type configuration ─────────────────────────────────────────────
# Each entry defines: label, icon, fields (with type/required/default/options),
# validation rules, and a summary generator function.

EFFECT_TYPE_CONFIG = {
    EffectType.FIXED_BONUS: {
        "label": "مكافأة ثابتة",
        "icon": "lucide:coins",
        "description": "يمنح نقاطاً ثابتة عند التفعيل",
        "fields": [
            {"key": "amount", "label": "المبلغ (نقاط)", "type": "number", "required": True, "min": 1, "max": 50000},
        ],
        "allowed_scopes": ["self", "target"],
        "allowed_triggers": ["activation", "next_success"],
    },
    EffectType.RATIO_MODIFIER: {
        "label": "معدّل نسبي",
        "icon": "lucide:trending-up",
        "description": "يضاعف مكافأة أو خسارة بنسبة معينة",
        "fields": [
            {"key": "modifier", "label": "المعدّل (مثال: 1.5 = زيادة 50%)", "type": "decimal", "required": True, "min": 0.1, "max": 10.0},
            {"key": "applies_to", "label": "يُطبّق على", "type": "select", "required": True,
             "options": [
                 {"value": "attack_reward", "label": "مكافأة الهجوم"},
                 {"value": "attack_penalty", "label": "خسارة الهجوم"},
             ],
             "default": "attack_reward"},
        ],
        "allowed_scopes": ["self"],
        "allowed_triggers": ["activation", "next_success", "next_failure"],
        "requires_duration_for": ["activation"],
    },
    EffectType.LOSS_REDUCTION: {
        "label": "تقليل الخسارة",
        "icon": "lucide:shield-minus",
        "description": "يقلل خسارة الهجوم الفاشل بنسبة",
        "fields": [
            {"key": "reduction", "label": "نسبة التقليل (0.5 = 50%)", "type": "decimal", "required": True, "min": 0.01, "max": 1.0},
        ],
        "allowed_scopes": ["self"],
        "allowed_triggers": ["activation", "next_failure", "next_defense"],
        "requires_duration_for": ["activation"],
    },
    EffectType.ACTION_PREVENTION: {
        "label": "منع إجراء",
        "icon": "lucide:shield-ban",
        "description": "يمنع الهجمات على اللاعب لمدة محددة",
        "fields": [
            {"key": "action", "label": "الإجراء الممنوع", "type": "select", "required": True,
             "options": [
                 {"value": "attack", "label": "الهجوم"},
             ],
             "default": "attack"},
        ],
        "allowed_scopes": ["self"],
        "allowed_triggers": ["activation"],
        "requires_duration_for": ["activation"],
    },
    EffectType.STATE_CHANGE: {
        "label": "تغيير حالة",
        "icon": "lucide:refresh-cw",
        "description": "يغيّر حالة اللاعب (حماية، إفلاس)",
        "fields": [
            {"key": "state", "label": "نوع الحالة", "type": "select", "required": True,
             "options": [
                 {"value": "protection", "label": "الحماية"},
                 {"value": "bankruptcy", "label": "الإفلاس"},
             ]},
            {"key": "value", "label": "القيمة الجديدة", "type": "select", "required": True,
             "options": [
                 {"value": "full", "label": "حماية كاملة"},
                 {"value": "partial", "label": "حماية جزئية"},
                 {"value": "none", "label": "بدون حماية"},
                 {"value": "clear", "label": "إنهاء الإفلاس"},
             ]},
        ],
        "allowed_scopes": ["self", "target"],
        "allowed_triggers": ["activation"],
    },
    EffectType.NEGATIVE_EFFECT: {
        "label": "تأثير سلبي",
        "icon": "lucide:skull",
        "description": "يطبّق تأثيراً سلبياً على الهدف أو يكسر حمايته الجزئية في الهجوم التالي",
        "fields": [
            {"key": "sub_type", "label": "نوع التأثير السلبي", "type": "select", "required": True,
             "options": [
                 {"value": "deduct_points", "label": "خصم نقاط"},
                 {"value": "deduct_percentage", "label": "خصم نسبة من الرصيد"},
                 {"value": "remove_protection", "label": "إزالة الحماية"},
             ]},
            {"key": "amount", "label": "المبلغ (للخصم الثابت)", "type": "number", "required": False, "min": 1, "max": 50000,
             "show_when": {"sub_type": "deduct_points"}},
            {"key": "percentage", "label": "النسبة المئوية (للخصم النسبي)", "type": "number", "required": False, "min": 1, "max": 100,
             "show_when": {"sub_type": "deduct_percentage"}},
        ],
        "allowed_scopes": ["target"],
        "allowed_triggers": ["activation", "next_success"],
    },
    EffectType.ALLOW_ALIAS_CHANGE: {
        "label": "تغيير اللقب",
        "icon": "lucide:badge",
        "description": "يسمح للاعب بتغيير لقبه مرة واحدة",
        "fields": [],
        "allowed_scopes": ["self"],
        "allowed_triggers": ["activation"],
    },
}

# Types that exist in enum but have no handler yet
UNIMPLEMENTED_TYPES = {
    EffectType.GRANT_ITEM, EffectType.GRANT_BOX, EffectType.MODIFY_DISTRIBUTION,
    EffectType.TIME_LIMITED_EFFECT, EffectType.CYCLE_EFFECT, EffectType.SEASON_EFFECT,
}


def validate_effect(effect_type: str, parameters: dict, target_scope: str, duration_minutes: int | None, trigger_on: str = "activation") -> list[str]:
    """
    Validate effect parameters against the config.
    Returns a list of error messages (empty = valid).
    """
    errors = []

    # Check effect type exists
    try:
        et = EffectType(effect_type)
    except ValueError:
        return [f"نوع التأثير غير معروف: {effect_type}"]

    if et in UNIMPLEMENTED_TYPES:
        return [f"نوع التأثير '{effect_type}' غير مدعوم حالياً"]

    config = EFFECT_TYPE_CONFIG.get(et)
    if not config:
        return [f"لا يوجد تكوين لنوع التأثير: {effect_type}"]

    # Validate target scope
    allowed_scopes = config.get("allowed_scopes", ["self", "target", "all"])
    if target_scope not in allowed_scopes:
        scope_labels = {"self": "الذات", "target": "الهدف", "all": "الجميع"}
        allowed = [scope_labels.get(s, s) for s in allowed_scopes]
        errors.append(f"نطاق '{target_scope}' غير مسموح — المسموح: {', '.join(allowed)}")

    # Validate trigger mode
    allowed_triggers = config.get("allowed_triggers", ["activation"])
    if trigger_on not in allowed_triggers:
        trigger_labels = [TRIGGER_LABELS.get(t, t) for t in allowed_triggers]
        errors.append(f"وضع التشغيل '{TRIGGER_LABELS.get(trigger_on, trigger_on)}' غير مسموح لهذا التأثير — المسموح: {', '.join(trigger_labels)}")

    # Validate duration requirement (only for activation trigger)
    requires_duration_for = config.get("requires_duration_for", [])
    if trigger_on in requires_duration_for and not duration_minutes:
        errors.append("هذا التأثير يتطلب تحديد مدة (دقائق) عند وضع التشغيل الفوري")

    # Validate fields
    for field in config.get("fields", []):
        key = field["key"]
        required = field.get("required", False)
        field_type = field.get("type", "string")

        # Check conditional visibility
        show_when = field.get("show_when")
        if show_when:
            condition_met = all(parameters.get(k) == v for k, v in show_when.items())
            if not condition_met:
                continue  # field not relevant for current sub_type

        value = parameters.get(key)

        if required and (value is None or value == ""):
            errors.append(f"الحقل '{field['label']}' مطلوب")
            continue

        if value is not None and value != "":
            if field_type in ("number", "decimal"):
                try:
                    num_val = float(value)
                    if "min" in field and num_val < field["min"]:
                        errors.append(f"'{field['label']}' يجب أن يكون {field['min']} أو أكثر")
                    if "max" in field and num_val > field["max"]:
                        errors.append(f"'{field['label']}' يجب أن يكون {field['max']} أو أقل")
                except (ValueError, TypeError):
                    errors.append(f"'{field['label']}' يجب أن يكون رقماً")

            if field_type == "select" and "options" in field:
                valid_values = [o["value"] for o in field["options"]]
                if str(value) not in valid_values:
                    errors.append(f"'{field['label']}': القيمة '{value}' غير مسموحة")

    return errors


def generate_effect_summary(effect_type: str, parameters: dict, duration_minutes: int | None = None, target_scope: str = "self", trigger_on: str = "activation") -> str:
    """Generate a human-readable Arabic summary for an effect."""
    try:
        et = EffectType(effect_type)
    except ValueError:
        return f"تأثير غير معروف: {effect_type}"

    duration_text = f" لمدة {duration_minutes} دقيقة" if duration_minutes else ""
    scope_text = " على الهدف" if target_scope == "target" else ""

    # Trigger prefix for pending effects
    trigger_prefix = ""
    if trigger_on == "next_success":
        trigger_prefix = "عند نجاح الهجوم التالي: "
    elif trigger_on == "next_failure":
        trigger_prefix = "عند فشل الهجوم التالي: "
    elif trigger_on == "next_defense":
        trigger_prefix = "عند تلقي هجوم: "

    if et == EffectType.FIXED_BONUS:
        amount = parameters.get("amount", 0)
        return f"{trigger_prefix}يمنح {amount} نقطة{scope_text}{duration_text}"

    if et == EffectType.RATIO_MODIFIER:
        modifier = parameters.get("modifier", 1.0)
        applies_to = parameters.get("applies_to", "attack_reward")
        pct = round((float(modifier) - 1) * 100)
        action = "مكافأة الهجوم" if applies_to == "attack_reward" else "خسارة الهجوم"
        direction = "يزيد" if pct > 0 else "يقلل"
        return f"{trigger_prefix}{direction} {action} بنسبة {abs(pct)}٪{duration_text}"

    if et == EffectType.LOSS_REDUCTION:
        reduction = parameters.get("reduction", 0.5)
        pct = round(float(reduction) * 100)
        return f"{trigger_prefix}يقلل خسارة الهجوم الفاشل بنسبة {pct}٪{duration_text}"

    if et == EffectType.ACTION_PREVENTION:
        action = parameters.get("action", "attack")
        action_label = "الهجمات" if action == "attack" else action
        return f"يمنع {action_label}{scope_text}{duration_text}"

    if et == EffectType.STATE_CHANGE:
        state = parameters.get("state", "")
        value = parameters.get("value", "")
        if state == "protection":
            labels = {"full": "حماية كاملة", "partial": "حماية جزئية", "none": "إزالة الحماية"}
            return f"يمنح {labels.get(value, value)}{scope_text}{duration_text}"
        if state == "bankruptcy" and value == "clear":
            return f"ينهي حالة الإفلاس{scope_text}"
        return f"يغيّر {state} إلى {value}{scope_text}"

    if et == EffectType.NEGATIVE_EFFECT:
        sub_type = parameters.get("sub_type", "")
        if sub_type == "deduct_points":
            amount = parameters.get("amount", 0)
            return f"يخصم {amount} نقطة من الهدف"
        if sub_type == "deduct_percentage":
            pct = parameters.get("percentage", 0)
            return f"يخصم {pct}٪ من رصيد الهدف"
        if sub_type == "remove_protection":
            if trigger_on == "next_success":
                return "عند نجاح الهجوم التالي: يزيل الحماية الجزئية عن الهدف"
            return "يزيل حماية الهدف"
        return f"تأثير سلبي: {sub_type}"

    if et == EffectType.ALLOW_ALIAS_CHANGE:
        return "يسمح بتغيير اللقب مرة واحدة"

    config = EFFECT_TYPE_CONFIG.get(et)
    return config["label"] if config else str(et)


def get_effect_types_schema() -> list[dict]:
    """Return the full schema for all supported effect types (for frontend form generation)."""
    trigger_options = [
        {"value": k, "label": v} for k, v in TRIGGER_LABELS.items()
    ]

    result = []
    for et, config in EFFECT_TYPE_CONFIG.items():
        allowed_trigger_values = config.get("allowed_triggers", ["activation"])
        result.append({
            "value": str(et.value),
            "label": config["label"],
            "icon": config["icon"],
            "description": config["description"],
            "fields": config["fields"],
            "allowed_scopes": config.get("allowed_scopes", ["self", "target", "all"]),
            "allowed_triggers": allowed_trigger_values,
            "trigger_options": [t for t in trigger_options if t["value"] in allowed_trigger_values],
            "requires_duration_for": config.get("requires_duration_for", []),
        })
    return result
