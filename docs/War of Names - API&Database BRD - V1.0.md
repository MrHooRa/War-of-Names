API Contract Specification
Project: Seasonal Alias Attack Competition Platform
Scope

This specification defines the contractual structure of the backend interface exposed to the frontend and admin client(s). It focuses on:

domain boundaries

payload expectations

input/output responsibilities

permissions

invariants

state transitions

response behavior

It does not define:

exact implementation details

framework-specific routing

controller/service names

ORM behavior

deployment behavior

1) API Contract Principles
1.1 Source of Truth

The backend is the only source of truth for:

account identity

competition membership state

alias visibility

score balance

ledger entries

attack eligibility and resolution

item definitions and item ownership

quiz eligibility and scoring

administrative actions

audit events

cycle and season state

The frontend must never be trusted to compute any authoritative business outcome.

1.2 Contract Stability

The API contract must be designed so that:

the frontend can evolve independently

the backend can evolve internally without breaking consumers

payload structures remain predictable

breaking changes are explicit and versioned if needed

1.3 Separation of Concerns

The API must separate:

authentication/account concerns

competition/membership concerns

gameplay actions

administrative actions

reporting/read models

audit/operational views

1.4 Deterministic Responses

Any operation that changes game state must return:

outcome status

user-visible effect

state references needed for frontend refresh

error semantics when rejected

1.5 Explicit Permission Boundaries

Each contract must clearly imply whether it is:

public

authenticated user

competition participant

competition-specific admin

system/global admin

2) Contract Structure Standards

Every contract should conceptually follow a consistent structure.

2.1 Request Types

Requests fall into these categories:

authentication requests

retrieval requests

command/action requests

admin mutation requests

file import/export requests

system settings requests

2.2 Response Types

Responses should conceptually contain one of:

resource payload

collection payload

action result payload

validation error payload

permission error payload

state conflict payload

system error payload

2.3 Standard Response Envelope

At a conceptual level, responses should provide:

success flag or outcome state

data payload when applicable

user-safe message

machine-usable error code/category when applicable

metadata when applicable

timestamps when helpful

pagination info for collections

This does not force a specific JSON wrapper style, but the semantics must exist.

3) Identity and Access Contract Domains
3.1 Account Authentication Contracts
Purpose

Manage platform-level identity.

Required capabilities

register account

login

logout

refresh/renew session if applicable

reset password workflow

change password

fetch current account context

Input responsibilities

The API must accept:

username

password

account profile fields required at registration

password reset token/workflow fields where applicable

Output responsibilities

The API must return:

account identity summary

authentication/session state

allowed user-level capabilities

minimal profile needed by the frontend shell

Core invariants

passwords are never returned

authentication tokens/session secrets are never exposed in unsafe ways

disabled/suspended accounts cannot authenticate successfully

account identity is separate from competition membership identity

3.2 Account Profile Contracts
Purpose

Allow the authenticated user to manage global account data.

Required capabilities

fetch account profile

update editable profile fields

change real name

view linked memberships

view account state

Output responsibilities

Must return:

account id

username

real name

account status

created timestamps

last activity reference if relevant

list or summary of memberships

Core invariants

changing real name must not corrupt historical audit data

changing real name must not alter alias history

profile update rules must be separate from competition rules

4) Competition and Membership Contract Domains
4.1 Competition Discovery / Join Contracts
Purpose

Allow authenticated users to join competitions.

Required capabilities

join via invite code

join via invite link

validate join eligibility

fetch competition join summary before confirmation

Output responsibilities

Before join confirmation, the contract should be able to return:

competition title

competition status

registration status

whether joining is allowed

human-readable denial reason if not allowed

After successful join:

membership identity summary

competition identity summary

current season/cycle context if active

current visible alias status if already assigned

Core invariants

a join operation creates or activates a membership, not a new account

the same account may join multiple competitions if allowed

join denial reasons must be explicit and frontend-safe

4.2 Competition Context Contracts
Purpose

Expose competition-level information to a participant or admin.

Required capabilities

fetch competition home context

fetch current season and cycle summary

fetch participant summary for current membership

fetch visibility rules relevant to current client

Output responsibilities

Must include enough data for the competition shell page:

competition identity

season identity and status

cycle identity and status

countdown or date boundaries

user membership state

current alias

visible ranking position

current score

relevant alerts/notifications summary

Core invariants

the participant should only receive what is visible under current rules

admin clients may receive expanded context

hidden competition data must not leak through convenience payloads

4.3 Membership Contracts
Purpose

Represent the relationship between account and competition.

Required capabilities

fetch membership details

fetch membership status

admin update membership state

suspend/remove/archive membership

view membership history summary

Output responsibilities

Must distinguish between:

account identity

membership identity

competition-specific state

alias-related state

scoring-related state

Core invariants

membership is the core competition participation unit

all competition-level gameplay actions attach to membership

membership removal must preserve historical records

5) Season and Cycle Contract Domains
5.1 Season Contracts
Purpose

Represent long-running structured competition periods.

Required capabilities

create season

update season

activate season

end season

fetch season summary

fetch season leaderboard summary

fetch season settings snapshot

Output responsibilities

Must include:

season id

season label/name

start/end times

status

current cycle reference

settings snapshot or reference

leaderboard visibility summary

Core invariants

season state is separate from cycle state

season settings may inherit from competition settings but should be resolvable at runtime

5.2 Cycle Contracts
Purpose

Represent shorter operational gameplay windows inside a season.

Required capabilities

create cycle

start cycle

pause cycle

end cycle

fetch cycle state

fetch cycle-specific gameplay constraints

Output responsibilities

Must include:

cycle id

state

start/end time

whether gameplay actions are currently allowed

whether quizzes are open

whether attacks are enabled

cycle-scoped restrictions that affect frontend display

Core invariants

gameplay eligibility may depend on cycle state

cycle boundaries are authoritative server-side

timing behavior uses backend time, not frontend local time

6) Leaderboard / Player View Contract Domains
6.1 Leaderboard Contracts
Purpose

Provide ranked, visible participant information.

Required capabilities

fetch leaderboard for competition/season/cycle

fetch pagination if needed

fetch participant rank context around current user

Output responsibilities

For each visible participant row, the contract must be able to return:

participant membership id

visible alias

visible score

rank

successful attacks count

attacks received count

status summary

bankrupt flag

real name only if visible by rule

optional public markers configured by admin

Core invariants

no hidden real identity leakage except allowed states

sorting semantics must be deterministic

rank ties, if any, must have a defined behavior

6.2 Participant Profile Contracts
Purpose

Provide deeper visible information about a specific participant.

Required capabilities

fetch participant profile view

fetch visible attack summary/history

fetch attack eligibility preview context from this page

Output responsibilities

Must be role-aware:

participant-view payload

admin-view payload

Participant-visible payload may include:

alias

current score

visible state

rank

successful attacks count

received attacks count

bankruptcy state if visible

allowed historical summaries

attack action eligibility snapshot

Admin-visible payload may additionally include:

real identity

internal state flags

exact protection states

membership control actions

audit references

Core invariants

participant profile is not an unrestricted data dump

visible history must respect privacy/game balance rules

7) Attack Engine Contract Domains
7.1 Attack Eligibility / Preview Contracts
Purpose

Allow frontend to present an attack action safely before execution.

Required capabilities

fetch attack eligibility against a target

preview outcome before confirmation

Input expectations

Must receive:

attacker membership context

intended target participant reference

guessed real identity target reference

guessed alias payload

Output responsibilities

The preview must be able to return:

whether action is currently allowed

reason if blocked

estimated reward

estimated penalty

active modifiers affecting reward

active restrictions affecting outcome

whether target is protected

whether target is bankrupt

whether attacker is disallowed

warning messages suitable for UI

Core invariants

preview is advisory but based on authoritative backend state

preview must not leak hidden information beyond what gameplay allows

preview must not itself mutate state

7.2 Attack Execution Contracts
Purpose

Resolve an attack attempt.

Required capabilities

execute attack

return resolved outcome

update immediate gameplay state

Output responsibilities

Must return enough for immediate frontend reconciliation:

action accepted or rejected

final outcome type

success/failure/blocked category

reward granted

penalty applied

target state change summary

protection update summary

bankruptcy trigger summary if applicable

notification-worthy message

references for refreshing leaderboard/profile/inventory if needed

Core invariants

attack resolution is authoritative and server-side only

attack execution must be deterministic

attack must be idempotency-safe enough to avoid duplicate submission effects

timing order must be respected

outcome should always be explainable through audit and ledger records

7.3 Attack History Contracts
Purpose

Display historical and analytical views of attack activity.

Required capabilities

fetch attack history for a participant

fetch attack history for admin

fetch attack details

Output responsibilities

Depending on viewer role, may include:

timestamp

outcome

attacker visible alias or admin identity

target visible alias or admin identity

reward/penalty result

visible state changes

reason for block/rejection

cycle/season reference

Core invariants

role-based visibility is mandatory

attack history should not leak hidden identity unless rules allow it

8) Score / Ledger Contract Domains
8.1 Score Summary Contracts
Purpose

Expose current score state.

Required capabilities

fetch current balance

fetch score summary by competition/season/cycle

fetch score components summary if needed

Output responsibilities

Must return:

current balance

visible derived indicators

recent gain/loss summary

bankruptcy threshold context if relevant

score state flags

Core invariants

balance is derived from authoritative ledger logic

summary payload should not replace detailed ledger traceability

8.2 Ledger Contracts
Purpose

Expose financial state transitions.

Required capabilities

fetch ledger entries for current user

fetch ledger entries for admin

fetch ledger entry details

admin adjustment request

Output responsibilities

Ledger views must be able to express:

entry type

amount

direction

before/after if tracked

source event reference

created timestamp

cause/label

actor/source category

visibility-safe message

Core invariants

every score-affecting action must map to ledger

admin adjustments must never bypass ledger

ledger must support auditability and explanation

9) Store / Item / Reward Contract Domains
9.1 Store Catalog Contracts
Purpose

Expose purchasable gameplay items.

Required capabilities

fetch store catalog

fetch item detail

fetch eligibility state for each visible item

Output responsibilities

For each item shown to a participant:

item id

display name

rarity

description

visible effect summary

price

stock/limit visibility if applicable

eligibility

denial reason if not eligible

whether purchase leads to inventory ownership or instant effect

Core invariants

item catalog visibility may be filtered by rules

store output is viewer-context aware

item definition and item ownership remain conceptually distinct

9.2 Purchase Contracts
Purpose

Resolve item purchase.

Required capabilities

preview purchase if needed

execute purchase

Output responsibilities

Must return:

purchase accepted/rejected

cost applied

resulting balance

inventory update summary

immediate effect summary if auto-applied

reason if denied

Core invariants

purchase must respect score availability and item rules

purchase cost must create ledger entries

purchase side effects must be traceable

9.3 Inventory Contracts
Purpose

Expose participant-owned items and their states.

Required capabilities

fetch participant inventory

fetch item ownership detail

fetch use eligibility

execute item use when applicable

Output responsibilities

For each owned item:

ownership id

item reference

quantity

state

expiry if relevant

uses remaining

active effect state if relevant

whether usable now

denial reason if not usable

Core invariants

inventory is participant-state, not catalog-state

item ownership lifecycle must be visible to the system even after use/expiry if needed historically

9.4 Reward / Box Contracts
Purpose

Expose and resolve granted rewards or boxes.

Required capabilities

fetch reward inbox or reward states

fetch unopened boxes

open a box

fetch opened result

Output responsibilities

Must return:

reward identity

type

source

eligibility/openability

expiry if relevant

open result summary

resulting ledger/inventory references

Core invariants

a box is a reward mechanism, not a special-case disconnected system

reward outcomes must be auditable

opening a box must produce deterministic persisted outcome once resolved

10) Distribution Contract Domains
10.1 Distribution Administration Contracts
Purpose

Define and manage timed or manual grants.

Required capabilities

create distribution

update distribution

schedule distribution

execute distribution manually

fetch distribution status

fetch execution results

Output responsibilities

Must support:

distribution identity

distribution type

target scope

content definition summary

schedule

current status

execution outcome summary

partial failure reporting if applicable

Core invariants

distribution is a first-class domain object

score distributions, item grants, and reward grants must all route into their canonical engines

11) Quiz / Question Contract Domains
11.1 Question Bank Contracts
Purpose

Manage reusable question content.

Required capabilities

list question groups

create question group

update question group

archive question group

create question

update question

archive question

import from spreadsheet

export question content

Output responsibilities

Question group detail must return:

group identity

label/name

description

status

question count

media capability summary

updated timestamps

Question detail must return:

question identity

question type

prompt

options if applicable

correct answer internally for admin contexts only

score value

media reference or external URL

classification data

status

Core invariants

reusable question content is separate from session delivery

participant-facing contracts must never leak correct answers before allowed

11.2 Quiz Session Contracts
Purpose

Represent an actual playable question event.

Required capabilities

create session

update session

open/close session

fetch current active sessions

fetch session detail for participant

submit answer

fetch result state

Participant-facing output responsibilities

Must return:

session identity

session state

visibility/open state

current time window

question payload

media payload if any

remaining time

user answer state

whether submission is allowed

result visibility if allowed

Admin-facing output responsibilities

Must additionally support:

correct answers

participation counts

scoring summary

result status

import source references

Core invariants

answer scoring is backend-authoritative

session timing is backend-authoritative

answer submission must be traceable

question bank reuse must not mutate original question semantics unexpectedly

12) Notification Contract Domains
12.1 Notification Retrieval Contracts
Purpose

Deliver user-facing event awareness.

Required capabilities

fetch unread count

fetch notifications list

mark as read

archive/hide if desired

Output responsibilities

Each notification should be able to express:

notification id

type/category

message

created time

read state

related reference

deep-link hint if applicable

urgency level if relevant

Core invariants

notifications must be user-safe

notifications must not be relied upon as the only source of truth for critical state

notifications must map to domain events or admin events

13) Settings Contract Domains
13.1 Settings Retrieval Contracts
Purpose

Expose configuration in a controlled, structured way.

Required capabilities

fetch effective settings for a competition/season/cycle

fetch settings metadata

fetch admin-editable settings

Output responsibilities

Must support:

category

key/identifier

current value

default value

description

data type

allowed range/options

editability

scope level

last updated metadata

Core invariants

settings must be scope-aware

settings output must be structured, not ad hoc

effective values must be resolvable deterministically

13.2 Settings Mutation Contracts
Purpose

Allow admin-driven rule changes.

Required capabilities

update settings

bulk update grouped settings where safe

preview/validate setting changes if needed

Output responsibilities

Must return:

accepted/rejected state

resulting effective values

validation issues

whether change impacts live behavior immediately

audit reference

Core invariants

all setting changes are auditable

settings change must not silently corrupt active game logic

14) Audit / Operational Contract Domains
14.1 Audit Retrieval Contracts
Purpose

Expose human-readable system history.

Required capabilities

fetch audit events list

filter by type/date/actor/entity

fetch event detail

Output responsibilities

Each audit event should be able to return:

event id

type

actor

subject entity

timestamp

message/summary

cause or reason if present

before/after summaries when applicable

related references

Core invariants

audit is operational history, not financial history

audit visibility is admin-controlled

audit messages must be readable and useful

15) Media / File Contract Domains
15.1 Upload / Reference Contracts
Purpose

Support question media, imports, and exports.

Required capabilities

upload media

register external media URL

attach media reference to domain object

fetch media metadata

import spreadsheet

export file artifacts

Output responsibilities

Must return:

media/file identity

type

source type

usage context

size if relevant

status

safe retrieval reference

Core invariants

file/media identity is separate from question identity

media access must respect security rules

import/export actions must be auditable

16) Error Contract Model

The API must classify errors conceptually into:

Validation errors

Bad or incomplete input.

Permission errors

Authenticated but not allowed.

Authentication errors

Unauthenticated or invalid session.

State conflict errors

The request is well-formed but not allowed under current domain state.

Examples:

cycle closed

target fully protected

user bankrupt

item expired

session already closed

Not found errors

Resource unavailable or not visible in this context.

System errors

Unexpected server-side failures.

Contract rules

Each error response should provide:

machine-readable category/code

human-safe message

enough context for the frontend to react appropriately

no leakage of sensitive internal details

17) Pagination / Filtering / Sorting Contract Principles

For list-style resources, the contract should support where relevant:

pagination

filtering

sorting

date range filtering

state filtering

actor/entity filtering for audit

competition/season/cycle scoping

The contract must define stable sort semantics for leaderboard and history views.

18) Contract-Level Security Principles

all mutating actions require authenticated context

admin contracts require elevated permission context

participant actions require membership-scoped authorization

hidden data must not leak through “convenience” nested payloads

preview contracts must not reveal protected identity information

file references must not bypass visibility rules

19) Contract-Level Invariants Summary

These are non-negotiable core truths the contracts must preserve:

Account != Membership

Real identity != Alias

Balance != Ledger

Ledger != Audit

Item Definition != Item Ownership

Question Bank != Quiz Session

Reward Box != Store Item by default

Season != Cycle

Preview != Execution

Frontend display state != backend authoritative state

Database Conceptual Schema Specification
Project: Seasonal Alias Attack Competition Platform
Scope

This defines the conceptual data model of the platform.

This is not:

final physical schema

final table naming

SQL DDL

ORM schema

indexing plan

migration script

This is:

domain entities

responsibilities

relationships

lifecycle roles

invariants

boundaries

1) Schema Modeling Principles
1.1 Domain-first Modeling

The schema must represent the real domain objects of the system, not just screen forms.

1.2 Explicit Boundaries

Entities must be separated where domain meaning differs, even if implementation later optimizes them.

1.3 History Preservation

The model must preserve history for:

scoring

attacks

aliases

settings changes

admin interventions

item ownership changes

cycle/season changes

1.4 Scoped Identity

Many things are scoped:

account is global

membership is competition-scoped

alias is membership-scoped

attacks are cycle/season scoped

settings are scope-aware

rewards may be global-to-competition or cycle-scoped

1.5 Do Not Collapse Distinct Concepts

Never conceptually merge:

account and membership

balance and ledger

audit and ledger

item template and owned item

reward definition and reward grant

question definition and session-delivered question state

2) Core Domain Entity Groups

The conceptual schema can be understood in these groups:

Identity & Access

Competition Structure

Membership Gameplay Identity

Score & Financial Trace

Attack & Protection State

Store / Item / Reward System

Question Bank & Quiz Delivery

Notification & Messaging

Audit & Settings

Media & Import/Export Support

3) Identity & Access Entities
3.1 Account
Purpose

Represents the global platform user identity.

Conceptual fields

global account identity

username/login identifier

real name

authentication credentials representation

account status

created/updated timestamps

last activity references

localization preference if used later

Relationships

one account can have many memberships

one account can have many audit actions as actor

one account can receive many notifications

one account may own uploaded/imported files as actor/source

Invariants

account exists independently of any competition

account deletion must not destroy historical references

real name changes affect future display rules, not past audit truth

3.2 Role / Permission Model
Purpose

Represent platform permissions.

Conceptual fields

role identity

scope

permission set

assignment status

Relationships

linked to accounts or scoped admin access

future-ready for multiple roles

Invariants

current MVP may effectively use one admin role, but schema should not prevent later expansion

4) Competition Structure Entities
4.1 Competition
Purpose

Top-level gameplay container.

Conceptual fields

competition identity

display name

description

status

registration visibility state

join mode

invite configuration

visibility configuration

created/updated timestamps

Relationships

one competition has many memberships

one competition has many seasons

one competition has many settings scoped at competition level

one competition may have many item/catalog settings

one competition may have many quiz sessions through seasons/cycles

Invariants

competition is the root gameplay container

memberships cannot exist without competition context

4.2 Competition Invite / Join Mechanism
Purpose

Represent joinable invitation references.

Conceptual fields

invite identity

invite type

token/code reference

status

expiry

usage rules

Relationships

belongs to competition

Invariants

invite data is not the same as membership

invite invalidation should not affect existing memberships

4.3 Season
Purpose

Long-duration structured phase of a competition.

Conceptual fields

season identity

competition reference

name/label

start/end time

state

configuration snapshot or effective settings relation

ordering/index within competition

Relationships

one competition has many seasons

one season has many cycles

one season has many leaderboard-relevant events

one season may scope settings, distributions, rewards, quiz sessions

Invariants

season lifecycle is independent but subordinate to competition lifecycle

4.4 Cycle
Purpose

Shorter operational window within a season.

Conceptual fields

cycle identity

season reference

label/index

start/end time

state

current operational flags

ordering

Relationships

belongs to season

associated with attacks, bankruptcies, distributions, quizzes, visible states

Invariants

cycle is the main temporal scope for many gameplay rules

only explicitly active cycles permit action where rules require it

5) Membership Gameplay Identity Entities
5.1 Membership
Purpose

Represents one account participating in one competition.

Conceptual fields

membership identity

account reference

competition reference

membership status

join time

participation flags

current gameplay state summary references

current visible score snapshot if denormalized

current alias reference if denormalized

Relationships

belongs to one account

belongs to one competition

can participate across many seasons/cycles within that competition

has many aliases over time

has many ledger entries

has many attacks as attacker or target

has many owned items

has many notifications

has many quiz submissions

Invariants

membership is the unit of participation

gameplay history attaches to membership, not account directly

suspension/removal affects future actions, not historical integrity

5.2 Alias Record
Purpose

Represent an alias state within a competition participation context.

Conceptual fields

alias record identity

membership reference

alias value

active flag

start/end validity

reason for change

cycle/season context if applicable

Relationships

membership has many alias records over time

one alias record may be the current active alias

Invariants

alias history must be preserved

current alias is a resolved state, not necessarily the only stored alias fact

alias belongs to membership context, not account

5.3 Membership State Snapshot / Derived State
Purpose

Represent current operational state for quick access.

Typical conceptual state dimensions

active/inactive

bankrupt/not bankrupt

partially protected / fully protected

attack eligibility

current score

current rank snapshot if cached

visible identity flags

Invariants

snapshot state must remain derivable from authoritative domain records

snapshot is not a replacement for historical truth

6) Score & Financial Trace Entities
6.1 Ledger Entry
Purpose

Authoritative financial trace of score changes.

Conceptual fields

ledger entry identity

membership reference

competition/season/cycle scope

entry type

amount

direction

before/after balances if tracked

source event reference

source type

reason/label

created timestamp

actor/source category

Relationships

many entries belong to one membership

entries may reference attacks, quiz outcomes, purchases, distributions, admin adjustments, rewards

Invariants

every score mutation must correspond to ledger

ledger entries are immutable in principle; corrections should be new entries, not silent rewrites

6.2 Score Snapshot / Balance Summary
Purpose

Represent current usable score state.

Conceptual fields

membership reference

current balance

updated timestamp

optional derived metrics

Invariants

balance is derived from ledger truth

balance may be stored for performance, but ledger remains authoritative

7) Attack & Protection Entities
7.1 Attack Attempt
Purpose

Represent one attack action.

Conceptual fields

attack identity

attacker membership reference

target membership reference

guessed real identity reference

guessed alias payload

cycle/season scope

execution timestamp

outcome state

reward amount

penalty amount

resolution summary

blocking reason if any

applied modifier summary

Relationships

one membership attacks many times

one membership may be targeted many times

attack references cycle and season context

attack may generate ledger entries

attack may generate audit events and notifications

Invariants

attack attempt is a first-class event regardless of success/failure

blocked attempts may still need history

ordering by timestamp is domain-significant

7.2 Protection State Record
Purpose

Represent protection status changes and reasons.

Conceptual fields

protection record identity

membership reference

state type

start timestamp

end timestamp if bounded

source attack/reference

reason

cycle/season scope

Relationships

membership can have many protection records over time

Invariants

protection is stateful and historically meaningful

full protection and partial protection should be distinguishable

7.3 Attack Exposure / Target Saturation Tracking
Purpose

Track how many effective successful attacks have been applied to a target under current rules.

Conceptual fields

membership reference

relevant cycle/season scope

effective successful attack count

current reward stage or modifier stage

max allowed attack stage

terminal protection reached flag

Invariants

this concept must exist, whether as derived or materialized state

reward decay and full protection depend on it

7.4 Bankruptcy State Record
Purpose

Represent bankruptcy activation and recovery.

Conceptual fields

bankruptcy record identity

membership reference

triggered at

trigger reason/reference

active until

resolved at

cycle context

visible identity release state

Relationships

membership may have many bankruptcy records over time

Invariants

bankruptcy is historical, not just a boolean

bankruptcy visibility effects must be explainable and time-bounded

8) Store / Item / Reward System Entities
8.1 Item Definition
Purpose

Master definition of an item type.

Conceptual fields

item definition identity

name

description

rarity

state

category

acquisition type

usage type

effect model reference

visibility rules

purchase rules

usage rules

stacking rules

expiry rules

scope applicability

Relationships

one item definition may appear in store

one item definition may be granted through rewards

one item definition may have many ownership records

Invariants

item definition is not player ownership

item definition must be reusable

item definition should not encode player-specific state

8.2 Item Effect Definition / Effect Payload
Purpose

Represent configurable effect logic at domain level.

Conceptual fields

effect identity

effect type

effect parameters

target scope

duration semantics

stacking behavior

trigger semantics

Relationships

one item definition may have one or many effect definitions

Invariants

effects are data-driven conceptually

effect payload must be structured, not arbitrary ad hoc logic blobs without schema discipline

8.3 Store Listing / Availability Rule
Purpose

Represent item availability for purchase in a given scope.

Conceptual fields

listing identity

item definition reference

competition/season/cycle scope

status

price definition

eligibility constraints

stock/limit constraints

visibility rules

Relationships

store listing points to item definition

Invariants

store listing is not item definition

item may exist without being listed in store

8.4 Owned Item / Inventory Record
Purpose

Represent a participant owning an item.

Conceptual fields

ownership identity

membership reference

item definition reference

source type

source reference

quantity

state

uses remaining

acquired at

expires at

activated at

consumed at

Relationships

membership has many owned items

owned item references item definition

owned item may generate effect activation history

Invariants

inventory is participant-state

ownership history should remain available even after use/expiry where required

8.5 Item Activation / Usage Record
Purpose

Track actual use/activation of an owned item.

Conceptual fields

activation identity

owned item reference

membership reference

target reference if any

activation time

result state

resulting effect summary

denial reason if applicable

Invariants

usage is distinct from ownership

usage may fail and still need tracking

8.6 Reward Definition / Reward Outcome Model
Purpose

Represent reward logic independent of store purchase.

Conceptual fields

reward definition identity

type

content model

rules

distribution model

Invariants

rewards may grant score, items, boxes, or combinations

reward definitions should not be conflated with reward grants

8.7 Reward Grant
Purpose

Represent a reward actually granted to a participant.

Conceptual fields

reward grant identity

membership reference

reward definition or source reference

granted at

state

claimed/opened state if applicable

expiry

Relationships

may lead to ledger entries, owned items, or box outcomes

Invariants

grant event must be historically traceable

8.8 Box Outcome Record
Purpose

Persist the result of opening a box/reward container.

Conceptual fields

box opening identity

reward grant reference or owned reward reference

opened by membership

opened at

resolved outcome type

resolved content references

ledger/item references created

Invariants

opened result must be stable once resolved

box resolution must not be re-randomized on repeated retrieval

8.9 Distribution Definition / Execution
Purpose

Represent scheduled or manual distributions.

Conceptual fields

distribution identity

source scope

execution type

target scope

content definition

scheduled time

execution state

executed at

result summary

Relationships

distribution may grant ledger entries, items, rewards

Invariants

distributions are first-class domain objects

execution results must be inspectable

9) Question Bank & Quiz Delivery Entities
9.1 Question Group
Purpose

Reusable logical collection of questions.

Conceptual fields

group identity

title

description

status

classification metadata

created/updated info

Relationships

one group has many questions

Invariants

group is reusable

session use of group does not collapse into group identity

9.2 Question Definition
Purpose

Reusable question content.

Conceptual fields

question identity

group reference

question type

prompt

option set

correct answer model

score value

difficulty

category

media reference or external URL

status

Relationships

belongs to question group

may be used by many sessions

Invariants

question definition is authoring content, not player attempt state

participant-facing contracts must hide correct answer until allowed

9.3 Quiz Session
Purpose

Actual playable scheduled question event.

Conceptual fields

session identity

competition/season/cycle scope

session type

start/end time

state

participation rules

scoring rules

source group or explicit question set

visibility rules

Relationships

one session has one or many session questions

one session has many participant submissions

Invariants

session behavior is independent from question authoring object lifecycle

session timing is authoritative

9.4 Session Question / Delivered Question State
Purpose

Represent the question as used within a specific session.

Conceptual fields

session question identity

session reference

source question reference

delivery order

effective score value

effective media reference

effective wording snapshot if snapshotting is required

Invariants

conceptually useful to distinguish source question from delivered session question

protects against future source edits changing past session meaning

9.5 Participant Answer Submission
Purpose

Represent one participant’s answer attempt.

Conceptual fields

answer submission identity

membership reference

session reference

session question reference

submitted answer payload

submitted at

evaluated state

correctness result

points awarded

evaluation timestamp

Invariants

answer submissions must be traceable

score awarded must map into ledger

multiple-attempt policy must be represented explicitly if allowed

10) Notification & Messaging Entities
10.1 Notification
Purpose

Represent a user-facing alert.

Conceptual fields

notification identity

recipient account or membership context

type

message

read state

created timestamp

related reference

delivery priority/category

Invariants

notifications are derived from events/actions

notification history may need retention

11) Audit & Settings Entities
11.1 Audit Event
Purpose

Represent operational and administrative history.

Conceptual fields

audit event identity

actor reference

actor type

subject entity reference

event type

summary message

reason

before snapshot summary if relevant

after snapshot summary if relevant

created timestamp

related references

Invariants

audit must remain human-readable

audit is not the same as ledger

admin mutations must create audit events

11.2 Settings Scope
Purpose

Represent configuration scope boundaries.

Possible scopes:

global platform

competition

season

cycle

item/store context if needed

Invariants

settings must resolve by scope precedence

scope semantics must be stable and deterministic

11.3 Setting Definition
Purpose

Represent configurable option metadata.

Conceptual fields

setting identity

key

category

type

allowed range/options

default value

description

Invariants

setting definitions are metadata, not current values

11.4 Setting Value / Effective Setting Assignment
Purpose

Represent actual chosen value at a scope.

Conceptual fields

setting assignment identity

setting definition reference

scope type

scope reference

assigned value

created/updated metadata

actor reference

Invariants

effective setting resolution should be computable

settings history should be recoverable for audit if required

12) Media / Import / Export Entities
12.1 Media Asset
Purpose

Represent uploaded or externally linked media.

Conceptual fields

media identity

storage type

storage reference or URL

media type

ownership/source context

status

created timestamp

Relationships

may be attached to questions

may be attached to import/export artifacts

Invariants

media identity is independent from question/entity identity

broken media should not corrupt the question object itself

12.2 Import Job
Purpose

Represent spreadsheet or bulk import operation.

Conceptual fields

import job identity

file reference

actor reference

import type

status

validation summary

created timestamp

completed timestamp

Invariants

imports should be traceable as jobs

failures should be recoverable and reviewable

12.3 Export Artifact
Purpose

Represent generated exports.

Conceptual fields

export identity

export type

source scope

file reference

generated at

actor reference

expiry if needed

13) Core Relationship Summary

At the highest level:

Account → has many Memberships

Competition → has many Memberships

Competition → has many Seasons

Season → has many Cycles

Membership → has many Alias Records

Membership → has many Ledger Entries

Membership → has many Attack Attempts as attacker and as target

Membership → has many Owned Items

Membership → has many Answer Submissions

Membership/Account → has many Notifications

Question Group → has many Question Definitions

Quiz Session → has many Session Questions

Quiz Session → has many Answer Submissions

Item Definition → has many Store Listings

Item Definition → has many Owned Items

Distribution → may create Ledger Entries, Reward Grants, Owned Items

Audit Event → references actors and subject entities

Setting Definition → has many Setting Assignments across scopes

14) Conceptual Read Models That Should Exist

Even if physically implemented later in different ways, the platform conceptually needs read models for:

Current competition home view

Current participant state summary

Leaderboard view

Participant profile view

Attack preview view

Store catalog view

Inventory view

Current active quiz sessions view

Notification center view

Admin dashboard summary

Audit exploration view

Effective settings view

These read models may aggregate from multiple canonical entities, but the canonical entities must remain conceptually separate.

15) Core Domain Invariants Summary

These are the strongest foundation rules for the schema:

A platform user is an Account.

A competition participant is a Membership.

A visible in-game identity is an Alias, not an Account name.

Score state is explained by Ledger Entries.

Gameplay history is explained by Attack Attempts, Answer Submissions, Owned Items, and Audit Events.

Administrative truth is explained by Audit Events.

Reusable content is represented by Question Definitions and Item Definitions.

Runtime participation state is represented by Quiz Sessions, Owned Items, Protection/Bankruptcy state, and Membership state.

Configurability is represented by Setting Definitions plus Scoped Setting Assignments.

Time structure is represented by Competition → Season → Cycle.

16) What Must Not Be Collapsed in the Final Design

To keep the foundation strong, the final implementation must not conceptually collapse these into one thing:

Account + Membership

Membership + Alias

Balance + Ledger

Attack result + Attack event history

Item definition + owned item

Reward grant + box outcome

Question definition + session question delivery

Quiz answer + ledger reward

Audit log + business entity tables

Setting definition + setting value

Competition lifecycle + season lifecycle + cycle lifecycle

17) Final Core Guidance

If the implementation preserves the principles in these two specs, the platform will remain strong and extensible because it will be built on:

clear identity boundaries

explicit state boundaries

auditable mutations

reusable content models

configurable scoped rules

temporally correct gameplay structure

If the implementation shortcuts these boundaries for speed, the system will become fragile fast, especially in:

attacks

scoring

items

settings

admin overrides

session history