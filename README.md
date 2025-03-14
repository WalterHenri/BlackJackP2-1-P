# Blackjack 21 P2P Game Architecture

## Core Components

### 1. Game Objects
- **Card**: Represents a playing card with suit and value
- **Deck**: Collection of 52 cards, with shuffle and draw capabilities
- **Hand**: Collection of cards for a player or dealer, with calculation methods
- **Player**: Represents a user with properties like name, balance, and current hand
- **Dealer**: Special player that follows specific rules for playing
- **Game**: Manages the game state, rules, and flow

### 2. Network Components
- **Socket Manager**: Handles P2P connections between players
- **Message Handler**: Processes and routes game messages between clients
- **Serialization Layer**: Converts game state to transferable format

### 3. Game Logic
- **Rules Engine**: Implements blackjack rules (hit, stand, split, double down)
- **Bet Manager**: Handles coin transactions and bet placement
- **Game State Manager**: Tracks the current state of the game (waiting, dealing, player turns, etc.)
- **Turn Manager**: Controls whose turn it is and what actions are valid

### 4. Data Management
- **Player Profile Store**: Stores player information and coin balances
- **Game History**: Records game outcomes and significant events
- **Session Manager**: Manages active game sessions

## Architecture Decisions

### Technology Stack
- **Backend**: Python with socket programming for P2P connectivity
- **Frontend**: Pygame for game visualization and user interaction
- **Data Storage**: SQLite for persistent player data
- **Networking**: Custom socket implementation using Python's `socket` library

### Application Structure
```
blackjack_p2p/
├── client/
│   ├── ui/                  # Pygame UI components
│   ├── network/             # Socket client implementation
│   └── game_client.py       # Client entry point
├── server/
│   ├── matchmaking.py       # Optional matchmaking server
│   └── lobby_server.py      # Minimal central server for discovery
├── shared/
│   ├── models/              # Game object definitions
│   │   ├── card.py
│   │   ├── deck.py
│   │   ├── hand.py
│   │   ├── player.py
│   │   └── game.py
│   ├── game_logic/          # Game rules and mechanics
│   │   ├── rules.py
│   │   ├── bet_manager.py
│   │   └── state_manager.py
│   ├── network/             # Network protocol definitions
│   │   ├── message.py
│   │   ├── serializer.py
│   │   └── p2p_manager.py
│   └── utils/               # Shared utilities
├── data/
│   ├── database.py          # Database interface
│   └── file_storage.py      # File-based storage
└── main.py                  # Application entry point
```

### P2P Network Architecture
- **Hybrid P2P Model**: Use a lightweight central server for discovery, then direct P2P for gameplay
- **Host-Based Games**: One player hosts the game (acts as server), others connect as clients
- **Fallback Mechanism**: If direct P2P fails, relay through the minimal central server

### Communication Protocol
- Custom message format for game events:
  ```json
  {
    "type": "GAME_ACTION",
    "action": "HIT",
    "player_id": "uuid",
    "timestamp": 1234567890,
    "game_id": "uuid"
  }
  ```

## Data Management Strategy

### Player Data
- Store core player information (username, uuid, balance) in SQLite
- Encrypt sensitive data like balance to prevent cheating

### Game State
- In-memory during active games
- Serialized for network transmission
- Basic game logs stored in text files for auditing

### Session Management
- Temporary game sessions stored in memory
- Option to persist incomplete games to files for recovery