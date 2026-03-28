# Research: Admin Configuration, Item Systems & Game Settings
## Industry Patterns for Competitive Gaming Platforms

**Purpose:** Deep research findings compiled for BRD enhancement — focused on practical patterns for a web-based competitive platform (not AAA game engine complexity).

**Date:** 2026-03-28

---

## 1. Game Item/Effect Systems Architecture

### 1.1 How Leading Games Define Items

Games like Clash Royale, League of Legends, and Brawl Stars all converge on a **data-driven item definition** pattern: items are not coded as individual scripts but defined as structured data records that a generic engine interprets at runtime.

**Clash Royale** defines cards with these metadata fields:
- Name, description, visual assets (icon, animation)
- Rarity tier (Common, Rare, Epic, Legendary, Champion)
- Elixir cost (resource cost to deploy)
- Base stats per level (HP, damage, range, speed)
- Card type (troop, spell, building)
- Arena unlock requirement (eligibility gate)
- Upgrade progression table (stats per level)

**League of Legends** items use a JSON-based definition:
- Item ID, name, description, icon path
- Gold cost (total and recipe components)
- Stats granted (flat and percentage modifiers)
- Passive/active effects (named unique passives)
- Build path (prerequisite items — tree structure)
- Tags for categorization (Damage, Health, Armor, etc.)
- Map availability (item can be restricted to specific game modes)

### 1.2 Complete Item Metadata Model (Industry Composite)

Based on patterns across multiple competitive platforms, the comprehensive metadata model for a game item includes:

```
ITEM DEFINITION
├── Identity
│   ├── id (unique, immutable)
│   ├── internal_name (code reference)
│   ├── display_name (localized)
│   ├── description (localized, supports templates like "{value}% damage boost")
│   ├── icon / visual_assets
│   └── flavor_text (optional lore/personality text)
│
├── Classification
│   ├── rarity (Common, Rare, Epic, Legendary, Mythic)
│   ├── category (offensive, defensive, utility, consumable, cosmetic)
│   ├── item_type (single_use, permanent, timed, passive, activated)
│   └── tags[] (searchable labels for filtering)
│
├── Effects[]
│   ├── effect_type (modify_percentage, add_flat, reduce_loss, block_action,
│   │                grant_status, grant_item, modify_distribution,
│   │                change_alias, negative_effect, timed_effect)
│   ├── target (self, opponent, all_players, random_player, specific_role)
│   ├── trigger (on_purchase, on_use, on_attack, on_defend, on_hit,
│   │            on_bankruptcy, passive, on_cycle_start, on_season_end)
│   ├── modifier_type (additive, multiplicative, override, conditional)
│   ├── value (numeric or reference)
│   ├── duration (instant, cycles:N, hours:N, season, permanent)
│   ├── conditions[] (min_rank, max_rank, has_status, in_cycle, time_window)
│   └── priority (for conflict resolution — higher priority wins)
│
├── Stacking & Limits
│   ├── stackable (boolean)
│   ├── max_stacks (integer)
│   ├── stack_behavior (refresh_duration, extend_duration, increase_effect)
│   ├── cooldown_after_use (time or cycles)
│   ├── max_uses_per_cycle / per_season / total
│   └── conflicts_with[] (item IDs that cannot coexist)
│
├── Acquisition
│   ├── obtainable_via (store, reward, loot_box, distribution, admin_grant)
│   ├── tradeable (boolean)
│   └── destroyable (boolean)
│
├── Lifecycle
│   ├── status (draft, active, deprecated, archived)
│   ├── version (integer, increments on edit)
│   ├── valid_from / valid_until (time-bound availability)
│   ├── competition_scope[] (all, specific competition IDs)
│   ├── season_scope[] (all, specific season IDs)
│   └── created_at / updated_at / created_by
│
└── Audit
    ├── change_history[] (who changed what, when)
    └── usage_statistics (total granted, total used, total active)
```

### 1.3 Effect Interaction Rules

**Stacking Rules (from Unreal GAS, ModiBuff, and card game patterns):**

| Stack Type | Behavior | Example |
|---|---|---|
| **No Stack** | Second application is rejected | One-time-use shield |
| **Refresh** | Timer resets, effect stays same | Protection refresh on re-purchase |
| **Extend** | Duration adds to remaining time | +2 cycles added to existing buff |
| **Intensity Stack** | Effect value increases per stack | Each stack adds +5% defense |
| **Independent** | Each instance runs separately with own timer | Multiple damage-over-time effects |

**Modifier Application Order (industry standard):**
1. Flat additive bonuses applied first (+10, +5, +20 = +35 total flat)
2. Multiplicative modifiers applied second (x1.5, x1.2 = x1.8 combined)
3. Override modifiers applied last (replaces computed value)
4. Caps/floors enforced at the end (minimum 0, maximum per setting)

**Conflict Resolution:**
- Each effect has a `priority` field (integer, higher wins)
- When two effects conflict (e.g., "immune to attacks" vs "guaranteed hit"), the higher priority wins
- Same-priority conflicts: defensive effect wins (platform-configurable default)
- Admin can define explicit conflict pairs via a conflict matrix

---

## 2. Data-Driven Design: Separating Logic from Data

### 2.1 The Core Pattern

The universally adopted pattern in modern game development:

```
CODE (Engine)              DATA (Configuration)
─────────────             ──────────────────
Effect processor      ←   Effect definitions (JSON/DB)
Store engine          ←   Store catalog entries (JSON/DB)
Quiz engine           ←   Question bank entries (DB)
Scoring engine        ←   Scoring rules (DB settings)
Distribution engine   ←   Distribution schedules (DB)
```

**The engine interprets data, never hardcodes behavior per item.** This is exactly what the War of Names BRD already mandates ("لا يتم بناء منطق كل عنصر كسكربت خاص منفصل").

### 2.2 Configuration Hierarchy

From game industry patterns (Unity ScriptableObjects, Habr's technical game design article):

```
Level 1: PLATFORM DEFAULTS
  └── Level 2: COMPETITION OVERRIDES
       └── Level 3: SEASON OVERRIDES
            └── Level 4: CYCLE OVERRIDES
                 └── Level 5: EVENT/PROMOTION OVERRIDES
```

Each level inherits from its parent and can override specific fields. This allows:
- Platform-wide defaults (base scoring, default store prices)
- Competition-specific tuning (this competition has 2x attack points)
- Seasonal themes (winter season has different item availability)
- Cycle-level tweaks (this cycle has flash sales)
- Event-level overrides (special event: all attacks cost double)

### 2.3 Config Storage Patterns

**For a web platform (PostgreSQL + JSON), the recommended hybrid approach:**

| Data Type | Storage | Why |
|---|---|---|
| Item definitions | DB table with JSON `effects` column | Queryable + flexible |
| Store catalog | DB table (item_id, price, stock, conditions) | Transactional integrity |
| Game rules/settings | Key-value table with scope (competition_id, season_id) | Hierarchical override |
| Question bank | Normalized DB tables | Complex queries, tags, randomization |
| Distribution schedules | DB table with cron-like fields | Scheduler needs structured data |
| UI display configs | JSON column or separate table | Rarely queried, frequently read |

### 2.4 Google Sheets to JSON Pipeline (from Habr article)

A proven pattern used by strategy games:
1. Game designers edit items/balance in Google Sheets (familiar, collaborative)
2. Each row generates a JSON object via formula
3. Validation script checks syntax and constraints
4. Merge script produces importable JSON file
5. Admin panel ingests the JSON, creating/updating DB records

**For War of Names:** Consider supporting CSV/Excel import for bulk item/question creation, with the admin panel as the primary CRUD interface and Excel as bulk import.

---

## 3. Admin Panel Best Practices for Game Management

### 3.1 Essential Admin Panel Sections

Based on Melior Games research and industry practice:

| Section | Key Capabilities |
|---|---|
| **Dashboard** | Active players, revenue metrics, current cycle status, alerts |
| **Player Management** | Search, view profile/history, ban/mute, manual adjustments |
| **Competition Management** | Create, configure, clone competitions; manage memberships |
| **Season/Cycle Control** | Create/schedule seasons and cycles; manual start/stop |
| **Item Catalog** | CRUD items with full metadata; preview effects; clone items |
| **Store Management** | Configure catalog entries, pricing, stock, availability windows |
| **Question Bank** | CRUD questions; bulk import; tag management; pool configuration |
| **Quiz Sessions** | Create/schedule sessions; assign question sources; view results |
| **Distribution Engine** | Schedule point/item distributions; define rules and targets |
| **Scoring Rules** | Configure point values for all game events per scope |
| **Notification Center** | Send announcements; configure auto-notifications |
| **Audit Logs** | Searchable log of all admin and system actions |
| **Settings** | Game rules, feature flags, system configuration |

### 3.2 Bulk Operations

From React-admin patterns and game plugin ecosystems:

- **Bulk Create:** CSV/Excel upload with column mapping and validation preview
- **Bulk Edit:** Select multiple items, change shared fields (e.g., set all Common items to active)
- **Bulk Status Change:** Activate/deactivate/archive multiple items at once
- **Clone:** Duplicate an existing item/question/session as a starting point for a new one
- **Template System:** Save item configurations as templates for rapid creation

### 3.3 Version Control for Game Configs

From workflow versioning platforms (Persona, Anvil, NextMatter):

**Draft-Review-Publish Workflow:**
```
DRAFT → REVIEW → PUBLISHED → (new edit creates new DRAFT)
                                    ↓
                              ARCHIVED (old version)
```

**Key fields per config version:**
- `version_number` (auto-increment)
- `status` (draft, published, archived)
- `published_at` / `published_by`
- `change_description` (admin's note explaining what changed)
- `diff_from_previous` (computed: what fields changed)
- `rollback_target` (which version this was rolled back from, if applicable)

**Practical implementation for War of Names:**
- Every item/setting edit creates a new version row, not an in-place update
- Only one version can be `published` at a time per item
- Admin can "revert to version X" which creates a NEW version with that version's data
- Full audit trail: who changed what, when, why

### 3.4 Preview/Test Mode

From feature flag platforms (LaunchDarkly, GrowthBook):

- **Admin Preview:** Admin can see how an item/store change looks before publishing
- **Sandbox Competition:** A test competition where admins can try items/rules without affecting real data
- **Feature Flags:** Toggle experimental features for specific competitions
- **Simulation Mode:** "What if" calculator for effect stacking before releasing an item

### 3.5 Balance Management (Buff/Nerf Pattern)

How platforms handle item balance changes without breaking existing items:

1. **Never mutate active items in-place** — create a new version
2. **Grandfathering:** Existing holders keep old item version until it expires; new acquisitions get new version
3. **Global Rebalance:** Update item definition; all instances update (simpler, used when items are consumables, not permanent)
4. **Deprecate + Replace:** Old item goes to `deprecated` status; new item is introduced; old item still works but is no longer obtainable
5. **Announce First:** Games typically announce balance changes in advance (patch notes / notifications)

**Recommendation for War of Names:** Since most items are consumables with temporary effects, use the **Global Rebalance** approach: editing a published item creates a new version that applies to all future uses. Already-active effects from old version continue until they expire naturally.

---

## 4. Store/Marketplace Configuration

### 4.1 Store Entry (Catalog Listing) Schema

```
STORE CATALOG ENTRY
├── catalog_entry_id
├── item_id (→ item definition)
├── display_order (sort position in store)
│
├── Pricing
│   ├── price (primary currency cost)
│   ├── price_currency (points, premium_currency, etc.)
│   ├── secondary_costs[] (additional requirements: items, achievements)
│   ├── original_price (for showing "was X, now Y" on sales)
│   └── discount_percentage (computed or manual)
│
├── Stock Control
│   ├── stock_type (unlimited, limited_total, limited_per_player)
│   ├── total_stock (null = unlimited)
│   ├── remaining_stock
│   ├── per_player_limit (max purchases per player per period)
│   └── per_player_period (per_cycle, per_season, lifetime)
│
├── Availability Window
│   ├── available_from (datetime, null = immediate)
│   ├── available_until (datetime, null = no expiry)
│   ├── recurring_schedule (cron-like: "weekends only", "every cycle start")
│   └── is_flash_sale (boolean — enables countdown timer UI)
│
├── Eligibility Rules
│   ├── min_rank (player must be at least rank X)
│   ├── max_rank (player must be at most rank X — for catch-up items)
│   ├── required_membership_status (active, not_bankrupt)
│   ├── required_items[] (must own these items first — prerequisites)
│   ├── excluded_items[] (cannot own these — mutual exclusion)
│   ├── competition_scope[] (specific competitions or all)
│   └── custom_conditions (JSON: extensible for future rules)
│
├── Purchase Behavior
│   ├── cooldown_between_purchases (seconds/cycles between buys)
│   ├── auto_activate (item activates immediately on purchase)
│   ├── confirmation_required (show "are you sure?" dialog)
│   └── gift_enabled (can buy for another player)
│
├── Display
│   ├── featured (boolean — appears in featured section)
│   ├── badge_text ("NEW", "HOT", "LIMITED", custom)
│   ├── category_placement (which store tab/section)
│   └── custom_styling (rarity-based CSS class)
│
└── Lifecycle
    ├── status (draft, active, paused, ended, archived)
    ├── version
    └── created_at / updated_at / created_by
```

### 4.2 Pricing Patterns

| Pattern | Implementation | Use Case |
|---|---|---|
| **Fixed Price** | Static price per item | Standard store items |
| **Tiered Pricing** | Price changes after X purchases (global or per-player) | Scarcity simulation |
| **Bundle** | Multiple items at combined discount (max 30% industry norm) | Value packs |
| **Dynamic Discount** | If player already owns part of bundle, reduce price | Smart bundles |
| **Flash Sale** | Time-limited discount with countdown timer | Urgency creation |
| **Seasonal Sale** | Discount during specific season/cycle | Thematic events |
| **Loss Leader** | Below-cost item to drive engagement | Re-engagement |

### 4.3 Cooldown Patterns

From Steam, Splinterlands, and mobile game patterns:

- **Purchase Cooldown:** Minimum time between purchases of same item (prevents hoarding)
- **Category Cooldown:** "Only one offensive item per cycle" — cooldown applies to a category
- **Global Cooldown:** After any purchase, N-second delay before next (anti-automation)
- **Discount Cooldown:** Minimum 30 days between discount events for same item (Steam pattern)

---

## 5. Effect System Design Patterns

### 5.1 Effect Type Taxonomy

Based on Unreal GAS, ModiBuff, and card game systems:

```
EFFECT TYPES
├── Stat Modifiers
│   ├── add_flat (e.g., +50 points)
│   ├── add_percentage (e.g., +20% attack bonus)
│   ├── multiply (e.g., x1.5 score multiplier)
│   ├── override (e.g., set defense to 100)
│   ├── reduce_flat (e.g., -30 points loss)
│   └── reduce_percentage (e.g., -25% loss reduction)
│
├── State Changes
│   ├── grant_status (e.g., "protected", "invisible", "boosted")
│   ├── remove_status (e.g., remove "vulnerable")
│   ├── block_action (e.g., cannot be attacked, cannot attack)
│   └── enable_action (e.g., unlock alias change)
│
├── Resource Grants
│   ├── grant_points (fixed or percentage of pool)
│   ├── grant_item (give another item)
│   ├── grant_loot_box (randomized reward)
│   └── modify_distribution (change upcoming distribution amount)
│
└── Meta Effects
    ├── reflect (return a portion of incoming effect to source)
    ├── absorb (convert incoming negative to positive, up to threshold)
    ├── transfer (move points/status to another player)
    └── reveal (expose information — e.g., hint about an alias)
```

### 5.2 Trigger System

```
TRIGGER POINTS
├── Immediate
│   ├── on_purchase    — when item is bought
│   ├── on_use         — when player manually activates
│   └── on_grant       — when item is given via distribution/reward
│
├── Combat-Related
│   ├── on_attack_initiated  — when this player starts an attack
│   ├── on_attack_success    — when attack correctly identifies target
│   ├── on_attack_fail       — when attack misidentifies target
│   ├── on_defend_success    — when player is attacked but attacker fails
│   ├── on_defend_fail       — when player is attacked and attacker succeeds
│   └── on_attack_received   — any attack targeting this player
│
├── Lifecycle
│   ├── on_cycle_start       — beginning of each cycle
│   ├── on_cycle_end         — end of each cycle
│   ├── on_season_start      — beginning of season
│   ├── on_season_end        — end of season
│   └── on_quiz_complete     — after finishing a quiz session
│
├── Threshold
│   ├── on_points_above(N)   — triggered when points exceed threshold
│   ├── on_points_below(N)   — triggered when points drop below threshold
│   ├── on_rank_change       — when player's rank changes
│   └── on_bankruptcy        — when player enters bankruptcy state
│
└── Passive
    └── always_active         — effect applies continuously while item is held
```

### 5.3 Target Resolution

```
TARGET TYPES
├── self              — the item holder
├── attacker          — the player who attacked (in combat context)
├── defender          — the player being attacked (in combat context)
├── specific_player   — admin-designated target
├── random_player     — randomly selected from eligible pool
├── all_players       — everyone in competition
├── top_N_players     — top N in leaderboard
├── bottom_N_players  — bottom N in leaderboard
├── same_rank_tier    — players in same rank bracket
└── custom_filter     — JSON condition (extensible)
```

### 5.4 Duration Model

```
DURATION TYPES
├── instant           — apply once, no persistence
├── timed             — expires after N hours/minutes
├── cycle_bound       — expires at end of current/N cycles
├── season_bound      — expires at end of current season
├── permanent         — never expires (until manually removed)
├── use_count         — expires after N uses (e.g., shield blocks 3 attacks)
└── conditional       — expires when condition is met (e.g., until next attack)
```

### 5.5 Stacking Policy (Recommended for War of Names)

Given the platform's scope (competitive but not MMO-complex):

**Recommended approach — "Category Additive, Cross-Category Multiplicative":**

1. Effects within the same category (e.g., two attack bonuses) stack **additively**: +10% + +15% = +25%
2. Effects across categories (e.g., attack bonus and score multiplier) apply **multiplicatively**: 1.25 x 1.5 = 1.875
3. Override effects always take precedence over additive/multiplicative
4. Hard caps per attribute prevent runaway values (configurable in settings)

This prevents degenerate combos while keeping the system intuitive for players.

---

## 6. Question/Quiz Configuration

### 6.1 Question Metadata (Industry Standard from Moodle, FlexiQuiz, ProProfs)

```
QUESTION DEFINITION
├── Identity
│   ├── id
│   ├── question_text (supports rich text / HTML)
│   ├── question_type (multiple_choice, true_false, text_input)
│   └── language (for multi-language support)
│
├── Answer Structure
│   ├── options[] (for multiple choice)
│   │   ├── option_text
│   │   ├── is_correct (boolean)
│   │   ├── partial_credit (0.0 to 1.0 — fraction of full score)
│   │   └── feedback_text (shown after answer)
│   ├── correct_answer (for text input)
│   └── answer_explanation (shown after session ends)
│
├── Classification
│   ├── category (hierarchical: parent → child)
│   ├── tags[] (multiple free-form tags)
│   ├── difficulty (1-5 scale, or numeric 1-999 for adaptive)
│   ├── points (reward for correct answer)
│   ├── negative_points (penalty for wrong answer, 0 = no penalty)
│   └── group / collection (named set for organized management)
│
├── Media
│   ├── attachments[]
│   │   ├── type (image, audio, video, link)
│   │   ├── url (server path or external URL)
│   │   ├── display_mode (inline, modal, background)
│   │   └── alt_text
│   └── time_to_answer_override (some media questions need more time)
│
├── Scope & Targeting
│   ├── competition_scope[] (all or specific)
│   ├── season_scope[] (all or specific)
│   └── target_audience (all, specific_rank_range)
│
├── Lifecycle
│   ├── status (draft, active, archived, retired)
│   ├── usage_count (how many times used in sessions)
│   ├── success_rate (auto-calculated: correct / total attempts)
│   ├── created_at / updated_at / created_by
│   └── last_used_at
│
└── Adaptive Metadata (future)
    ├── irt_difficulty (Item Response Theory difficulty parameter)
    ├── irt_discrimination (how well question differentiates ability levels)
    └── estimated_time_seconds (expected answer time)
```

### 6.2 Question Pool & Randomization Patterns

From Moodle and quiz platform research:

**Pool Selection Strategies:**
| Strategy | Description | Use Case |
|---|---|---|
| **Fixed Order** | All players get same questions in same order | Fair timed competitions |
| **Fixed Set, Random Order** | Same questions, shuffled | Slight variation |
| **Random from Pool** | N questions drawn from larger pool | Replay value, reduces sharing |
| **Stratified Random** | N easy + M medium + K hard from respective pools | Balanced difficulty |
| **Weighted Random** | Questions weighted by inverse usage (less-used = higher chance) | Freshness |
| **Adaptive** | Next question difficulty based on previous answers | Personalized challenge |

**Recommended for War of Names MVP:** Stratified Random — admin defines how many questions per difficulty level, system draws from matching pools. This is simple to implement, fair, and prevents difficulty spikes.

### 6.3 Session Configuration

```
QUIZ SESSION
├── Identity
│   ├── session_id
│   ├── title
│   ├── description
│   └── competition_id / season_id / cycle_id
│
├── Timing
│   ├── session_type (live, async_window)
│   ├── start_at (scheduled start)
│   ├── end_at (hard deadline)
│   ├── duration_per_question (seconds, or null for session-level timer)
│   ├── total_session_duration (minutes)
│   └── grace_period (seconds after end for submission)
│
├── Question Source
│   ├── source_type (manual_selection, pool_random, stratified_random)
│   ├── question_ids[] (for manual selection)
│   ├── pool_filters (for random: category, difficulty range, tags)
│   ├── question_count (total questions to draw)
│   ├── difficulty_distribution {easy: N, medium: M, hard: K}
│   └── randomize_option_order (boolean — shuffle answer choices)
│
├── Scoring
│   ├── points_per_correct (or per-question override)
│   ├── penalty_per_wrong (0 = no penalty)
│   ├── bonus_for_speed (boolean — faster = more points)
│   ├── speed_bonus_formula (e.g., "base * (time_remaining / total_time)")
│   └── all_correct_bonus (bonus points if 100% correct)
│
├── Rules
│   ├── max_attempts (usually 1)
│   ├── show_correct_after (immediately, after_session, never)
│   ├── allow_skip (can player skip and return)
│   ├── shuffle_questions (boolean)
│   └── eligible_participants (all, specific list, rank range)
│
└── Lifecycle
    ├── status (draft, scheduled, active, completed, cancelled)
    ├── created_by / created_at
    └── results_published_at
```

### 6.4 Adaptive Difficulty (Future Enhancement)

From Moodle's Adaptive Quiz plugin and QuizCat research:

- Questions tagged with numeric difficulty (1-999)
- System estimates player ability based on recent performance
- Next question selected to match estimated ability level
- After each answer, ability estimate is updated (Item Response Theory)
- Converges on player's true ability level in 15-20 questions

**Implementation cost:** High. **Recommendation:** Tag questions with difficulty (1-5) in MVP for future adaptive support, but use stratified random selection initially.

---

## 7. Practical Recommendations for War of Names

### 7.1 What to Implement Now (MVP)

1. **Item definitions as data:** JSON `effects` column in items table, interpreted by a generic effect processor
2. **Store catalog as separate table:** Pricing, stock, availability decoupled from item definitions
3. **Draft/Published lifecycle:** For items and store entries (no versioning history in MVP, just draft → published)
4. **Hierarchical settings:** Platform → Competition → Season key-value settings with override chain
5. **Question bank with tags:** Category + difficulty + tags, support for manual and stratified random pool selection
6. **Effect triggers:** Start with on_purchase, on_use, on_attack_success, on_defend_success, passive, on_cycle_start
7. **Simple stacking:** Additive within category, non-stackable across same item type
8. **Audit trail:** Every config change logged with admin_id, timestamp, old_value, new_value

### 7.2 What to Design For (Architecture Ready, Build Later)

1. **Full version history** for items/settings (keep the data model flexible for it)
2. **Adaptive quiz difficulty** (tag questions with numeric difficulty from day one)
3. **Bundle system** for store (combo purchases at discount)
4. **Effect priority/conflict matrix** (simple priority integer is enough for now)
5. **Feature flags** per competition (enable/disable experimental features)
6. **Excel/CSV bulk import** for questions and items
7. **Simulation mode** for testing effect interactions before publishing

### 7.3 What to Avoid

1. **Per-item scripts:** Never build a custom handler per item. All items use the same effect engine.
2. **Client-side effect calculation:** All effect resolution happens server-side. Frontend only displays results.
3. **Unbounded stacking:** Always enforce max_stacks and hard caps on computed values.
4. **In-place mutation:** Config changes should create new versions, not overwrite existing data (at minimum, log the old value before changing).
5. **Over-engineering rarity:** Keep rarity as a simple enum with associated display rules. Don't tie game mechanics to rarity — tie them to effects.

---

## Sources

### Game Item/Effect Systems
- [Clash Royale Cards - Fandom Wiki](https://clashroyale.fandom.com/wiki/Cards)
- [Clash Royale API Data - GitHub](https://github.com/RoyaleAPI/cr-api-data)
- [League of Legends Items JSON - GitHub](https://github.com/ngryman/lol-items/blob/master/items.json)
- [ModiBuff: Buff/Debuff Library - GitHub](https://github.com/Chillu1/ModiBuff)
- [GAS Documentation - GitHub](https://github.com/tranek/GASDocumentation)

### Data-Driven Design
- [Data-Oriented Design - Games from Within](https://gamesfromwithin.com/data-oriented-design)
- [Data-Driven Design in Game Development - UMICH](https://web.eecs.umich.edu/~soar/Classes/494/talks/Schumaker.pdf)
- [Technical Game Design: Configs and Balance - Habr](https://habr.com/en/articles/737534/)
- [Separate Game Data with ScriptableObjects - Unity](https://unity.com/how-to/separate-game-data-logic-scriptable-objects)
- [Data-Driven Design in Software - DEV.to](https://dev.to/methodox/data-driven-design-leveraging-lessons-from-game-development-in-everyday-software-5512)

### Admin Panel & Live Ops
- [Creating a Game Admin Panel - Melior Games](https://meliorgames.com/game-development/creating-a-casual-game-admin-panel-what-it-should-include/)
- [Essential Guide to Live Ops - iLogos](https://ilogos.biz/the-essential-guide-to-live-ops/)
- [React-admin CRUD Pages](https://marmelab.com/react-admin/CRUD.html)
- [Version Control in Game Development - Gridly](https://www.gridly.com/blog/version-control-in-game-development/)

### Store/Marketplace
- [Dynamic Tier Pricing in Games - Zigpoll](https://www.zigpoll.com/content/how-can-we-design-a-dynamic-tier-pricing-system-that-adjusts-promotional-discounts-based-on-realtime-player-engagement-and-purchase-patterns-within-an-ingame-store)
- [Steam Pricing Documentation](https://partner.steamgames.com/doc/store/pricing)
- [Steam Discounting Documentation](https://partner.steamgames.com/doc/marketing/discounts)
- [Custom Price Tiers - Epic Games](https://dev.epicgames.com/docs/epic-games-store/store-presence/custom-price-tiers)

### Effect Systems
- [Gameplay Effects - Unreal Engine 5.7 Docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/gameplay-effects-for-the-gameplay-ability-system-in-unreal-engine)
- [Gameplay Effect Components Explained - Quod Soler](https://www.quodsoler.com/blog/how-to-use-gameplay-effect-components-in-unreal-engine-5)
- [Flexible Buff/Debuff System - Game Dev Stack Exchange](https://gamedev-stackexchange-com.translate.goog/questions/29982/whats-a-way-to-implement-a-flexible-buff-debuff-system)
- [Additive vs Multiplicative Bonuses - Paradox Forums](https://forum.paradoxplaza.com/forum/threads/additive-bonuses-vs-multiplicative-bonuses.1144836/)

### Gacha & Item Management
- [Gacha Systems In-Depth - Machinations.io](https://machinations.io/articles/an-in-depth-look-at-gacha-boxes)
- [Gacha Game Design Core Elements - Alchemy of Game Design](https://oozbey.blog/2023/03/28/gacha-game-design-the-core-elements-and-systems/)
- [Gacha Games Explained - Epic Games Store](https://store.epicgames.com/en-US/news/gacha-games-explained-banners-pulls-pity-systems-and-more)
- [gachapy Python Engine - GitHub](https://github.com/jakejack13/gachapy)

### Quiz/Question Systems
- [Question Database Structure - Moodle Docs](https://docs.moodle.org/dev/Question_database_structure)
- [Quiz Database Structure - Moodle Docs](https://docs.moodle.org/dev/Quiz_database_structure)
- [Adaptive Quiz Plugin - Moodle](https://moodle.org/plugins/mod_adaptivequiz)
- [What is a Question Bank - SpeedExam](https://www.speedexam.net/blog/what-is-a-question-bank/)
- [Adaptive Quiz Difficulty Scaling - QuizCat](https://www.quizcat.ai/blog/what-is-adaptive-quiz-difficulty-scaling)
- [Quiz Database Design - Tutorials24x7](https://www.tutorials24x7.com/mysql/guide-to-design-database-for-quiz-in-mysql)

### Feature Flags & Config Management
- [Feature Flags Essential Guide - Apwide](https://www.apwide.com/what-are-feature-flags-guide/)
- [A/B Testing with Feature Flags - CloudBees](https://www.cloudbees.com/blog/a-b-testing-with-feature-flags)
- [LaunchDarkly Feature Management](https://launchdarkly.com/)
- [Workflow Version History - GoHighLevel](https://help.gohighlevel.com/support/solutions/articles/155000006656-workflows-version-history-restore)
