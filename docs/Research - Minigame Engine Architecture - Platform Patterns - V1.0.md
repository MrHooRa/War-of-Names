# Research: Minigame Engine Architecture -- Platform Patterns

**Version:** 1.0
**Date:** 2026-03-30
**Purpose:** Technical architecture analysis of how major platforms build minigame engines -- the underlying systems/frameworks that power multiple different games within a single platform. Real patterns from production systems, not theory.

---

## Table of Contents

1. [Roblox -- Platform-Scale Game Engine](#1-roblox)
2. [Discord Activities -- Embedded Games SDK](#2-discord-activities)
3. [Telegram Mini Apps / Mini Games](#3-telegram-mini-apps)
4. [WeChat Mini Games](#4-wechat-mini-games)
5. [Facebook Instant Games](#5-facebook-instant-games)
6. [Supercell -- Multi-Mode Single-App Architecture](#6-supercell)
7. [Jackbox Games -- Party Game Engine](#7-jackbox-games)
8. [Game Frameworks & Engine Patterns](#8-game-frameworks--engine-patterns)
9. [Lobby Systems Architecture](#9-lobby-systems-architecture)
10. [Leaderboard Systems](#10-leaderboard-systems)
11. [Key Takeaways for War of Names](#11-key-takeaways-for-war-of-names)

---

## 1. Roblox

### Architecture Overview

Roblox is a C++ engine with an embedded Luau (typed Lua) scripting VM. The key insight: Roblox is NOT a game -- it is a **game hosting platform** where thousands of independent games ("Experiences") share a common infrastructure layer.

### Shared Infrastructure vs. Per-Game Logic

**Shared (Platform-Provided):**

| Service | Description |
|---------|-------------|
| **DataStoreService** | Persistent key-value storage (GlobalDataStore for general data, OrderedDataStore for leaderboards) |
| **MessagingService** | Cross-server pub/sub messaging between game instances |
| **Matchmaking** | Evaluates up to 4B join combinations/second; supports custom matchmaking signals (e.g., skill rating) |
| **Currency (Robux)** | Platform-wide virtual currency with developer exchange |
| **Identity & Auth** | Platform accounts, avatar system, friend graphs |
| **Physics Engine** | Shared rigid body physics simulation |
| **Networking** | Client-server replication, remote events/functions |
| **Moderation** | Chat filtering, content moderation, reporting |
| **Analytics** | Telemetry, retention metrics, funnel tracking |
| **Asset CDN** | Meshes, textures, audio served from edge CDN |

**Per-Game (Developer-Controlled):**

| Component | Description |
|-----------|-------------|
| **Game Logic** | Written in Luau scripts, completely custom per experience |
| **Level Design** | 3D world built in Roblox Studio |
| **UI** | Custom ScreenGui / SurfaceGui elements |
| **Game Rules** | Win conditions, scoring, progression -- all custom |
| **Monetization** | Developer-defined game passes, dev products |

### DataStore API (Key for Leaderboards & Persistence)

```
-- GlobalDataStore (general purpose)
DataStoreService:GetDataStore(name) -> GlobalDataStore
  :GetAsync(key) -> value
  :SetAsync(key, value)
  :UpdateAsync(key, transformFunction)
  :IncrementAsync(key, delta) -> newValue
  :RemoveAsync(key)

-- OrderedDataStore (sorted, for leaderboards)
DataStoreService:GetOrderedDataStore(name) -> OrderedDataStore
  :GetSortedAsync(ascending, pageSize, minValue?, maxValue?) -> DataStorePages
  -- Values MUST be integers
  -- No versioning, no metadata
  -- pageSize: max 100 per page
  :SetAsync(key, integerValue)
  :IncrementAsync(key, delta) -> newValue
```

**Rate Limiting:** Request budget system per request type. Exceeding budget causes throttling. Developers must monitor via `GetRequestBudgetForRequestType()`.

### Per-Game Isolation Model

Each script gets a new global table with `__index` pointing to the builtin global table. This sandboxes builtin globals while allowing script-local globals. All scripts are isolated from each other.

Thread identity determines API permissions -- scripts of different identity levels run in different VMs.

**Parallel Luau:** Multiple VMs, each representing an Actor. Scripts within an Actor execute on that VM, enabling true parallel execution while maintaining isolation.

### Server-Client Model

- Server is source of truth for all game state
- Clients send input, server processes and replicates
- Server authority (in beta) shifts critical gameplay truth to server
- Delta updates instead of full state transmission
- Client-side prediction with server reconciliation
- Configurable tick rates (typically 30 updates/second)

### Infrastructure Scale

- Cellular infrastructure with cloud bursting for peak demand
- Regionally distributed game servers to minimize latency
- Edge proxies for reducing round-trip times
- CDN for assets (avatars, textures, maps)

---

## 2. Discord Activities

### Architecture Overview

Activities are **web applications** rendered inside Discord clients through a **sandboxed iframe**. The `@discord/embedded-app-sdk` handles all communication between the Activity and Discord via `postMessage`.

### iframe Sandbox Model

```
Activity (your web app)
    |
    | postMessage protocol
    |
Discord Client (iframe host)
    |
    | proxy through discordsays.com
    |
Your Backend Server
```

All network requests route through `https://<app_id>.discordsays.com`. Direct external domain requests are blocked (CSP enforcement). IP obfuscation is automatic.

### SDK Communication Protocol

Message format:
```json
[FRAME, {"evt": "EVENT_NAME", "data": {...}, "nonce": "unique-id"}]
```

- First element: Message type (FRAME or CLOSE)
- `nonce`: Unique identifier for request/response correlation
- Close message: `[CLOSE, {"message": "string", "code": number}]`

### Session Lifecycle (5 Stages)

```
1. INITIALIZATION
   iframe loads with query params:
   - frame_id (unique iframe instance)
   - instance_id (activity session ID)
   - platform (desktop/web/mobile)

2. HANDSHAKE
   SDK calls ready()
   Resolves when: [FRAME, {evt: 'READY', ...}] received

3. AUTHORIZATION (OAuth2 Split-Flow)
   Client: authorize() -> returns auth code
   Server: exchanges code for access_token (using client_secret)
   Client: authenticate(access_token)

   This prevents exposing secrets in browser context.

4. ACTIVE STATE
   Commands via: discordSdk.commands.*
   Events via: subscription system

5. DISCONNECTION
   User close, errors, or Activity-initiated [CLOSE]
```

### URL Mapping / Proxy System

Configured in Discord Developer Portal:

| Prefix | Target | Routes To |
|--------|--------|-----------|
| `/` | `example.com` | `https://example.com/[path]` |
| `/api` | `api.example.com` | `https://api.example.com/[path]` |

SDK provides `patchUrlMappings()` to rewrite URLs in `fetch`, `WebSocket`, and `XMLHttpRequest.prototype.open`.

Proxy uses Cloudflare Workers. Supports HTTP/S, WebSocket. WebTransport in progress. WebRTC not supported.

### Event System

| Event | Data |
|-------|------|
| `voiceStateUpdate` | User voice state changes |
| `speakingUpdate` | User speaking status |
| `ACTIVITY_LAYOUT_MODE_UPDATE` | PiP, grid mode changes |
| `ORIENTATION_UPDATE` | Device orientation |
| `THERMAL_STATE_UPDATE` | Mobile thermal state |

### Rich Presence

```json
{
  "type": 0,          // 0=Playing, 1=Streaming, 2=Listening
  "state": "...",
  "details": "...",
  "timestamps": {"start": unix, "end": unix},
  "assets": {
    "large_image": "url",
    "large_text": "tooltip",
    "small_image": "url"
  },
  "party": {"size": [current, max]}
}
```

### State Management: Developer Responsibility

Discord does NOT provide built-in state sync or matchmaking. Developers must bring their own game server. Common approach: **Colyseus** or **Playroom Kit** for room-based state synchronization over WebSocket.

### Security Model

- iframe sandbox: No DOM access to Discord client, no cookie sharing
- CSP: Restricts network, inline scripts, mixed content
- Cookie isolation: `SameSite=None`, `Partitioned`, `Secure` required
- Server-side verification of user identity via OAuth2 (never trust client data)

---

## 3. Telegram Mini Apps

### Architecture Overview

Mini Apps are standard web applications displayed in Telegram's WebView. They communicate with the Telegram client via a JavaScript bridge.

```
Your Web App (HTML/CSS/JS)
    |
    | Telegram Bridge (postMessage)
    |
Telegram Client WebView
    |
    | Bot API
    |
Your Backend Server <-> Telegram Bot API
```

Every Mini App requires a Telegram Bot as its parent. No standalone Mini Apps exist.

### Initialization

```html
<script src="https://telegram.org/js/telegram-web-app.js"></script>
```

Creates `window.Telegram.WebApp` object.

### Authentication -- initData Validation

**Client receives:**
```
query_id=<session_id>
&user={"id":123,"first_name":"Salman",...}
&auth_date=<unix_timestamp>
&hash=<HMAC-SHA-256 signature>
&signature=<Ed25519 signature>
```

**Server-side HMAC-SHA-256 verification:**
```python
secret_key = HMAC_SHA256(bot_token, "WebAppData")
data_check_string = "auth_date=<val>\nquery_id=<val>\nuser=<val>"
# Fields sorted alphabetically, joined with newlines
valid = HEX(HMAC_SHA256(data_check_string, secret_key)) == received_hash
```

**Third-party Ed25519 verification** (for services without bot token):
- Construct: `bot_id:WebAppData\nauth_date=<val>\n...`
- Verify against Telegram's public key

### Shared Platform Services

| Service | API |
|---------|-----|
| **Auth** | `initData` with HMAC-SHA-256 / Ed25519 validation |
| **Payments** | `openInvoice(url, callback)` -> Telegram Stars |
| **Cloud Storage** | `CloudStorage.setItem/getItem/removeItem` -- 1024 items, cloud-synced |
| **Device Storage** | `DeviceStorage` -- 5 MB local |
| **Secure Storage** | `SecureStorage` -- 10 items, OS-encrypted (Keychain/Keystore) |
| **Haptic Feedback** | `impactOccurred()`, `notificationOccurred()`, `selectionChanged()` |
| **Biometrics** | `BiometricManager.authenticate()` |
| **QR Scanner** | `showScanQrPopup(params, callback)` |
| **Device Sensors** | Accelerometer, Gyroscope, DeviceOrientation |
| **Location** | `LocationManager.getLocation()` |

### UI Controls

```javascript
// Bottom action button
Telegram.WebApp.MainButton.setText("Play");
Telegram.WebApp.MainButton.show();
Telegram.WebApp.MainButton.onClick(handler);

// Back button
Telegram.WebApp.BackButton.show();
Telegram.WebApp.BackButton.onClick(handler);

// Popups
Telegram.WebApp.showPopup({
  title: "...",        // 0-64 chars
  message: "...",      // 1-256 chars
  buttons: [           // 1-3 buttons
    {id: "ok", type: "default", text: "OK"},
    {id: "cancel", type: "cancel"}
  ]
});

// Theming -- CSS variables
var(--tg-theme-bg-color)
var(--tg-theme-text-color)
var(--tg-theme-button-color)
var(--tg-color-scheme)  // "light" or "dark"
```

### Event System

Key events: `themeChanged`, `viewportChanged`, `mainButtonClicked`, `backButtonClicked`, `invoiceClosed` (with status: `"paid"|"cancelled"|"failed"|"pending"`), `popupClosed` (with `button_id`).

### Leaderboard Pattern

Telegram does NOT provide built-in leaderboards. Developers must:
1. Store scores in their own database
2. Build leaderboard UI within the Mini App
3. Use `setGameScore` Bot API method for inline game messages

### Data Transmission

`sendData(data)` -- up to 4096 bytes to the parent bot. Closes the Mini App after sending.

### Launch Modes

7 launch modes: keyboard button, inline button, menu button, main Mini App, direct link (`/appname?startapp=param`), inline mode, attachment menu. Each has different capabilities.

---

## 4. WeChat Mini Games

### Architecture Overview

WeChat Mini Games run inside WeChat's JavaScript runtime. The framework provides a two-layer architecture:

```
Layer 1: Hardware/OS (iOS, Android)
Layer 2: WeChat Runtime
  - Android: V8 JavaScript Engine
  - iOS: JavaScriptCore Engine
Layer 3: WeChat APIs (wx.* namespace)
Layer 4: Game Code (JavaScript/TypeScript)
```

### Runtime Environment

- Games execute in a JavaScript sandbox within WeChat
- Canvas/WebGL rendering for graphics
- Resource caching is segmented -- resources between different users and different games never conflict
- Package size limits with subpackage loading for optimization

### Network APIs

```javascript
// HTTP requests
wx.request({url, data, method, header, success, fail})

// WebSocket
wx.connectSocket({url, protocols})
wx.onSocketMessage(callback)
wx.sendSocketMessage({data})

// File operations
wx.getFileSystemManager()
  .readFile({filePath, encoding, success})
  .writeFile({filePath, data, encoding})
  .rename(), .unlink(), .mkdir()
```

### Shared Services

| Service | Description |
|---------|-------------|
| **Login/Auth** | WeChat account-based, automatic identity |
| **Social ("Relationship Chain")** | Friend list access, group sharing |
| **Virtual Payments** | WeChat Pay integration |
| **Leaderboards/Rankings** | Built-in ranking lists |
| **Share/Forward** | Dynamic messages to chats/groups |
| **Advertising** | Banner ads, rewarded video ads |
| **Game Circle** | Social gaming features |

### Resource Management

- UUID-based asset tracking with dependency management
- AssetsBundle for modular resource loading
- Built-in resource cache system
- CDN upload with version control
- Subpackage loading (independent sub-packages for on-demand installation)

### Game Registration

Developers register on the Mini Program Registration Page, select "Game" as service category, get an AppID, and submit for review. Games run within WeChat -- no standalone installation.

---

## 5. Facebook Instant Games

### Architecture Overview

Facebook Instant Games are HTML5 games embedded within Facebook Messenger and News Feed. The `FBInstant` SDK provides a JavaScript API for platform integration.

### SDK Lifecycle

```javascript
// 1. Initialize
FBInstant.initializeAsync().then(() => {
  // 2. Report loading progress
  FBInstant.setLoadingProgress(50);

  // 3. Start game
  FBInstant.startGameAsync().then(() => {
    // Game is now visible and playable
  });
});
```

### Player API

```javascript
FBInstant.player.getID()           // Unique player ID
FBInstant.player.getName()         // Display name
FBInstant.player.getPhoto()        // Profile picture URL

// Persistent data
FBInstant.player.getDataAsync(['score', 'level'])
  .then(data => { /* {score: 100, level: 5} */ });
FBInstant.player.setDataAsync({score: 200, level: 6});

// Signed player info (for server verification)
FBInstant.player.getSignedPlayerInfoAsync('nonce')
  .then(result => {
    result.getPlayerID();    // verified player ID
    result.getSignature();   // HMAC signature for server
  });

// Social graph
FBInstant.player.getConnectedPlayersAsync()
  .then(players => {
    players.forEach(p => {
      p.getID();     // player ID
      p.getName();   // display name
      p.getPhoto();  // profile picture
    });
  });
```

### Context API (Social Multiplayer)

The "context" represents WHERE the game is being played (a specific Messenger conversation, a Facebook post, etc.).

```javascript
FBInstant.context.getID()      // Current context ID (null = solo)
FBInstant.context.getType()    // "SOLO" | "THREAD" | "GROUP" | "POST"

// Switch to playing with a friend
FBInstant.context.switchAsync(contextId);

// Choose friends to play with
FBInstant.context.chooseAsync({
  filters: ['NEW_CONTEXT_ONLY'],
  minSize: 2,
  maxSize: 4
});

// Create new context with specific player
FBInstant.context.createAsync(playerId);

// Get players in current context
FBInstant.context.getPlayersAsync()
  .then(players => { /* ContextPlayer objects */ });
```

### Leaderboard API

Leaderboards are a **hosted service** provided by Facebook. Each game creates named leaderboards.

```javascript
// Get leaderboard reference
FBInstant.getLeaderboardAsync('high_scores')
  .then(leaderboard => {
    // Set score
    leaderboard.setScoreAsync(100, 'extra_data')
      .then(entry => {
        entry.getScore();       // 100
        entry.getRank();        // player's rank
        entry.getExtraData();   // 'extra_data'
        entry.getPlayer();      // LeaderboardPlayer
      });

    // Get my score
    leaderboard.getPlayerEntryAsync();

    // Get top entries
    leaderboard.getEntriesAsync(10, 0)  // count, offset
      .then(entries => {
        entries.forEach(e => {
          e.getScore();
          e.getRank();
          e.getPlayer().getName();
          e.getPlayer().getPhoto();
        });
      });

    // Get connected players' entries
    leaderboard.getConnectedPlayerEntriesAsync(10, 0);

    // Leaderboard metadata
    leaderboard.getEntryCountAsync();
    leaderboard.getName();
  });
```

Leaderboards can be **context-specific** (scoped to a conversation) or **global** (across all players).

### Key Data Models

```typescript
interface LeaderboardEntry {
  getScore(): number;
  getFormattedScore(): string;
  getTimestamp(): number;
  getRank(): number;
  getExtraData(): string;
  getPlayer(): LeaderboardPlayer;
}

interface LeaderboardPlayer {
  getName(): string;
  getPhoto(): string;
  getID(): string;
}

interface ConnectedPlayer {
  getID(): string;
  getName(): string;
  getPhoto(): string;
}

interface ContextPlayer extends ConnectedPlayer {
  // Additional context-specific data
}
```

### Payments API

```javascript
FBInstant.payments.getCatalogAsync()
  .then(catalog => {
    catalog.forEach(product => {
      product.getTitle();
      product.getProductID();
      product.getDescription();
      product.getPrice();
      product.getPriceCurrencyCode();
    });
  });

FBInstant.payments.purchaseAsync({productID: 'gems_100'})
  .then(purchase => {
    purchase.getPaymentID();
    purchase.getProductID();
    purchase.getPurchaseToken();  // for server verification
    purchase.getSignedRequest();  // HMAC-signed for validation
  });

// Consume purchase (required for consumable items)
FBInstant.payments.consumePurchaseAsync(purchaseToken);
```

---

## 6. Supercell

### Multi-Mode Architecture

Supercell games (Clash Royale, Brawl Stars, Clash of Clans) run **multiple game modes** within a single app. Each mode has different rules but shares:

**Shared Across Modes:**
- Account system (Supercell ID)
- Currency (Gems, Gold, Star Points)
- Card/character collection and progression
- Trophy/ranking system
- Friend graph and social features
- Chat system
- Clan/team infrastructure
- Season pass progression

**Per-Mode:**
- Win conditions and rules
- Map/arena configuration
- Team size (1v1, 2v2, 3v3, 5v5)
- Mode-specific rewards
- Matchmaking parameters

### Cross-Game Social Platform (Supercell ID)

Supercell built a unified social platform connecting hundreds of millions of gamers across all five games. Architecture built by a team of just two engineers.

**Data Model -- Hierarchical Key-Value Store with CDC:**

```
Top-level keys = Topics (clients subscribe to these)
Values = map(string, map(string, string))  -- two-layer nested maps
```

Each data source controls its own timestamps. Clients discard updates older than cached values (idempotent operations).

**This single abstraction unifies:**
- Chat messages
- Player presence
- Friend state
- Team formation

### Real-Time Communication Pipeline

```
Game Client
    |
    | HTTP/2 + Protocol Buffers
    |
Proxy Servers
    |  (maintain subscriptions, route to correct shard)
    |
Event Routing Servers
    |  (topics sharded across servers, primary + backup)
    |
ScyllaDB Cloud (synchronous persistence)
```

**Key design decisions:**
- All load balancing at TCP level (same HTTP/2 connection -> same socket)
- Events persisted synchronously in ScyllaDB BEFORE broadcasting
- Primary shard maintains sequence numbers to detect lost messages
- Backup shard forwards without sequence numbers
- Server restarts trigger client-side state refresh

### Concrete Data Models

**Chat Messages:**
```
<room_ID> -> <timestamp_UUID> -> message: "hi there"
                               -> metadata: {...}
                               -> reactions: {...}
```

**Player Presence:**
```
<player_ID> -> "presence" -> weapon: sword
                           -> level: 29
                           -> status: in_battle
```

### Matchmaking

Supercell uses trophy-based matchmaking with progressive flexing:
- Clash Royale: Trophies determine matchmaking tier
- Brawl Stars: Per-brawler trophy count for matchmaking
- Multiple game modes accessible via Game Mode Switcher
- Matchmaking criteria differ per mode but share underlying infrastructure

### Infrastructure

- AWS-based cloud infrastructure
- Globally distributed servers across multiple regions
- Strategic placement to reduce lag by connecting players to nearest data center
- ScyllaDB for real-time event persistence (handles numerous small writes with low latency)

---

## 7. Jackbox Games

### Architecture Overview

Jackbox is a **party game engine** hosting multiple distinct games within "Party Packs." The architecture separates the **host** (TV/PC showing the game) from **players** (phones/tablets as controllers).

```
Host (Console/PC)
    |
    | Game logic, rendering, state management
    |
Jackbox Servers (WebSocket Broker)
    |
    | WebSocket connections
    |
Player Devices (jackbox.tv in browser)
```

### Room Code Architecture

```
1. Host starts a game
2. Server generates 4-letter Room Code (e.g., "ABCD")
3. Room Code displayed on host screen
4. Players navigate to jackbox.tv, enter Room Code
5. Broker maps Room Code -> specific game session
6. First player to join = VIP (can start game)
```

The **Broker** manages Rooms:
- Clients identified by "Participant Name"
- Rooms identified by "Room Code"
- On create request: Broker generates code, returns to host
- Room Code is temporary, single-use, session-scoped

### WebSocket Protocol

All Jackbox games share a consistent JSON message structure:

```json
{
  "seq": 42,           // sequence identifier
  "opcode": "action",  // operation type
  "body": { ... }      // game-specific payload
}
```

- Text data (answers, prompts): JSON messages
- Binary data (drawings): Raw WebSocket binary frames
- Two-way: Server pushes prompts/instructions to players; players submit answers/actions to server

### Per-Game Rule Engine

Each game in a Party Pack defines:
- Input types (text, drawing, selection, voting)
- Round structure and timing
- Scoring rules
- Elimination/progression logic
- UI prompts sent to player devices

The shared infrastructure handles:
- Room creation and player management
- WebSocket message routing
- VIP designation and game start
- Timer management
- Score aggregation display

### State Synchronization Pattern

```
Player submits answer on phone
    -> WebSocket to Jackbox server
    -> Server processes (validates, scores)
    -> Updates game state
    -> Broadcasts to host screen (display update)
    -> Sends next prompt to player devices
```

Handlers override `ServerMessageReceived` and process relevant opcodes. The underlying protocol is consistent; game-specific logic lives in opcode handlers.

---

## 8. Game Frameworks & Engine Patterns

### 8.1 Entity-Component-System (ECS)

ECS separates game objects into three concepts:

```
Entity: Just an ID (integer)
    Has: Component[] (data containers)

Component: Pure data, no behavior
    Examples: Position{x,y}, Health{current,max}, Velocity{dx,dy}

System: Logic that operates on entities with specific component sets
    Example: MovementSystem queries entities with (Position + Velocity)
             PhysicsSystem queries entities with (Position + Velocity + Mass)
```

**Key Principles:**
- Composition over inheritance
- Behavior changes at runtime by adding/removing components
- No ambiguity from deep inheritance hierarchies
- Data stored in tightly packed typed arrays (cache-friendly)

**For Multiplayer:**

The Entity-Component-Worker (ECW) pattern extends ECS:
- Components specify which worker type handles updates
- Game world can scale to millions of entities across thousands of workers on hundreds of servers
- Developer writes code as if single-player ECS; the framework distributes automatically

**Practical Application for Minigames:**
```
// Each minigame type registers its components
GameRegistry.register("quiz", {
  components: [QuizQuestion, Timer, Score, PlayerAnswer],
  systems: [QuestionRotationSystem, TimerSystem, ScoringSystem]
});

GameRegistry.register("attack", {
  components: [AttackTarget, Guess, Protection, Score],
  systems: [AttackResolutionSystem, ProtectionSystem, ScoringSystem]
});

// Shared systems (ScoringSystem) reused across game types
```

### 8.2 State Machine Patterns for Game Sessions

**Basic FSM (Enum + Switch):**

```
States: LOBBY -> STARTING -> PLAYING -> ROUND_END -> GAME_END -> RESULTS

Transitions:
  LOBBY + all_ready -> STARTING
  STARTING + countdown_done -> PLAYING
  PLAYING + round_timer_expired -> ROUND_END
  ROUND_END + more_rounds -> PLAYING
  ROUND_END + final_round -> GAME_END
  GAME_END + results_shown -> RESULTS
```

**Gang of Four State Pattern (Polymorphic):**

```typescript
interface GameState {
  enter(session: GameSession): void;
  handleInput(session: GameSession, input: PlayerInput): void;
  update(session: GameSession, deltaTime: number): void;
  exit(session: GameSession): void;
}

class LobbyState implements GameState {
  enter(session) { session.broadcastLobbyInfo(); }
  handleInput(session, input) {
    if (input.type === 'READY' && session.allReady()) {
      session.transition(new StartingState());
    }
  }
}

class PlayingState implements GameState {
  private timer: number;
  enter(session) { this.timer = session.config.roundDuration; }
  update(session, dt) {
    this.timer -= dt;
    if (this.timer <= 0) session.transition(new RoundEndState());
  }
}
```

**Key advantage:** State-specific data (timers, counters) belongs to the state object, not the session.

**Hierarchical State Machines:**
```
GameSession
  |-- PreGame
  |     |-- WaitingForPlayers
  |     |-- Countdown
  |-- InGame
  |     |-- RoundActive
  |     |     |-- QuestionPhase
  |     |     |-- AnswerPhase
  |     |     |-- RevealPhase
  |     |-- RoundTransition
  |-- PostGame
        |-- Results
        |-- Rematch
```

Substates delegate unhandled inputs to parent states (chain of responsibility).

**Concurrent State Machines:**
```
// Orthogonal state machines running in parallel
GameSession {
  gamePhase: GamePhaseStateMachine,     // LOBBY -> PLAYING -> ENDED
  timerState: TimerStateMachine,         // RUNNING -> PAUSED -> EXPIRED
  connectionState: ConnectionStateMachine // CONNECTED -> RECONNECTING -> DROPPED
}
```

Avoids exponential state explosion (n x m states become n + m).

**Pushdown Automata (State Stack):**
```
Stack: [PlayingState]
  -> Player opens store: push(StoreState)
Stack: [PlayingState, StoreState]
  -> Player closes store: pop()
Stack: [PlayingState]  // returns to exact previous state
```

### 8.3 Plugin/Registry Architecture

**Pattern from Unreal Engine 5 Modular Game Features:**

```
Core Game (knows nothing about plugins)
    |
    | Plugin Interface
    |
Plugin Manager / Registry
    |
    |-- Plugin: "QuizGame"  (registers: rules, UI, scoring)
    |-- Plugin: "AttackGame" (registers: rules, UI, scoring)
    |-- Plugin: "StoreGame"  (registers: rules, UI, scoring)
```

**Key principles:**
- Core game is completely unaware of plugin existence
- No dependencies from game to new content
- Plugins can be freely turned on/off without breaking the game
- Engine compiles without game-specific code knowledge
- Hot-swapping possible via dynamically linked modules

**Registration Pattern:**

```typescript
// Game Type Registry
interface GameTypePlugin {
  id: string;
  name: string;
  minPlayers: number;
  maxPlayers: number;
  defaultConfig: GameConfig;
  createState(): GameState;
  createRules(): GameRules;
  validateAction(action: PlayerAction, state: GameState): boolean;
  processAction(action: PlayerAction, state: GameState): StateUpdate;
  checkWinCondition(state: GameState): WinResult | null;
}

class GameRegistry {
  private games: Map<string, GameTypePlugin> = new Map();

  register(plugin: GameTypePlugin): void {
    this.games.set(plugin.id, plugin);
  }

  create(gameId: string, config: Partial<GameConfig>): GameSession {
    const plugin = this.games.get(gameId);
    return new GameSession(plugin, {...plugin.defaultConfig, ...config});
  }

  list(): GameTypePlugin[] {
    return Array.from(this.games.values());
  }
}
```

### 8.4 Real-Time Communication Patterns

**WebSocket Room Architecture (Traditional):**

```
Client -> Load Balancer -> WebSocket Server Instance
                              |
                              | Redis Pub/Sub
                              |
                        Other Server Instances
                              |
                        Shared Database (Postgres)
```

Problem: Every state update processed by ALL servers (throughput bottleneck).

**Stateful Router Architecture (Modern, from Hathora):**

```
Client -> Stateful Router -> Collocated Game Server
              |                    |
              | room-to-server     | Local DB (SQLite/RocksDB)
              | mapping            |
              |
              +-> All clients for same room
                  route to SAME server
```

**Key advantages:**
- Only one server processes state for a given room
- Infinitely scalable as long as busiest room fits on one server
- Data locality eliminates distributed consistency issues
- Single multiplexed connection between server and router (reduces file descriptors)

**Message Flow:**
1. Client connects to Stateful Router with room ID
2. Router maps room to nearest server
3. All subsequent connections to same room -> same server
4. Server processes messages, updates local state
5. Server sends updates to router
6. Router broadcasts to room's connected clients

### 8.5 Anti-Cheat Patterns

**Server-Authoritative Model (Gold Standard):**

```
Client: "I pressed 'attack' at position (10,20)"
Server: Validates input, simulates attack, determines outcome
Server -> Client: "Attack hit. Target lost 25 HP."

NEVER:
Client: "I killed the target and gained 500 points"
Server: "OK" (trusting client)
```

**Client-Side Prediction with Server Reconciliation:**

```
Frame 1: Client sends input #42 (move right)
         Client immediately applies move locally (prediction)
Frame 2: Client sends input #43 (attack)
         Client applies attack locally
Frame 5: Server confirms input #42 result
         Client checks: prediction matches? -> keep
                        prediction differs? -> rollback + replay #43
```

**Defense Layers:**
1. **Server authority**: Server recomputes all critical state
2. **Input validation**: Rate limiting, range checking, physics bounds
3. **Behavioral analysis**: Statistical anomaly detection (impossible reaction times, perfect accuracy)
4. **Deterministic lockstep**: Create verifiable game states for validation
5. **Bulkhead pattern**: Compromises in one area cannot cascade

**For Web-Based Games (like War of Names):**
- All game logic on backend (already planned)
- API rate limiting per player
- Server-side timer validation (don't trust client timestamps)
- Action sequence validation (can't attack if protection is active)
- Statistical monitoring (impossible score gains)

---

## 9. Lobby Systems Architecture

### Three-Service Architecture (Industry Standard from AccelByte)

```
1. LOBBY SERVICE
   - Persistent WebSocket connection per client
   - Handles: presence, notifications, party invites, chat
   - Always connected while player is in game

2. SESSION SERVICE
   - Party formation and operations (create, join, update, leave)
   - Session creation and player assignment
   - User attribute tracking (skill ratings, region)
   - Session lifecycle tracking

3. MATCHMAKING SERVICE
   - Collects match tickets from players/parties
   - Puts tickets in queues
   - Spawns worker processes to group tickets into matches
   - Applies matchmaking ruleset
```

### Matchmaking Algorithm (AccelByte -- Tested to 1M CCU)

**Ticket Structure:**
```json
{
  "party_id": "abc-123",
  "players": [
    {"id": "p1", "mmr": 1500, "latency": {"us-east-1": 29, "eu-central-1": 72}}
  ],
  "game_mode": "5v5",
  "match_criteria": {
    "max_mmr_spread": 40,
    "max_latency": 50,
    "min_team_size": 3
  }
}
```

**Progressive Flexing (Time-Based):**

| Wait Time | MMR Spread | Latency Threshold |
|-----------|-----------|-------------------|
| 0-20s | 40 | 50ms |
| 20-30s | 60 | 100ms |
| 30-60s | 80 | 150ms |
| 60s+ | 100 | 200ms |

Auto-backfill: System creates tickets to fill incomplete sessions.

**Performance at 1M CCU:**
- Matchmaking p99 latency: < 35 seconds
- API operations p99: < 1 second
- Success rate: > 99.89%
- Concurrent match sessions: ~100,000 at peak

### Room-Based Architecture (Nakama / SmartFoxServer)

```
Master Server
    |-- Authentication
    |-- Lobby management
    |-- Matchmaking
    |
    +-- Game Server Instance 1 (Room A, Room B)
    +-- Game Server Instance 2 (Room C, Room D)
    +-- Game Server Instance N ...
```

**Room Properties:**
- Maximum players (e.g., 10)
- Maximum spectators (e.g., 50)
- Room metadata (game mode, skill bracket)
- Lock status (joinable / in-progress)
- Room state (waiting, playing, finished)

### Presence System (Nakama)

Presence = `(user_id, session_id, node_id)` tuple.

```
// On join
match.presences -> [{userId, sessionId, username, node}]

// Subscribe to changes
onMatchPresence(joins: Presence[], leaves: Presence[])

// Status updates
setStatus("online") / setStatus("in_game") / setStatus("away")

// Free-form status visible to friends
setStatus('{"playing": "quiz", "score": 150}')
```

### Spectator Architecture

Room configuration supports separate spectator capacity:
```
Room {
  maxPlayers: 10,
  maxSpectators: 50,
  properties: {
    spectatorMode: true,
    delayedFeed: 5000  // 5-second delay to prevent ghosting
  }
}
```

Spectators:
- Receive state updates (read-only)
- Cannot send game actions
- Can send chat messages
- Optional delay to prevent cheating (ghosting prevention)

---

## 10. Leaderboard Systems

### Redis Sorted Sets (Industry Standard)

**Core Operations:**

| Operation | Command | Complexity | Description |
|-----------|---------|------------|-------------|
| Add/Update | `ZADD board score player` | O(log N) | Upsert player score |
| Increment | `ZINCRBY board delta player` | O(log N) | Add to player score |
| Get Score | `ZSCORE board player` | O(1) | Fetch specific player's score |
| Get Rank | `ZREVRANK board player` | O(log N) | Player's position (0-indexed) |
| Top N | `ZREVRANGE board 0 N-1 WITHSCORES` | O(log N + N) | Top N players |
| Around Me | `ZREVRANGE board (rank-5) (rank+5)` | O(log N + 10) | Players near specific rank |
| Remove | `ZREM board player` | O(log N) | Remove player |
| Social | `ZINTERSTORE friends_board 2 board friends_set` | O(N*K) | Leaderboard filtered to friends |

**Key property:** Sorting happens on write (ZADD), not on read. Optimal for leaderboards where reads vastly outnumber writes.

**Performance:** Fetching top 10 is O(log N + 10) whether N = 100 or 100 million.

### Time-Windowed Leaderboards

```
// Create separate sorted sets per time window
leaderboard:daily:2026-03-30
leaderboard:weekly:2026-W13
leaderboard:monthly:2026-03
leaderboard:season:2026-S1
leaderboard:alltime

// On score update, update ALL relevant windows
MULTI
  ZADD leaderboard:daily:2026-03-30 100 "player:123"
  ZADD leaderboard:weekly:2026-W13 100 "player:123"
  ZADD leaderboard:monthly:2026-03 100 "player:123"
  ZADD leaderboard:alltime 100 "player:123"
EXEC

// Set TTL on time-windowed keys
EXPIRE leaderboard:daily:2026-03-30 172800  // 2 days
EXPIRE leaderboard:weekly:2026-W13 1209600  // 14 days
```

### Leaderboard API Design

```
POST   /leaderboard/{id}/score      -> Submit score (200 OK or 202 Accepted)
GET    /leaderboard/{id}/top/:count -> Absolute leaderboard (top N)
GET    /leaderboard/{id}/around/:player_id/:count -> Relative (around me)
GET    /leaderboard/{id}/player/:player_id -> Individual rank + score
GET    /leaderboard/{id}/friends/:player_id/:count -> Friends only
```

### Nakama Leaderboard Model

```
Leaderboard {
  id: string,                           // unique identifier
  sortOrder: "DESC" | "ASC",            // ranking direction
  operator: "set" | "best" | "incr" | "decr",  // score update behavior
  resetSchedule: "0 0 * * 1",          // CRON format (e.g., weekly Monday)
  authoritative: boolean,               // if true, only server can submit
  metadata: {}                          // custom data
}

Record {
  ownerId: string,           // user ID (one record per owner per leaderboard)
  score: number,             // numeric score
  subscore: number,          // tiebreaker
  username: string,          // display name
  rank: number,              // computed position
  metadata: string,          // custom JSON data
  createTime: timestamp,
  updateTime: timestamp,
  expiryTime: timestamp      // auto-cleanup
}
```

**Operators in detail:**
- `set`: Replace score with submitted value (absolute)
- `best`: Update only if submitted > current (high score)
- `incr`: Add submitted value to current (cumulative)
- `decr`: Subtract submitted value from current

**Tournaments** in Nakama are leaderboards with additional config: scheduling, authoritative status, participant limits, entry fees, rewards.

### Scaling Patterns

**Partitioning:**
- Score-based sharding for top-N queries
- Player-ID sharding for individual lookups
- Consistent hashing for distributed architectures
- Redis Cluster with hash slot redistribution

**Caching:**
- Cache-aside for relational database
- Write-behind for async persistence from Redis to database
- CDN for popular leaderboard pages with TTL-based expiration

**Capacity Planning (50M DAU reference):**
- Write QPS: 600
- Read QPS: 3,000 (5:1 ratio)
- Memory: 2.2 GB (70M players x 32 bytes)
- Storage: 2.9 TB (5-year retention)

### ELO / Glicko-2 Rating Systems

**ELO (Basic):**
- Single parameter: Rating (R)
- Uniform K-factor for all players
- Expected score: `E = 1 / (1 + 10^((R_opponent - R_player) / 400))`
- Update: `R_new = R_old + K * (actual - expected)`
- Problem: No confidence tracking, slow to converge for new players

**Glicko-2 (Advanced -- Used by CS2, Dota 2, Lichess, Chess.com):**

Three parameters:
- **mu (Rating)**: Player strength estimate
- **phi (Rating Deviation / RD)**: Confidence in rating (higher = less certain)
- **sigma (Volatility)**: How erratic the player's performance is

**Key behaviors:**
- RD increases over inactivity: `RD = min(sqrt(RD_0^2 + c^2 * t), 350)`
- High RD = larger rating changes per game (less confident, learns faster)
- Low RD = smaller changes (confident assessment, stable)
- Volatility tracks performance consistency vs. upset frequency

**Update Algorithm (Simplified):**

```
1. Pre-period: Convert Glicko ratings to Glicko-2 scale

2. Compute auxiliary quantities:
   g(phi) = 1 / sqrt(1 + 3*phi^2 / pi^2)
   E(mu, mu_j, phi_j) = 1 / (1 + exp(-g(phi_j) * (mu - mu_j)))
   v = [sum(g(phi_j)^2 * E * (1-E))]^(-1)
   Delta = v * sum(g(phi_j) * (s_j - E))

3. Update volatility sigma' (iterative Illinois algorithm)

4. Update deviation:
   phi' = 1 / sqrt(1/(phi^2 + sigma'^2) + 1/v)

5. Update rating:
   mu' = mu + phi'^2 * sum(g(phi_j) * (s_j - E))

6. Convert back to Glicko scale
```

**Practical implementation for matchmaking:**
- Match players with similar ratings (mu)
- Weight by RD: prefer matching players with low RD (confident ratings)
- Use sigma to identify inconsistent players (may need different bracket)
- New players start with high RD (1500 rating, 350 RD, 0.06 volatility)
- After 10-20 games, RD decreases to ~50, ratings stabilize

---

## 11. Key Takeaways for War of Names

### Patterns Most Relevant to This Project

War of Names is a **closed competition platform** with potential for multiple game modes within a competition (quiz, attack/guess, future minigames). Here are the patterns that map directly:

#### 1. Plugin/Registry Architecture for Game Types

Like Roblox's per-game isolation or Colyseus's room types, War of Names could define each game mode as a registered plugin:

```python
# Backend game type registry
class GameTypeRegistry:
    _types: dict[str, GameTypePlugin] = {}

    @classmethod
    def register(cls, game_type: GameTypePlugin):
        cls._types[game_type.id] = game_type

    @classmethod
    def create_session(cls, type_id: str, competition_id: int, config: dict):
        plugin = cls._types[type_id]
        return plugin.create_session(competition_id, config)

# Each game mode registers itself
@GameTypeRegistry.register
class QuizGameType(GameTypePlugin):
    id = "quiz"
    min_players = 1
    max_players = 100

    def create_session(self, competition_id, config):
        return QuizSession(competition_id, config)

    def validate_action(self, action, state):
        # Quiz-specific validation
        pass

    def process_action(self, action, state):
        # Score answer, advance question
        pass

@GameTypeRegistry.register
class AttackGameType(GameTypePlugin):
    id = "attack"
    min_players = 2
    max_players = 2  # attacker + target
    # ...
```

#### 2. State Machine for Game Sessions

Following the hierarchical FSM pattern, each game session follows predictable state transitions:

```
CompetitionState:
  REGISTRATION -> ACTIVE -> CYCLE_TRANSITION -> ACTIVE -> ... -> SEASON_END

CycleState:
  STARTING -> QUIZ_PHASE -> ATTACK_PHASE -> SCORING -> RESULTS -> ENDED

QuizSessionState:
  WAITING -> QUESTION_ACTIVE -> ANSWER_REVEAL -> NEXT_QUESTION -> COMPLETED
```

#### 3. Leaderboard Architecture

Redis sorted sets are the clear winner for real-time leaderboards. For War of Names:

```
leaderboard:competition:{id}:season:{season_id}          -- season leaderboard
leaderboard:competition:{id}:cycle:{cycle_id}             -- per-cycle leaderboard
leaderboard:competition:{id}:alltime                      -- all-time leaderboard

# Operations map to existing Scoring Engine
ZINCRBY leaderboard:competition:1:season:1 50 "player:42"  -- add 50 points
ZREVRANK leaderboard:competition:1:season:1 "player:42"    -- get rank
ZREVRANGE leaderboard:competition:1:season:1 0 9 WITHSCORES -- top 10
```

#### 4. Supercell's Cross-Game Abstraction

The hierarchical key-value store with CDC pattern is remarkably elegant for War of Names:

```
Topic: competition:{id}:player:{player_id}
  "score"     -> {points: 150, rank: 3}
  "inventory" -> {shield: 2, reveal: 1}
  "status"    -> {online: true, in_quiz: false}

Topic: competition:{id}:announcements
  "<timestamp_uuid>" -> {type: "cycle_start", message: "..."}
```

#### 5. Authentication Pattern

Follow the Telegram/Discord model:
- Server-side token verification (never trust client)
- Short-lived session tokens with refresh
- All game actions require valid session

#### 6. Anti-Cheat (Already Planned)

War of Names already follows the right pattern:
- All business logic on backend (server-authoritative)
- Database is single source of truth
- Ledger-based scoring (no direct balance mutations)
- Audit trail on every state change
- Frontend handles display/interaction/validation only

---

## Open-Source Game Servers Worth Studying

### Colyseus (Node.js)
- Room-based architecture with Schema state sync
- Binary delta compression
- Matchmaking with filterBy/sortBy
- Room lifecycle: onCreate -> onJoin -> onLeave -> onDispose
- patchRate: 50ms default (20fps)
- Max 64 serialized fields per Schema
- Zod validation for messages
- Reconnection support with tokens
- [docs.colyseus.io](https://docs.colyseus.io/)

### Nakama (Go)
- Monolithic stateful server
- WebSocket + rUDP, Protocol Buffers + JSON
- Built-in matchmaking, leaderboards, tournaments
- Presence system (user + session + node)
- Streams for real-time data distribution
- PostgreSQL/CockroachDB persistence
- In-memory search (Bluge)
- Server-authoritative match handlers
- [heroiclabs.com/docs](https://heroiclabs.com/docs/)

---

## Sources

### Roblox
- [Roblox Infrastructure for Record-Breaking Experiences](https://about.roblox.com/newsroom/2025/06/roblox-infrastructure-supporting-record-breaking-games)
- [Roblox Engineering Infrastructure](https://corp.roblox.com/engineering/infrastructure)
- [Roblox OrderedDataStore Documentation](https://create.roblox.com/docs/reference/engine/classes/OrderedDataStore)
- [Roblox Engine -- Fandom Wiki](https://roblox.fandom.com/wiki/Engine)
- [Luau Sandbox Documentation](https://luau.org/sandbox/)
- [Multiplayer Game Deep Dive -- Roblox Backend Concepts](https://edgegap.com/blog/multiplayer-game-deep-dive-introducing-backend-concepts-through-roblox)

### Discord Activities
- [Discord Activities Overview](https://discord.com/developers/docs/activities/overview)
- [Discord Embedded App SDK -- GitHub](https://github.com/discord/embedded-app-sdk)
- [Activities Architecture -- DeepWiki](https://deepwiki.com/discord/discord-api-docs/5.1-activities-overview-and-architecture)
- [Colyseus + Discord Integration](https://colyseus.io/blog/discord-embedded-sdk/)
- [Playroom Kit for Discord](https://docs.joinplayroom.com/components/discord)

### Telegram Mini Apps
- [Telegram Mini Apps Documentation](https://core.telegram.org/bots/webapps)
- [About the Platform -- Telegram Mini Apps](https://docs.telegram-mini-apps.com/platform/about)
- [Telegram Mini Apps Ecosystem Explained](https://www.nadcab.com/blog/telegram-mini-apps-ecosystem-explained)

### WeChat Mini Games
- [WeChat Mini Game Infrastructure -- Cocos](https://www.cocos.com/en/post/get-to-know-the-wechat-mini-game-infrastructure)
- [WeChat Mini Game Developer Guide](https://developers.weixin.qq.com/minigame/en/dev/guide/)
- [Building WeChat Mini Games -- Game Developer](https://www.gamedeveloper.com/business/-mostly-everything-you-need-to-know-about-building-wechat-mini-games)

### Facebook Instant Games
- [Instant Games SDK Reference](https://developers.facebook.com/docs/games/build/instant-games/reference/instant-games-sdk)
- [Phaser Facebook Instant Games Leaderboards](https://phaser.io/tutorials/facebook-instant-games-leaderboards)
- [Facebook Instant Games Development Guide 2026](https://ilogos.biz/facebook-instant-games-development-guide)

### Supercell
- [Supercell Real-Time Events with ScyllaDB](https://www.scylladb.com/2025/01/14/how-supercell-handles-real-time-persisted-events-with-scylladb/)
- [Inside Supercell's Minimalist Social Network -- The New Stack](https://thenewstack.io/inside-supercells-minimalist-massive-social-network/)
- [Supercell Case Study -- AWS](https://aws.amazon.com/solutions/case-studies/supercell-all-in/)
- [Clash Royale Deconstruction -- Game Developer](https://www.gamedeveloper.com/design/clash-royale---deconstructing-supercell-s-next-billion-dollar-game)

### Jackbox Games
- [Behind the Scenes of Party Pack 10 Engineering](https://www.jackboxgames.com/blog/behind-the-scenes-of-pp10-engineering)
- [Johnbox Private Server Implementation](https://github.com/InvoxiPlayGames/johnbox)
- [Party Box Framework](https://github.com/hammre/party-box)
- [Jackbox Games Design Principles](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack)

### Game Architecture Patterns
- [State Pattern -- Game Programming Patterns](https://gameprogrammingpatterns.com/state.html)
- [ECS FAQ -- GitHub](https://github.com/SanderMertens/ecs-faq)
- [Entity-Component-Worker Architecture](https://www.gamedeveloper.com/programming/the-entity-component-worker-architecture-and-its-use-on-massive-online-games)
- [Scalable WebSocket Architecture -- Hathora](https://blog.hathora.dev/scalable-websocket-architecture/)
- [Client-Server Game Architecture -- Gabriel Gambetta](https://www.gabrielgambetta.com/client-server-game-architecture.html)
- [Modular Game Features in UE5](https://www.unrealengine.com/en-US/blog/modular-game-features-in-ue5-plug-n-play-the-unreal-way)

### Lobby & Matchmaking
- [Scaling Matchmaking to 1M Players -- AccelByte](https://accelbyte.io/blog/scaling-matchmaking-to-one-million-players)
- [Nakama Lobby System](https://heroiclabs.com/docs/nakama/guides/concepts/lobby/)
- [Nakama Architecture Overview](https://heroiclabs.com/docs/nakama/getting-started/architecture/)
- [SmartFoxServer Lobby Matchmaking](https://docs2x.smartfoxserver.com/ExamplesUnity/lobby-matchmaking)

### Leaderboards & Rating Systems
- [Designing Real-Time Leaderboards -- Redis](https://systemdr.substack.com/p/designing-real-time-leaderboards)
- [Leaderboard System Design](https://systemdesign.one/leaderboard-system-design/)
- [Redis Leaderboards](https://redis.io/solutions/leaderboards/)
- [Nakama Leaderboards](https://heroiclabs.com/docs/nakama/concepts/leaderboards/)
- [Glicko Rating System -- Wikipedia](https://en.wikipedia.org/wiki/Glicko_rating_system)
- [Glicko-2 Algorithm -- Mark Glickman](https://www.glicko.net/glicko/glicko2.pdf)
- [Elo-MMR for Massive Competitions](https://cs.stanford.edu/people/paulliu/files/www-2021-elor.pdf)

### Anti-Cheat
- [Anti-Cheat Architecture -- Stage Four Security](https://stagefoursecurity.com/blog/2025/05/13/anti-cheat-architecture/)
- [Real-Time Card Games .NET Architecture](https://developersvoice.com/blog/practical-design/realtime-card-games-net-architecture-guide/)
- [Systematic Review of Anti-Cheat Defenses](https://arxiv.org/html/2512.21377v1)

### Open-Source Game Servers
- [Colyseus Documentation](https://docs.colyseus.io/)
- [Colyseus State Synchronization](https://docs.colyseus.io/state)
- [Colyseus Rooms](https://docs.colyseus.io/room)
- [Nakama -- GitHub](https://github.com/heroiclabs/nakama)
- [Nakama Tournaments](https://heroiclabs.com/docs/nakama/concepts/tournaments/)
