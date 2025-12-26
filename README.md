# 🏥 AI Health Coach

A AI health coaching web application built with Django and OpenAI GPT. Features intelligent context management, long-term memory, and safety protocol integration.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen)

## ✨ Features

- **Chat Interface** - Clean, intuitive messaging experience with typing indicators
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
- MongoDB
- OpenAI API key

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/gulshan-100/HealthCoach-AI-Bot.git
cd HealthCoach-AI-Bot

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env

# 5. Run migrations
python manage.py migrate

# 6. Seed safety protocols
python manage.py seed_protocols

# 7. Start the server
python manage.py runserver

# 8. Open browser
# Navigate to: 
http://localhost:8000
```

### Configuration (.env)

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# MongoDB (use your own or the provided test database)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_NAME=ai_healthcoach

# Optional
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
```

