<<<<<<< HEAD
# 🏥 AI Health Coach

A WhatsApp-style AI health coaching web application built with Django and OpenAI GPT. Features intelligent context management, long-term memory, and safety protocol integration.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen)

## ✨ Features

- **WhatsApp-like Chat Interface** - Clean, intuitive messaging experience with typing indicators
- **Username-Based User Isolation** - Each user gets their own private chat history via unique username
- **Smart Onboarding** - Automatic information gathering about users
- **Context-Aware Responses** - Uses recent chat, long-term memories, and safety protocols
- **Streaming Responses** - Real-time response streaming via Server-Sent Events (1-2s response time)
- **Long-term Memory** - Extracts and stores important user information across sessions
- **Safety Protocols** - Built-in guardrails for appropriate health guidance
- **Voice Input/Output** - Speech-to-text and text-to-speech for hands-free interaction
- **Infinite Scroll** - Auto-loads older messages on scroll

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MongoDB Atlas account (free tier works)
- OpenAI API key
- Redis (optional, for caching)

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd AI_Healthcoach

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration below)

# 5. Run migrations
python manage.py migrate

# 6. Seed safety protocols
python manage.py seed_protocols

# 7. Start the server
python manage.py runserver

# 8. Open browser
# Navigate to: http://localhost:8000
```

### Configuration (.env)

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# MongoDB (use your own or the provided test database)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_NAME=ai_healthcoach

# Optional
REDIS_URL=redis://localhost:6379/0
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## 🏗️ Architecture Overview

```
AI_Healthcoach/
├── AI_Healthcoach/          # Django project settings
│   ├── settings.py          # Configuration
│   └── urls.py              # Main routing
│
├── chat/                    # Main application
│   ├── models.py            # MongoDB models (User, Message, Memory, Protocol)
│   ├── views.py             # API endpoints
│   ├── urls.py              # Chat routing
│   │
│   ├── services/            # Business logic layer
│   │   ├── chat_service.py       # Main orchestration
│   │   ├── llm_service.py        # OpenAI integration + context management
│   │   ├── memory_service.py     # Long-term memory management
│   │   ├── protocol_service.py   # Safety protocol matching
│   │   └── voice_service.py      # Voice transcription/synthesis
│   │
│   └── management/commands/
│       └── seed_protocols.py     # Seed default protocols
│
├── templates/chat.html      # Main chat interface
├── static/                  # CSS + JavaScript
└── requirements.txt
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Service Layer Pattern** | Clean separation of concerns, testable business logic |
| **MongoDB** | Flexible schema for varied health data, efficient document storage |
| **PyMongo (not Djongo)** | Better Python 3.10+ compatibility, direct MongoDB access |
| **GPT-3.5-turbo** | Optimal speed/quality balance for conversational health coaching |
| **Streaming (SSE)** | Lower perceived latency, better UX for long responses |
| **Session-based Users** | No auth required for MVP, simpler onboarding |

---

## 🤖 LLM Integration

### Provider: OpenAI GPT-3.5-turbo-0125

Chosen for:
- Fast response times (~1-2 seconds)
- Good conversational quality
- Cost-effective for chat applications

### Prompting Strategy

The system prompt includes:

1. **Role Definition** - Caring, professional AI Health Coach
2. **User Profile** - Name, age, health conditions, medications
3. **Long-term Memories** - Top 5 relevant memories from past conversations
4. **Safety Protocols** - Matched guidelines for the current query
5. **Recent Context** - Last 10 messages for conversation flow

### Context Window Management

| Challenge | Solution |
|-----------|----------|
| Token limits | Dynamic context optimization with priority system |
| Context overflow | Automatic truncation of oldest messages |
| Response length | Max 400 tokens for fast, focused responses |

**Token Budget**: ~2500 tokens for context, ~400 for response

---

## � User System

### Username-Based Isolation
Each user creates a unique username to access their private chat history:
- **Persistent**: Same username = same history across devices/sessions
- **Isolated**: Each username has completely separate chat data
- **Simple**: No password needed (designed for personal/family use)
- **Validated**: 3-50 characters, alphanumeric + hyphens/underscores only

### How It Works
1. **First Visit**: User prompted to enter a unique username
2. **Storage**: Username stored in browser's localStorage
3. **Identification**: Username sent in `X-Username` header with every request
4. **Database**: Messages filtered by `user_id` (normalized username)

### Sharing the App
Perfect for families or small groups:
- Share the URL with others
- Each person enters their own username
- Everyone gets their own private AI health coach
- No cross-contamination of chat histories

**Example**: "alice" and "bob" can use the same app instance with completely separate conversations.

For detailed documentation, see [USERNAME_SYSTEM.md](USERNAME_SYSTEM.md).

---

## �📡 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/api/messages` | GET | Get message history (pagination supported) |
| `/api/messages/stream` | POST | Send message, get streaming response |
| `/api/messages/send` | POST | Send message, get full response |
| `/api/typing` | GET | Get typing indicator status |
| `/api/profile` | GET | Get user profile |
| `/api/profile/username` | POST | Set username |
| `/api/health` | GET | Health check |

### Voice Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/voice/transcribe` | POST | Transcribe audio to text |
| `/api/voice/speak` | POST | Convert text to speech |
| `/api/voice/chat` | POST | Full voice conversation |

### Example: Send Message

```bash
curl -X POST http://localhost:8000/api/messages/send \
  -H "Content-Type: application/json" \
  -d '{"content": "I have a headache"}'
```

---

## 🗄️ Data Models

### Message
- `message_id`, `user_id`, `role`, `content`, `tokens`, `created_at`
- Indexed: `(user_id, -created_at)` for efficient pagination

### User
- `user_id`, `name`, `age`, `gender`, `health_conditions[]`, `medications[]`, `allergies[]`
- Tracks onboarding completion status

### Memory
- `memory_id`, `user_id`, `content`, `memory_type`, `importance` (0-10)
- Types: fact, preference, health_event, goal, concern

### Protocol
- `protocol_id`, `name`, `keywords[]`, `category`, `content`, `priority`
- Categories: safety, privacy, emergency, policy

---

## ⚡ Performance Optimizations

| Optimization | Impact |
|--------------|--------|
| GPT-3.5-turbo-0125 | ~10x faster than GPT-4 |
| Streaming responses | Instant feedback to users |
| Limited context (10 msgs) | Faster API calls |
| Redis caching | Reduced database queries |
| Batched DOM updates | Smooth UI during streaming |

**Typical response time**: 1-3 seconds

---

## 🔒 Safety Protocols

Built-in guardrails include:

1. **Medical Advice Boundaries** - Never diagnose or prescribe
2. **Sensitive Content** - Block inappropriate discussions
3. **Privacy Protection** - Never request sensitive data
4. **Emergency Recognition** - Direct to 911 when needed
5. **Professional Boundaries** - Maintain coach role
6. **Misinformation Prevention** - Avoid unverified claims
7. **Scope of Practice** - Stay within health coaching domain

---

## 🚀 Deployment

### Render (Recommended)

1. Connect GitHub repository
2. Set environment variables
3. Build command:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
   ```
4. Start command:
   ```bash
   gunicorn AI_Healthcoach.wsgi:application
   ```

### Environment Variables for Production

```env
DEBUG=False
SECRET_KEY=<generate-secure-key>
ALLOWED_HOSTS=your-domain.com
OPENAI_API_KEY=<your-api-key>
MONGODB_URI=<your-mongodb-uri>
REDIS_URL=<your-redis-url>
```

---

## ⚖️ Trade-offs & Future Improvements

### Current Limitations

| Limitation | Reason | Future Solution |
|------------|--------|-----------------|
| No user authentication | MVP simplicity | OAuth2/JWT |
| Keyword-based protocol matching | Fast, reliable | Semantic search with embeddings |
| Polling for typing | Simple implementation | WebSockets |
| Single session | Simpler data model | Multi-device sync |

### If I Had More Time...

**Features:**
- Advanced voice conversations with TTS responses
- Health tracking integration (Fitbit, Apple Health)
- Symptom checker with decision trees
- Medication interaction checking
- Multi-language support

**Technical:**
- RAG for better protocol matching
- Vector database for semantic search
- Comprehensive test suite
- CI/CD pipeline
- Monitoring (Sentry, DataDog)

**UX:**
- Rich message formatting
- Dark mode
- Message search
- Conversation export

---

## 📝 Notes

### Medical Disclaimer

This is a demonstration application. The AI provides general health information only and should **not** be considered medical advice. Users should consult healthcare professionals for medical concerns.

### API Costs

OpenAI API usage incurs costs. Set billing limits in your OpenAI account.

### Testing

For production, implement:
- Unit tests for services
- Integration tests for API endpoints
- E2E tests for chat flow
- Load testing

---

## 📄 License

This project is for educational/demonstration purposes.

## 👥 Contact

For questions: jai@cure.link

---

**Built with ❤️ for the AI Health Coach Assignment**
=======
# HealthCoach-AI-VoiceBot
>>>>>>> cee9f6e0063d256efb5ea7e1a78a993eb4640e60
