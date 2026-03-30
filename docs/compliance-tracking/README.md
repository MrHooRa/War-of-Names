# Compliance Feature Tracking

This file tracks features/capabilities mentioned in legal pages (Terms of Use, Privacy Policy)
against their actual implementation status. Every claim made to users in the legal pages creates
a compliance obligation — this file ensures nothing is promised but undelivered at launch.

**Source Files:**
- Terms of Use: `frontend/src/pages/TermsPage.jsx` (11 sections)
- Privacy Policy: `frontend/src/pages/PrivacyPage.jsx` (11 sections)

**Last Audited:** 2026-03-29

---

## Status Legend
- IMPLEMENTED — Feature exists and works as described
- PARTIAL — Feature partially exists or has gaps
- NOT IMPLEMENTED — Feature promised but not built yet
- PLANNED — Feature planned for future phase
- N/A — Statement is informational, no implementation needed

---

## Terms of Use Claims

### Section 01 — Introduction (مقدمة)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-01 | Platform is operated from Saudi Arabia | IMPLEMENTED | VPS may be outside KSA but platform is managed from KSA |
| T-02 | Platform is subject to KSA regulations | N/A | Legal statement, no implementation needed |
| T-03 | By using the platform you agree to these terms | IMPLEMENTED | Registration now requires an explicit terms/privacy consent checkbox and backend-enforced consent flag |
| T-04 | We reserve the right to modify terms at any time | N/A | Legal reservation |
| T-05 | Modifications will be announced via in-platform notification or registered email | PARTIAL | Announcement overlay system exists (AnnouncementOverlay.jsx); admin can notify users of terms changes via announcements. No email field exists in Account model |
| T-06 | Continued use after modifications constitutes acceptance | N/A | Legal statement |

### Section 02 — Definitions (التعريفات)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-07 | "Platform" includes all pages and functions | N/A | Definitional |
| T-08 | "Competition" joined via invite code | IMPLEMENTED | Invite code system works (`competition_invites` table, join flow) |
| T-09 | "Alias" is temporary identity within competition | IMPLEMENTED | `alias_records` table, alias selection on join |
| T-10 | "Points" are internal currency for ranking, purchasing, attacking | IMPLEMENTED | Ledger-based scoring engine, store, attack costs |
| T-11 | "Store" allows purchasing virtual items with points | IMPLEMENTED | Store module with listings, purchases, owned items |
| T-12 | "Attack" is guessing another player's real identity | IMPLEMENTED | Attack engine with guess logic, point consequences |

### Section 03 — Eligibility & Account Conditions (أهلية الاستخدام وشروط الحساب)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-13 | Minimum age 13 to create account | NOT IMPLEMENTED | No age verification during registration |
| T-14 | Under 18 requires parental consent | NOT IMPLEMENTED | No parental consent mechanism |
| T-15 | User must provide accurate information | PARTIAL | Registration collects username + real_name but no validation of real_name accuracy |
| T-16 | User is responsible for keeping login credentials secret | N/A | User responsibility, not a system feature |
| T-17 | Any activity under your account is your responsibility | N/A | Legal statement |
| T-18 | Prohibited: more than one account per person per competition | PARTIAL | No technical enforcement — relies on admin detection |
| T-19 | Prohibited: sharing or transferring account | N/A | Policy statement, no technical enforcement |
| T-20 | Platform can suspend or terminate accounts without prior notice | IMPLEMENTED | Admin can change account status to suspended/disabled/archived via `PATCH /api/admin/accounts/{id}/status`; IP ban system implemented via owner panel |

### Section 04 — Fair Play Policy (سياسة اللعب النظيف)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-21 | Prohibited: collusion | N/A | Policy — detection relies on admin judgment |
| T-22 | Prohibited: bots/automated tools | IMPLEMENTED | In-memory rate limiter on auth endpoints (login, register) — 30 req/min per IP; IP ban system for persistent abuse |
| T-23 | Prohibited: exploiting bugs (must report) | N/A | Policy statement — no formal bug report mechanism |
| T-24 | Prohibited: identity impersonation outside alias system | N/A | Policy statement |
| T-25 | Prohibited: harassment | N/A | Policy statement — no in-app messaging to moderate |
| T-26 | Prohibited: smurf accounts (multiple accounts) | PARTIAL | No IP-based detection; no device fingerprinting |
| T-27 | Admin can investigate and take action: warning, point deduction, suspension, permanent ban | PARTIAL | Admin can: adjust points (IMPLEMENTED), suspend membership/account (IMPLEMENTED), but no formal warning system exists |

### Section 05 — Content Rules (قواعد المحتوى)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-28 | No offensive, racist, sectarian language | PARTIAL | No automated content filter on aliases or user input; relies on admin review |
| T-29 | No religious or national insults | PARTIAL | Same as above — no automated filtering |
| T-30 | No sharing personal info of others | N/A | Policy — no mechanism for users to share content beyond aliases |
| T-31 | No pornographic/violent content | PARTIAL | Limited user-generated content (only aliases); no filter |
| T-32 | No harmful links or malicious software | N/A | No URL input fields in current UI |
| T-33 | Comply with Anti-Cybercrime Law | N/A | Legal obligation on user |
| T-34 | Admin can delete violating content without notice | PARTIAL | Admin can suspend/remove players; cannot edit aliases directly through admin panel |

### Section 06 — Virtual Items & Points (العناصر الافتراضية والنقاط)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-35 | Points are not real currency, no monetary value | N/A | Legal/definitional — enforced by not having real-money exchange |
| T-36 | Points/items cannot be exchanged for real money | N/A | No exchange mechanism exists (correct) |
| T-37 | Admin can modify item prices/properties at any time | IMPLEMENTED | Admin can update items via `PATCH /api/admin/store/items/{id}` and deactivate listings |
| T-38 | No vested right in point balance or virtual items | N/A | Legal statement |
| T-39 | Balances may change at season/cycle end per game rules | IMPLEMENTED | Cycle management endpoints exist; admin can reset balances via bulk actions |

### Section 07 — Intellectual Property (الملكية الفكرية)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-40 | All IP belongs to War of Names platform | N/A | Legal declaration |
| T-41 | Prohibited: copying/redistributing platform content | N/A | Legal prohibition |
| T-42 | Prohibited: using brand name/logo commercially | N/A | Legal prohibition |
| T-43 | User retains ownership of their content (aliases) | N/A | Legal statement |
| T-44 | User grants platform non-exclusive license to use content | N/A | Legal statement |

### Section 08 — Liability Limitations (حدود المسؤولية)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-45 | Platform provided "as is" | N/A | Legal disclaimer |
| T-46 | Not liable for direct/indirect damages | N/A | Legal disclaimer |
| T-47 | Not liable for disputes between users | N/A | Legal disclaimer |
| T-48 | Not liable for data loss from technical failures | PARTIAL | Daily backups exist but no redundancy; no off-site backup |
| T-49 | User responsible for all activity on their account | N/A | Legal statement |

### Section 09 — Account Termination (إنهاء الحساب)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-50 | User can delete account at any time via settings or by contacting admin | IMPLEMENTED | `POST /api/auth/me/request-deletion` endpoint + button in AccountSettingsPage; creates audit event for owner review |
| T-51 | Platform can suspend/terminate accounts with or without notice | IMPLEMENTED | Admin can change account status (suspend/disable/archive) |
| T-52 | Upon termination, user loses access to all data, points, items | PARTIAL | Status change blocks access, but data is not deleted |
| T-53 | Platform may retain some data after deletion per legal requirements | N/A | Legal reservation — but no actual deletion mechanism exists to trigger retention rules |
| T-54 | Termination does not relieve user of pre-existing obligations | N/A | Legal statement |

### Section 10 — Governing Law & Dispute Resolution (القانون الحاكم)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-55 | Governed by KSA law | N/A | Legal statement |
| T-56 | References: E-Transactions Law, Anti-Cybercrime Law, PDPL, E-Commerce Law | N/A | Legal reference |
| T-57 | 30-day amicable resolution period | N/A | Process commitment |
| T-58 | Saudi courts have exclusive jurisdiction | N/A | Legal statement |

### Section 11 — Contact Us (التواصل معنا)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| T-59 | Contact via email: support@warofnames.com | NOT IMPLEMENTED | Email address is stated but no email infrastructure exists; no mailbox verified |
| T-60 | We will respond as soon as possible | N/A | Process commitment |

---

## Privacy Policy Claims

### Section 01 — Introduction (مقدمة)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-01 | Compliant with PDPL (Royal Decree M/19) | PARTIAL | Privacy Policy text references PDPL correctly, but several PDPL rights are not technically enforceable yet |
| P-02 | Policy explains how data is collected, used, stored, protected, shared | IMPLEMENTED | Privacy Policy covers all these areas |
| P-03 | Modifications announced via in-platform notification | PARTIAL | Announcement overlay system exists (AnnouncementOverlay.jsx); admin can notify users of policy changes via announcements. No automated versioned terms tracking |

### Section 02 — Data We Collect (البيانات التي نجمعها)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-04 | Collect: real name at registration | IMPLEMENTED | `real_name` field in Account model |
| P-05 | Collect: email address | IMPLEMENTED | Email reference removed from Privacy Policy — page no longer claims email is collected, matching actual behavior |
| P-06 | Collect: password (stored encrypted, nobody can see it) | IMPLEMENTED | bcrypt hash stored; not reversible |
| P-07 | Collect: alias chosen in competition | IMPLEMENTED | `alias_records` table |
| P-08 | Collect: IP address | PARTIAL | IP is now stored on auth/security audit events, but not yet for all request/session activity |
| P-09 | Collect: browser type, version, OS | PARTIAL | Browser/OS metadata is now captured on auth/security audit events, but no full telemetry pipeline exists |
| P-10 | Collect: device identifier and session info | PARTIAL | JWT tokens for sessions; no device identifier stored |
| P-11 | Collect: activity log (pages visited, login/logout times) | PARTIAL | `last_login_at` tracked; no page visit tracking |
| P-12 | Collect: performance and interaction data | NOT IMPLEMENTED | No performance/interaction tracking |
| P-13 | Collect: attack and defense records | IMPLEMENTED | `attack_attempts` table |
| P-14 | Collect: point balance and transaction history | IMPLEMENTED | `ledger_entries` table |
| P-15 | Collect: purchased and used items | IMPLEMENTED | `owned_items` table |
| P-16 | Collect: quiz session results | IMPLEMENTED | `answer_submissions` table |
| P-17 | Collect: ranking and competition position | IMPLEMENTED | Calculated from ledger; leaderboard endpoint exists |

### Section 03 — Purpose of Data Use (أغراض استخدام البيانات)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-18 | Purpose: platform operation (account, auth, sessions, gameplay) | IMPLEMENTED | Core functionality works |
| P-19 | Purpose: security (fraud detection, unauthorized access prevention) | PARTIAL | Auth tokens and admin status checks exist; no advanced fraud detection |
| P-20 | Purpose: service improvement (usage pattern analysis) | NOT IMPLEMENTED | No analytics pipeline exists |
| P-21 | Purpose: communication (account/competition notifications, security updates) | IMPLEMENTED | In-app notification system works |
| P-22 | Purpose: legal compliance | PARTIAL | Audit trail exists; data retention rules not automated |
| P-23 | Purpose: fair play enforcement | PARTIAL | Admin can investigate and act; no automated detection |
| P-24 | Won't use data for other purposes without consent (PDPL Art. 5) | N/A | Commitment — no violation currently |

### Section 04 — Data Storage & Protection (تخزين البيانات وحمايتها)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-25 | Data stored on secure servers with modern encryption (TLS/SSL, bcrypt) | IMPLEMENTED | Caddy provides TLS; bcrypt for passwords |
| P-26 | Strict access controls, data accessible only to authorized persons | PARTIAL | Admin role exists; but no fine-grained RBAC for multi-admin |
| P-27 | Data stored/processed within KSA; cross-border per PDPL Art. 29 | NOT IMPLEMENTED | VPS is outside KSA; no PDPL Art. 29 documentation or SCCs in place |
| P-28 | Periodic security reviews | NOT IMPLEMENTED | No documented security review process |
| P-29 | Breach notification to authorities and affected users per regulations | NOT IMPLEMENTED | No breach notification procedure documented |

### Section 05 — Data Sharing with Third Parties (مشاركة البيانات مع أطراف ثالثة)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-30 | We do not sell or rent personal data | N/A | Policy commitment — no data selling mechanism exists |
| P-31 | Share with technical service providers (hosting, infrastructure) per DPA | PARTIAL | Data is on hosting provider's infrastructure, but no DPA executed |
| P-32 | Share for legal compliance (court order, government request) | N/A | Process commitment |
| P-33 | Share to protect platform rights/user safety | N/A | Process commitment |
| P-34 | Share aggregated non-identifying statistics | NOT IMPLEMENTED | No aggregation/sharing pipeline exists |
| P-35 | Data minimization principle in all sharing | N/A | Policy commitment |

### Section 06 — Gameplay Data Privacy (خصوصية بيانات اللعب)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-36 | Alias visible to all competition participants | IMPLEMENTED | Leaderboard and dashboard show aliases |
| P-37 | Alias-to-real-identity link protected; only revealed via game mechanics (successful attack, bankruptcy) | IMPLEMENTED | Attack success reveals identity; alias_record.is_revealed flag |
| P-38 | Battle records visible to attacker, defender, and admin | IMPLEMENTED | Attack history endpoints scoped correctly |
| P-39 | Points and ranking visible to all via alias only | IMPLEMENTED | Leaderboard shows alias + points; no real name exposure |
| P-40 | Admin can view all gameplay data for management and integrity | IMPLEMENTED | Admin endpoints provide full data access |

### Section 07 — Cookies & Similar Technologies (ملفات تعريف الارتباط)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-41 | Session cookies for login maintenance | IMPLEMENTED | JWT tokens used (localStorage, not cookies, but functionally equivalent) |
| P-42 | Auth tokens stored locally for persistent access | IMPLEMENTED | JWT stored in localStorage |
| P-43 | Local storage for display preferences (dark/light mode) | IMPLEMENTED | Theme toggle uses localStorage |
| P-44 | We do NOT use advertising tracking cookies or third-party analytics | IMPLEMENTED | No tracking scripts in codebase — MUST UPDATE if analytics/ads are added |

### Section 08 — Data Retention (الاحتفاظ بالبيانات)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-45 | Data retained while account is active | IMPLEMENTED | Data persists in database |
| P-46 | Identifiable data deleted within 30 days of account deletion | NOT IMPLEMENTED | No account deletion mechanism exists; no 30-day purge job |
| P-47 | Audit/transaction logs retained up to 1 year post-deletion | NOT IMPLEMENTED | No retention policy enforcement; no deletion triggers |
| P-48 | Aggregated non-identifying data may be kept longer | N/A | No aggregation system exists yet |

### Section 09 — User Rights Under PDPL (حقوقك بموجب نظام حماية البيانات الشخصية)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-49 | Right of access: obtain copy of personal data (Art. 4) | IMPLEMENTED | `GET /api/auth/me/export-data` provides self-service machine-readable export; owner export also exists |
| P-50 | Right of correction: request correction of inaccurate data (Art. 4) | PARTIAL | Users can update `real_name` via account settings; cannot correct other data fields |
| P-51 | Right of deletion: request deletion when data no longer needed (Art. 4) | IMPLEMENTED | `POST /api/auth/me/request-deletion` endpoint + button in AccountSettingsPage; Privacy Policy text updated to reflect availability |
| P-52 | Right of consent withdrawal (Art. 6) | NOT IMPLEMENTED | No consent management; no withdrawal mechanism |
| P-53 | Right of objection: object to processing in certain cases | NOT IMPLEMENTED | No objection process |
| P-54 | Right of portability: data transfer in machine-readable format (Art. 4) | IMPLEMENTED | Account settings now allow downloading a JSON export from `GET /api/auth/me/export-data` |
| P-55 | Requests responded to within 30 days | NOT IMPLEMENTED | No formal request intake/tracking system |

### Section 10 — Children's Privacy (خصوصية الأطفال)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-56 | Platform does not target children under 13 | N/A | Policy statement |
| P-57 | Ages 13-18 require parental consent (PDPL Art. 10) | NOT IMPLEMENTED | No age verification or parental consent mechanism |
| P-58 | If child under 13 registers without consent, account will be deleted | NOT IMPLEMENTED | No age detection; no automated deletion |

### Section 11 — Contact Us (التواصل معنا)

| # | Claim | Status | Notes |
|---|-------|--------|-------|
| P-59 | Contact via email: privacy@warofnames.com | NOT IMPLEMENTED | Email address stated but no mailbox/infrastructure verified |
| P-60 | Right to file complaint with SDAIA | N/A | Legal information — no implementation needed |

---

## Summary Statistics

| Status | Terms of Use | Privacy Policy | Total |
|--------|-------------|----------------|-------|
| IMPLEMENTED | 14 | 21 | 35 |
| PARTIAL | 8 | 10 | 18 |
| NOT IMPLEMENTED | 2 | 9 | 11 |
| PLANNED | 0 | 0 | 0 |
| N/A | 36 | 11 | 47 |

**Total trackable claims (excluding N/A):** 64
**Compliance coverage:** 54.7% IMPLEMENTED, 28.1% PARTIAL, 17.2% NOT IMPLEMENTED

---

## Action Items Before Public Launch

### Critical — Legal Compliance Risk

1. [x] **Implement account self-deletion** — `POST /api/auth/me/request-deletion` + AccountSettingsPage button. Creates audit event for owner review. (T-50, P-51)
2. [x] **Implement user data export** — `GET /api/auth/me/export-data` + AccountSettingsPage download action now provide self-service access/portability export. (P-49, P-54)
3. [x] **Fix email discrepancy** — Privacy Policy no longer claims email is collected; page was rewritten to match actual data collection. (P-05)
4. [ ] **Expand IP address collection or narrow the claim** — Auth/security audit events now store IPs, but collection is not yet comprehensive across all activity. (P-08)
5. [ ] **Complete browser/OS/device/activity telemetry or narrow the claims** — Auth/security audit events now capture browser/OS metadata, but device/activity/performance claims remain broader than the implementation. (P-09, P-10, P-12)
6. [ ] **Execute DPA with hosting provider** — Privacy Policy promises DPA-backed data sharing (P-31) but no DPA exists.
7. [ ] **Document cross-border data transfer** — Privacy Policy references PDPL Art. 29 compliance (P-27) but no documentation or safeguards exist.
8. [ ] **Create breach notification procedure** — Privacy Policy promises regulatory notification (P-29) but no procedure exists.
9. [ ] **Implement data retention automation** — Privacy Policy promises 30-day deletion (P-46) and 1-year audit retention (P-47) but no purge jobs exist.
10. [ ] **Set up support@warofnames.com** — Terms contact email (T-59) and **privacy@warofnames.com** — Privacy Policy contact email (P-59).

### Important — Feature Gaps

11. [x] **Implement terms change notification** — Announcement overlay system available; admin can notify via announcements. Marked PARTIAL. (T-05, P-03)
12. [ ] **Add age verification** — Both pages reference age restrictions (T-13, T-14, P-57) with zero enforcement.
13. [ ] **Add content filtering** for aliases — Terms promises content moderation (T-28, T-29) but no automated filter exists.
14. [x] **Add rate limiting/bot protection** — In-memory rate limiter added to auth endpoints (30 req/min per IP); IP ban system via owner panel. (T-22)
15. [ ] **Implement formal PDPL request intake** — Privacy Policy promises 30-day response to rights requests (P-55) but no intake system exists.
16. [ ] **Implement periodic security review process** — Privacy Policy claims this (P-28).
17. [ ] **Add off-site backup** — Terms acknowledges no data loss liability (T-48) but backups are local-only.

### Low Priority — Process Items

18. [ ] **Create formal bug report mechanism** — Terms requires users to report exploits (T-23) but provides no channel beyond email.
19. [ ] **Document security review schedule** — Commit to periodic reviews as promised (P-28).
20. [ ] **Implement admin warning system** — Terms mentions warnings as an escalation step (T-27) but no formal warning feature exists.
21. [x] **Add explicit terms acceptance checkbox** at registration — Registration now requires explicit consent in frontend and backend. (T-03)

---

*This document should be updated whenever legal pages are modified or new features are implemented.*
