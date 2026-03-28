# War of Names — Compliance & Regulations BRD V1.0

> **Document Type:** Business Requirements Document — Legal & Regulatory Compliance
> **Platform:** War of Names (حرب الأسماء)
> **Jurisdiction:** Kingdom of Saudi Arabia
> **Version:** 1.0
> **Last Updated:** 2026-03-27

---

## 1. Purpose

This document tracks all legal, regulatory, and compliance requirements for the War of Names platform. It serves as the authoritative reference for:

- Saudi Arabia regulatory obligations and how the platform satisfies them
- Data processing inventory and legal basis for each data category
- AI and data usage policies
- Multi-admin governance model and liability boundaries
- Infrastructure and data residency considerations
- Third-party service disclosures
- IP ban system governance
- Future monetization compliance guardrails
- Backup and data export requirements

This BRD must be consulted before any feature launch, data flow change, or infrastructure decision. It is a living document that must be updated as regulations evolve.

---

## 2. Saudi Arabia Regulatory Framework

### 2.1 SDAIA — Personal Data Protection Law (PDPL)

**Governing Authority:** Saudi Data & AI Authority (الهيئة السعودية للبيانات والذكاء الاصطناعي — سدايا)
**Legislation:** Personal Data Protection Law, Royal Decree M/19, dated 09/02/1443H
**Effective:** September 2023, with a transitional compliance period

#### 2.1.1 Data We Collect

The platform collects the following categories of personal data:

| Category | Examples | Collection Method |
|----------|----------|-------------------|
| Identity data | Username, real name | User-provided at registration |
| Authentication data | Password (stored as bcrypt hash) | User-provided at registration |
| Network data | IP address, browser type, OS, device identifier | Automatically collected |
| Game activity data | Attack history, quiz answers, scores, purchases, rankings | Generated through gameplay |
| Session data | Login timestamps, session tokens, page visits | Automatically collected |
| Preference data | Dark/light mode, locale | User-set, stored in localStorage |
| Alias data | Competition aliases (nicknames) | User-provided when joining competition |

**Note:** The platform does NOT currently collect email addresses, phone numbers, or government-issued IDs. The Privacy Policy mentions email collection, but the Account model currently stores only: `username`, `real_name`, `password_hash`, `status`, `is_admin`, `locale`, `last_login_at`. If email is added in the future, this document and the data inventory must be updated.

#### 2.1.2 Legal Basis for Processing

| Processing Activity | Legal Basis (PDPL) | Article |
|---------------------|-------------------|---------|
| Account creation & authentication | Contractual necessity — required to provide the service | Art. 5(1) |
| Gameplay mechanics (attacks, scoring, store) | Contractual necessity — core service delivery | Art. 5(1) |
| IP address logging | Legitimate interest — security, anti-fraud, fair play enforcement | Art. 5(3) |
| Session & activity tracking | Legitimate interest — platform security and integrity | Art. 5(3) |
| Audit trail logging | Legal obligation — record-keeping for dispute resolution | Art. 5(4) |
| Anonymized analytics | Legitimate interest — service improvement | Art. 5(3) |

#### 2.1.3 User Rights Under PDPL

The following rights are guaranteed by PDPL and must be enforceable through the platform:

| Right | PDPL Article | Platform Implementation Status |
|-------|-------------|-------------------------------|
| **Right of Access** — obtain a copy of personal data | Art. 4 | NOT IMPLEMENTED — no self-service data export endpoint exists |
| **Right of Correction** — correct inaccurate data | Art. 4 | PARTIAL — users can update `real_name` and password via `/api/auth/me` PATCH |
| **Right of Deletion** — request deletion of personal data | Art. 4 | NOT IMPLEMENTED — no account self-deletion; admin can suspend/disable |
| **Right of Withdrawal** — withdraw consent at any time | Art. 6 | NOT IMPLEMENTED — no consent withdrawal mechanism |
| **Right of Objection** — object to certain processing | Art. 4 | NOT IMPLEMENTED — no formal objection process |
| **Right of Portability** — receive data in machine-readable format | Art. 4 | NOT IMPLEMENTED — no data export in structured format |

**Action Required:** Before public launch, implement at minimum:
1. Account self-deletion (or formal deletion request flow)
2. User data export endpoint (machine-readable JSON/CSV)
3. A formal process for handling rights requests within 30 days (as promised in Privacy Policy)

#### 2.1.4 Data Retention

| Data Category | Retention Period | Deletion Trigger |
|---------------|-----------------|------------------|
| Active account data | While account is active | Account deletion request |
| Personally identifiable data after deletion | 30 days post-deletion (as stated in Privacy Policy) | Automatic purge job |
| Audit/transaction logs after deletion | Up to 1 year (as stated in Privacy Policy) | Automatic purge job |
| Anonymized/aggregated statistics | Indefinite | N/A — non-identifiable |

**Action Required:** Implement automated data purge jobs that respect the retention periods promised in the Privacy Policy.

#### 2.1.5 Cross-Border Data Transfer

The platform may use VPS servers located outside the Kingdom of Saudi Arabia (e.g., OVH servers in Europe) for cost and performance reasons.

**PDPL Article 29 Requirements:**
- Transfer is only permitted when the receiving country provides an adequate level of protection, OR
- Adequate safeguards are in place (contractual clauses, binding corporate rules)
- Transfer must be limited to the minimum data necessary

**Current Approach:**
- VPS hosting on OVH (France/Europe) — must verify SDAIA adequacy decisions for the hosting country
- If no adequacy decision exists, implement Standard Contractual Clauses (SCCs) with the hosting provider
- Document the transfer in the Data Processing Agreement (DPA)

**Action Required:**
1. Execute DPA with OVH or hosting provider
2. Document the cross-border transfer mechanism (adequacy or SCCs)
3. Disclose server location region in Privacy Policy (currently not disclosed)

#### 2.1.6 Breach Notification

Per PDPL requirements:
- Data breaches must be reported to SDAIA within **72 hours** of discovery
- Affected users must be notified without undue delay
- The notification must include: nature of breach, data affected, remedial measures taken
- The Privacy Policy already states this commitment (Section 04 — Storage & Protection)

**Penalties:** Up to **SAR 5,000,000** per violation of PDPL provisions.

**Action Required:** Establish an internal breach response procedure document with:
1. Detection and assessment protocol
2. 72-hour reporting checklist for SDAIA
3. User notification template
4. Remediation workflow

### 2.2 CITC — Digital Platform Regulations

**Governing Authority:** Communications, Information Technology & Technology Commission (هيئة الاتصالات وتقنية المعلومات)

**Applicable Regulations:**
- Digital platform registration requirements (if applicable based on user count thresholds)
- Content hosting obligations
- Compliance with content takedown requests from authorized parties

**Current Assessment:** As a closed-competition gaming platform (not a public social media platform), War of Names likely does not require CITC platform registration. However, this must be reassessed if the platform grows to significant public user counts or adds user-generated content features beyond aliases.

### 2.3 Saudi E-Commerce Law

**Legislation:** E-Commerce Law (نظام التجارة الإلكترونية), Royal Decree M/126, 2019

**Applicability:** Currently limited — the platform does not process real-money transactions. Becomes fully applicable if real-money purchases are introduced.

**Key Provisions:**
- **7-day withdrawal right:** Consumers can return digital purchases within 7 days. However, an exemption applies for digital content that has been accessed/used — once a virtual item is used in-game, the withdrawal right is waived.
- **Disclosure requirements:** Clear pricing, provider identity, and contact information must be visible before purchase.
- **Electronic contract formation:** Terms must be accepted before transaction.

**Current Status:** The in-game store uses virtual points (no real money). This section becomes critical if the monetization features described in Section 9 are activated.

### 2.4 Anti-Cybercrime Law

**Legislation:** Anti-Cybercrime Law (نظام مكافحة جرائم المعلوماتية), Royal Decree M/17, 2007

**Relevant Provisions:**
- **Art. 3:** Unauthorized access to systems — platform must secure endpoints
- **Art. 5:** Defamation and slander via electronic means — content moderation rules apply
- **Art. 6:** Content harmful to public order, religious values, morals — content filtering required

**Platform Compliance:**
- Terms of Use Section 05 (Content Rules) explicitly prohibits: offensive language, religious insults, national symbol disrespect, personal data leaks, pornographic/violent content, harmful links, and all violations of the Anti-Cybercrime Law
- Admin has content moderation capabilities (suspend/remove players, audit trail)
- The Terms of Use reference the Anti-Cybercrime Law directly

### 2.5 VAT — ZATCA

**Governing Authority:** Zakat, Tax and Customs Authority (هيئة الزكاة والضريبة والجمارك)

**Standard Rate:** 15% VAT on digital services and goods

**Current Status:** Not applicable — no real-money transactions exist.

**Future Applicability:**
- If the platform introduces paid subscriptions, real-money store items, or premium features, 15% VAT must be collected and remitted
- VAT registration threshold and filing obligations per ZATCA rules
- Must be factored into pricing display (inclusive or exclusive, with clear disclosure)

---

## 3. Data Processing Inventory

### 3.1 Complete Data Map

| Data Element | Purpose | Legal Basis | Retention | Who Has Access | Storage |
|-------------|---------|-------------|-----------|---------------|---------|
| `username` | Account identification, login | Contractual necessity | While account active; 30 days post-deletion | User, Admin, System | PostgreSQL `accounts` table |
| `real_name` | Identity within game mechanics (attack system reveals real names) | Contractual necessity | While account active; 30 days post-deletion | User, Admin (via admin panel), revealed to attackers per game rules | PostgreSQL `accounts` table |
| `password_hash` | Authentication | Contractual necessity | While account active; deleted with account | System only (bcrypt, not reversible) | PostgreSQL `accounts` table |
| `ip_address` | Security, anti-fraud, IP ban enforcement | Legitimate interest | Not currently collected in DB — future: per session log retention | Admin (future), System | Not yet stored explicitly |
| `last_login_at` | Security monitoring | Legitimate interest | While account active | Admin, System | PostgreSQL `accounts` table |
| `locale` | UI language preference | Contractual necessity | While account active | System | PostgreSQL `accounts` table |
| `alias` (nickname) | Core gameplay — anonymous competition identity | Contractual necessity | Tied to membership; while competition active | All competition participants (by design) | PostgreSQL `alias_records` table |
| `attack_history` | Game mechanics, audit trail, fair play enforcement | Contractual necessity + Legitimate interest | While competition active; audit logs up to 1 year | Attacker, Defender, Admin | PostgreSQL `attack_attempts` table |
| `quiz_answers` | Scoring, game mechanics | Contractual necessity | While competition active | Admin, System | PostgreSQL `answer_submissions` table |
| `point_balance` | Scoring, leaderboard, store purchases | Contractual necessity | While competition active | User (own), All (via alias on leaderboard), Admin | PostgreSQL `ledger_entries` table |
| `owned_items` | Inventory management, game effects | Contractual necessity | While competition active | User (own), Admin | PostgreSQL `owned_items` table |
| `notifications` | Communication, game events | Contractual necessity | While account active | User (own), Admin (broadcast) | PostgreSQL `notifications` table |
| `audit_logs` | System integrity, dispute resolution | Legal obligation + Legitimate interest | Up to 1 year post-event | Admin, System | PostgreSQL `audit_logs` table |
| `session_tokens` | Authentication continuity | Contractual necessity | JWT expiry (configured) | System | Client-side (localStorage) |
| `theme_preference` | UI display | User preference | Indefinite (client-side) | Client only | Client localStorage |
| `device_info` | Session management, security | Legitimate interest | Not currently collected | N/A | Not implemented |
| `browser/OS info` | Mentioned in Privacy Policy | Legitimate interest | Not currently collected in DB | N/A | Not explicitly stored |

### 3.2 Data Not Yet Collected But Mentioned in Legal Pages

The following data types are mentioned in the Privacy Policy but are NOT currently collected or stored:

| Data Element | Mentioned In | Current Status |
|-------------|-------------|---------------|
| Email address (البريد الإلكتروني) | Privacy Policy Section 02 | NOT in Account model — no email field exists |
| Device identifier (معرّف الجهاز) | Privacy Policy Section 02 | NOT collected |
| Browser version and OS details | Privacy Policy Section 02 | NOT stored in database |
| Page visit history | Privacy Policy Section 02 | NOT tracked server-side |
| Performance and interaction data | Privacy Policy Section 02 | NOT collected |

**Action Required:** Either implement collection of these data types or update the Privacy Policy to accurately reflect what is actually collected. The Privacy Policy should not claim to collect data that the system does not collect.

---

## 4. AI & Data Usage Policy

### 4.1 Platform Owner Rights

The Platform Owner reserves the right to use **anonymized and aggregated** gameplay data for:

1. **AI Model Training** — Training machine learning models (hosted or on-premises) for:
   - Game balance optimization (e.g., attack success rate analysis, item pricing models)
   - Anti-cheat detection patterns
   - Quiz difficulty calibration
   - Player engagement prediction

2. **Generative AI Features** — Powering potential future features such as:
   - AI-generated quiz questions
   - Dynamic game narrative content
   - Automated game balance recommendations

3. **Analytics and Optimization** — Using aggregated statistics for:
   - Game design decisions
   - Feature prioritization
   - A/B testing outcomes

### 4.2 Personal Data Exclusions

The following data will **NOT** be used for AI training without explicit, granular, opt-in consent:

- Real names (`real_name`)
- Usernames (`username`)
- Any data that could directly or indirectly identify an individual
- Attack history linked to identifiable individuals
- Individual quiz responses linked to identifiable individuals

### 4.3 Anonymization Standard

Data used for AI purposes must be:
- Stripped of all direct identifiers (username, real_name, account_id)
- Aggregated to a level where re-identification is not reasonably possible
- Processed through a documented anonymization pipeline

### 4.4 Disclosure Requirement

The AI data usage policy **must** be disclosed in the Privacy Policy before any AI processing begins. A new section should be added to the Privacy Policy covering:
- What data is used
- How it is anonymized
- What it is used for
- User's right to object

**Current Status:** The Privacy Policy does NOT currently mention AI/ML data usage. This section must be added before any AI features are developed or any data is used for training purposes.

---

## 5. Multi-Admin Platform Model

### 5.1 Current Architecture

The platform currently operates with a single admin role (`is_admin = true` on the `accounts` table). The architecture is designed to support multiple independent competitions, each managed by admins.

### 5.2 Role Hierarchy

| Role | Scope | Access Level |
|------|-------|-------------|
| **Platform Owner (مالك المنصة)** | Entire system | Super-admin: infrastructure, database, system settings, deployment, all competitions. Has direct database access for legal/technical necessity. |
| **Admin (مشرف)** | Own competition(s) | Full management of competitions they create: players, seasons, cycles, quiz, store, attacks, settings, announcements. |
| **Participant (متسابق)** | Own data within competition | View own profile, attack, answer quizzes, use store, see leaderboard (via aliases). |

### 5.3 Access Boundaries

#### Platform Owner Access
- **CAN** access the database directly for: maintenance, debugging, legal compliance requests, data breach investigation, backup/restore operations
- **CANNOT** access player real names through the standard admin interface — the admin panel shows real names for competition management, but the Platform Owner's access to real names is limited to direct DB access only when justified by legal or technical necessity
- **MUST** log any direct database access in an operational log

#### Regular Admin Access
- **CAN** view all player data (including real names) within competitions they manage — this is necessary for the game mechanics (identity-based attacks, dispute resolution)
- **CANNOT** access competitions they do not manage
- **CANNOT** access system-level settings, infrastructure, or other admins' data
- **CANNOT** access the database directly

#### Legal Protections
- **Platform Owner Liability:** The Platform Owner provides the platform infrastructure but is NOT responsible for individual competition admin decisions regarding player management, scoring adjustments, or game rule configurations within their competitions.
- **Admin Terms of Service:** Each admin must agree to an Admin Terms of Service that covers:
  - Responsibility for their competition's content moderation
  - Obligation to comply with platform-wide rules
  - Prohibition on misusing player personal data
  - Agreement that the Platform Owner may audit their competition for compliance
- **Indemnification:** Admins indemnify the Platform Owner against claims arising from their competition management decisions.

### 5.4 Current Implementation Gap

The current codebase has a single `is_admin` boolean. The multi-admin model with scoped competition access is NOT yet implemented:

- No `platform_owner` vs `competition_admin` distinction in code
- No competition-scoped admin access control (any admin can currently access all admin endpoints)
- No Admin Terms of Service acceptance flow

**Action Required:** Implement role-based access control (RBAC) that scopes admin access to their own competitions before enabling multi-admin features.

---

## 6. Infrastructure & Data Residency

### 6.1 Current Infrastructure

| Component | Location | Provider |
|-----------|----------|----------|
| Application (Docker) | OVH VPS | OVH |
| Database (PostgreSQL) | Same VPS | Self-managed |
| Domain/DNS | Configurable | TBD |
| CDN | None currently | N/A |

### 6.2 VPS Location

The VPS is (or may be) located **outside the Kingdom of Saudi Arabia** — OVH data centers are primarily in France, Canada, and other regions. This decision is driven by cost-effectiveness and server availability.

### 6.3 PDPL Cross-Border Transfer Compliance

Per PDPL Article 29, transferring personal data outside KSA requires:

1. **Adequacy Determination:** SDAIA must have determined that the receiving country provides adequate data protection, OR
2. **Appropriate Safeguards:** Contractual clauses ensuring equivalent protection levels

**Compliance Steps:**
1. Check SDAIA's list of countries with adequate protection levels
2. If the hosting country is not on the list, execute Standard Contractual Clauses with OVH
3. Document the transfer mechanism in the Privacy Policy
4. Conduct a Transfer Impact Assessment if required

### 6.4 Backup Strategy

**Current Implementation (per Deployment Guide):**

| Aspect | Detail |
|--------|--------|
| Method | `pg_dump` via Docker, gzipped |
| Schedule | Daily at 03:00 via cron |
| Location | `/opt/war-of-names/backups/` on the VPS |
| Restore | `./scripts/restore.sh <backup_file>` |
| Retention | Not specified — needs policy |

**Requirements:**
- Manual backup must be exportable as a compressed file that can be downloaded from the server
- Backup should include: accounts, memberships, game data, settings, questions, audit logs
- A documented restore procedure must exist (already documented in deployment guide)
- Backup files must be tested periodically to ensure recoverability

### 6.5 Server Non-Renewal Risk

If the VPS subscription lapses or is not renewed:
- All data on the server will be lost
- The daily backup cron job produces local backups, but these are ON the same server
- **Action Required:** Implement an off-site backup mechanism (e.g., periodic upload of backup files to a separate storage service, or manual download reminder)

---

## 7. Third-Party Services

### 7.1 Current Third-Party Dependencies

| Service | Purpose | Data Shared | DPA Required |
|---------|---------|-------------|-------------|
| OVH (or hosting provider) | VPS hosting | All data (stored on their infrastructure) | YES — must execute DPA |
| Google Fonts CDN | Font loading (Cairo, Changa) | IP address (via CDN request) | NO — no personal data beyond IP in transit |
| Iconify CDN | Icon loading | IP address (via CDN request) | NO — no personal data beyond IP in transit |
| Let's Encrypt (via Caddy) | TLS certificates | Domain name | NO — public service |

### 7.2 Future Third-Party Services

| Service | Purpose | Data Shared | Compliance Requirement |
|---------|---------|-------------|----------------------|
| Google Analytics | Usage tracking | IP, page views, device info, behavior | Must disclose in Privacy Policy; implement cookie consent banner; honor Do Not Track |
| Google Ads | Advertising revenue | IP, tracking cookies, behavior | Must disclose ad tracking in Privacy Policy; implement cookie consent; comply with PDPL Art. 24 on direct marketing |
| Payment gateway (Moyasar recommended) | Real-money purchases | Name, payment details | Must execute DPA; PCI-DSS compliance required; disclose in Privacy Policy |
| Email service (e.g., Mailgun, Resend) | Transactional emails | Email address, name | Must execute DPA; disclose in Privacy Policy |

### 7.3 Privacy Policy Alignment

The current Privacy Policy (Section 07 — Cookies) states: *"We do not use advertising tracking cookies or third-party analytics tools that track your behavior across other websites."*

**This statement must be updated** if Google Analytics, Google Ads, or any tracking services are added. The Privacy Policy must be revised BEFORE activating any such service.

---

## 8. IP Ban System

### 8.1 Functionality

Admin can ban users by IP address to prevent:
- Banned users from creating new accounts
- Multi-account abuse (smurf accounts)
- Platform access by sanctioned individuals

### 8.2 Current Implementation Status

**NOT IMPLEMENTED.** The backend has:
- Account status management (`active`, `suspended`, `disabled`, `archived`)
- Membership status management (`active`, `suspended`, `removed`)
- Audit trail for status changes

But there is NO:
- IP address storage in the database
- IP-based blocking middleware
- Admin interface for viewing/managing IP bans

### 8.3 Legal Requirements When Implemented

| Requirement | Detail |
|-------------|--------|
| Disclosure | Must be disclosed in Terms of Use (currently mentioned implicitly via suspension language) |
| Audit logging | Every IP ban action must be recorded in the audit trail with: admin who issued it, reason, target IP, timestamp |
| Duration | Must support both temporary and permanent bans |
| Appeal process | Users must have a way to appeal IP bans (contact email) |
| Data protection | Stored IP addresses are personal data under PDPL — subject to all PDPL obligations |
| Proportionality | IP bans should be proportionate to the offense — document the policy |

---

## 9. Future Monetization Compliance

### 9.1 Real-Money Store

If the platform introduces real-money purchases:

| Aspect | Requirement |
|--------|-------------|
| **Item type** | COSMETIC ONLY — to avoid gambling classification under Saudi regulations. No pay-to-win mechanics that affect competitive outcomes. |
| **VAT** | 15% VAT must be applied to all digital purchases (ZATCA). VAT amount must be clearly displayed before purchase. |
| **Age verification** | 18+ required for real-money purchases. Must implement age gate or verification. |
| **Pricing transparency** | All prices in SAR. Total including VAT displayed before confirmation. |
| **Payment methods** | Moyasar recommended for Saudi-compliant payment processing (supports mada, Visa, Mastercard, Apple Pay). |

### 9.2 Loot Box / Mystery Box Compliance

The platform already has a box/mystery item system using in-game points. If real money is ever involved:

| Aspect | Requirement |
|--------|-------------|
| **Odds disclosure** | Show exact probability/odds for each possible outcome, even if not yet legally mandated in KSA — this is an industry best practice and preempts likely future regulation. |
| **No gambling classification** | Ensure boxes cannot be characterized as gambling: items have no real-world monetary value, cannot be traded for money, odds are disclosed. |
| **Minimum value guarantee** | Consider guaranteeing minimum value to avoid predatory mechanics perception. |

### 9.3 Refund Policy

| Scenario | Policy |
|----------|--------|
| Unused digital content | 7-day withdrawal right per Saudi E-Commerce Law |
| Used digital content (consumed item, opened box) | EXEMPT from withdrawal — digital content exception applies once content is accessed/used |
| Technical failure (payment processed but item not delivered) | Full refund required |
| Account ban with paid items | No refund — Terms of Use violation forfeits rights |

### 9.4 In-Game Points (Current System)

The current points system (earned through gameplay) does NOT constitute real-money transactions and is NOT subject to e-commerce, VAT, or payment regulations. The Terms of Use (Section 06) already correctly states:
- Points have no real monetary value
- Points cannot be exchanged for real money
- Points cannot be transferred, sold, or traded outside the platform

---

## 10. Backup & Data Export Requirements

### 10.1 Database Backup

| Requirement | Implementation |
|-------------|---------------|
| Automated daily backup | Implemented via cron `pg_dump` (deployment guide Phase 8) |
| Compressed format | `.sql.gz` files |
| Exportable / downloadable | Available on server filesystem; no API endpoint for download |
| Restore capability | `./scripts/restore.sh` documented |

### 10.2 User Data Export (PDPL Compliance)

Per PDPL Article 4 (Right of Portability), users can request their data in a machine-readable format.

**Required Export Contents:**
- Account data: username, real_name, creation date, status
- Membership data: competitions joined, aliases used, join dates
- Game data: attack history (as attacker and defender), quiz answers, scores
- Financial data: point balance, ledger history, purchases
- Inventory: owned items and their status
- Notifications: all notifications received
- Settings: personal preferences

**Current Status:** NOT IMPLEMENTED. No self-service or admin-triggered data export for individual users exists.

**Action Required:**
1. Build a `/api/auth/me/export` endpoint that generates a JSON file containing all user data
2. Implement admin-side data export trigger for responding to formal PDPL requests
3. Response time: within 30 days of request (as promised in Privacy Policy)

### 10.3 Admin-Triggered Full Backup

| Requirement | Status |
|-------------|--------|
| Admin can trigger backup from owner panel | NOT IMPLEMENTED — backup is cron-only |
| Backup download via admin interface | NOT IMPLEMENTED |
| Backup contents | Covered by `pg_dump` (full database) |

**Action Required:**
1. Add an admin endpoint or UI for triggering manual backups
2. Add backup download capability (protected, admin-only)
3. Document backup contents and format in user-facing documentation

### 10.4 Backup Scope

A complete backup must include:

| Data Category | Table(s) | Included in pg_dump |
|---------------|----------|-------------------|
| Accounts | `accounts`, `roles`, `account_roles` | Yes |
| Competitions | `competitions`, `seasons`, `cycles`, `memberships`, `alias_records` | Yes |
| Game data | `attack_attempts`, `ledger_entries`, `bankruptcy_records` | Yes |
| Store | `item_definitions`, `item_effects`, `store_listings`, `owned_items` | Yes |
| Quiz | `question_groups`, `questions`, `quiz_sessions`, `session_questions`, `answer_submissions` | Yes |
| Notifications | `notifications` | Yes |
| Settings | `setting_definitions`, `setting_values` | Yes |
| Audit | `audit_logs` | Yes |
| Invites | `competition_invites` | Yes |
| Media | `media_assets` | Yes |
| Announcements | `announcements` | Yes |

---

## Appendix A: Regulatory Reference Links

| Regulation | Arabic Name | Reference |
|-----------|-------------|-----------|
| Personal Data Protection Law | نظام حماية البيانات الشخصية | Royal Decree M/19, 09/02/1443H |
| Anti-Cybercrime Law | نظام مكافحة جرائم المعلوماتية | Royal Decree M/17, 08/03/1428H |
| E-Commerce Law | نظام التجارة الإلكترونية | Royal Decree M/126, 07/11/1440H |
| Electronic Transactions Law | نظام التعاملات الإلكترونية | Royal Decree M/18, 08/03/1428H |
| VAT Law | نظام ضريبة القيمة المضافة | Royal Decree M/113, 02/11/1438H |

## Appendix B: Compliance Action Tracker

### Critical (Before Public Launch)

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Implement account self-deletion (or formal deletion request flow) | Backend | NOT STARTED |
| 2 | Implement user data export endpoint (JSON) | Backend | NOT STARTED |
| 3 | Add email field to Account model (or remove from Privacy Policy) | Backend + Legal | NOT STARTED |
| 4 | Execute DPA with hosting provider | Platform Owner | NOT STARTED |
| 5 | Document cross-border transfer mechanism | Platform Owner | NOT STARTED |
| 6 | Create breach notification procedure | Platform Owner | NOT STARTED |
| 7 | Implement automated data purge jobs (30-day post-deletion) | Backend | NOT STARTED |
| 8 | Add off-site backup mechanism | DevOps | NOT STARTED |
| 9 | Update Privacy Policy to match actual data collection (remove email if not collected, or add email collection) | Legal + Frontend | NOT STARTED |

### Important (Before Multi-Admin Features)

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 10 | Implement RBAC for multi-admin scoped access | Backend | NOT STARTED |
| 11 | Create Admin Terms of Service | Legal | NOT STARTED |
| 12 | Implement Admin ToS acceptance flow | Backend + Frontend | NOT STARTED |

### Future (Before Monetization)

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 13 | Integrate payment gateway (Moyasar) | Backend | NOT STARTED |
| 14 | Implement VAT calculation and display | Backend + Frontend | NOT STARTED |
| 15 | Implement age verification for purchases | Backend + Frontend | NOT STARTED |
| 16 | Implement loot box odds disclosure | Frontend | NOT STARTED |
| 17 | Create refund policy and refund processing | Backend + Legal | NOT STARTED |
| 18 | Register for VAT with ZATCA if applicable | Platform Owner | NOT STARTED |

### Future (Before Analytics/Ads)

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 19 | Implement cookie consent banner | Frontend | NOT STARTED |
| 20 | Update Privacy Policy for analytics/ads disclosure | Legal + Frontend | NOT STARTED |
| 21 | Add AI data usage section to Privacy Policy | Legal + Frontend | NOT STARTED |
| 22 | Implement IP ban system with audit trail | Backend | NOT STARTED |

---

*End of Document*
