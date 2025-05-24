# VoiceBot with LiveKit and Twilio Integration

## Overview

This project provides a comprehensive voicebot solution using LiveKit for real-time communication and Twilio for telephony integration. The system supports Retrieval-Augmented Generation (RAG) capabilities with Redis as the vector store and MySQL for conversation tracking and agent management.

## Prerequisites

- **Python 3.12 or 3.13** (Recommended)
- **Redis** (with Redis Stack for vector operations)
- **MySQL** (for conversation tracking and agent management)
- **LiveKit Server**
- **Twilio Account**
- **OpenAI API Key**
- **Deepgram API Key** (for speech-to-text)

## Installation

### 1. Clone the Repository

```sh
git clone https://github.com/maulesh-softmaxai/voicebot-live-kit.git
cd voicebot-live-kit
```

### 2. Set Up Virtual Environment

```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies

```sh
pip install -r requirements.txt
```

## Configuration

### Database Setup

#### Redis Configuration (Vector Store)

```sh
# Start Redis Stack with Docker
docker run -p 6379:6379 redis/redis-stack-server:latest

# Verify Redis is running
redis-cli ping
```

#### MySQL Configuration (Agent Management)

Ensure your MySQL database is running with the following schema:

```sql
CREATE DATABASE Intellizen;

-- Users table
CREATE TABLE users (
    UserID INT PRIMARY KEY,
    Name VARCHAR(100),
    Email VARCHAR(100),
    ShopName VARCHAR(100),
    isDelete TINYINT(1) DEFAULT 0
);

-- Agents table
CREATE TABLE agents (
    AgentID INT PRIMARY KEY,
    UserID INT,
    AgentName VARCHAR(100),
    CreatedDate DATE,
    AssociatedTwilioNumber VARCHAR(15),
    IsActive TINYINT(1) DEFAULT 1,
    isDelete TINYINT(1) DEFAULT 0,
    FOREIGN KEY (UserID) REFERENCES users(UserID)
);

-- Conversations table
CREATE TABLE conversations (
    ConversationID INT PRIMARY KEY,
    AgentID INT,
    CallerNumber VARCHAR(15),
    CalledNumber VARCHAR(15),
    Duration INT,
    ConversationSummary TEXT,
    Conversation TEXT,
    UserID INT,
    FOREIGN KEY (AgentID) REFERENCES agents(AgentID),
    FOREIGN KEY (UserID) REFERENCES users(UserID)
);

-- Documents table
CREATE TABLE documents (
    DocumentID INT PRIMARY KEY,
    AgentID INT,
    UserID INT,
    DocumentName VARCHAR(100),
    UploadDate DATE,
    Category ENUM('Document', 'Link'),
    IsActive TINYINT(1) DEFAULT 1,
    ProcessingStartedAt DATETIME,
    ProcessingCompletedAt DATETIME,
    IsProcessed ENUM('Processing', 'Processed', 'Failed') DEFAULT 'Processing',
    isDelete TINYINT(1) DEFAULT 0,
    FOREIGN KEY (AgentID) REFERENCES agents(AgentID),
    FOREIGN KEY (UserID) REFERENCES users(UserID)
);

-- Twilio table
CREATE TABLE twilio (
    TwilioNumber VARCHAR(15) PRIMARY KEY,
    AgentID INT,
    TwilioAccountSID VARCHAR(50),
    TwilioAccountAuthToken VARCHAR(50),
    Label VARCHAR(100),
    IsActive TINYINT(1) DEFAULT 1,
    UserID INT,
    isDelete TINYINT(1) DEFAULT 0,
    FOREIGN KEY (AgentID) REFERENCES agents(AgentID),
    FOREIGN KEY (UserID) REFERENCES users(UserID)
);
```

### Environment Variables

Create an `.env` file with the following variables:

```env
# LiveKit Configuration
LIVEKIT_URL=<YOUR_LIVEKIT_URL>
LIVEKIT_API_KEY=<YOUR_LIVEKIT_API_KEY>
LIVEKIT_API_SECRET=<YOUR_LIVEKIT_API_SECRET>

# API Keys
DEEPGRAM_API_KEY=<YOUR_DEEPGRAM_API_KEY>
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>

# Database Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=root@5555
MYSQL_DATABASE=Intellizen
```

Load the environment variables:

```sh
source .env
```

## Running the Application

### 1. Download Required Files

```sh
python intellizen_voicebot.py download-files
```

### 2. Start the Agent Server

For production:
```sh
python intellizen_voicebot.py start
```

For development:
```sh
python intellizen_voicebot.py dev
```

## Vector Database Processing

The system uses Redis as a vector store for embeddings. Here's the key portion of the code that handles vector database operations:

```python
# In your FastAPI application (e.g., main.py)
from langchain_openai import OpenAIEmbeddings
from redis import Redis

# Initialize Redis client (update host/port as needed)
redis_client = Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True)

# Initialize MySQL connection (update config as needed)
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}
db_connection = mysql.connector.connect(**db_config)

# Example embedding storage
embeddings_model = OpenAIEmbeddings(openai_api_key=openai_api_key)
text = "Sample text to embed"
embedding = embeddings_model.embed_documents([text])

# Store in Redis
redis_key = f"embedding:doc:{document_id}"
redis_client.set(redis_key, json.dumps({
    "text": text,
    "embedding": embedding,
    "document_id": document_id
}))
```

## Telephony Integration with Twilio

### 1. Create SIP Trunk

```sh
# Using the LiveKit CLI
lk sip inbound create inbound-trunk.json
```

Example `inbound-trunk.json`:
```json
{
  "trunk": {
    "name": "Demo inbound trunk",
    "numbers": ["+1234567890"]
  }
}
```

### 2. Create Dispatch Rule

```sh
lk sip dispatch create dispatchRule.json
```

Example `dispatchRule.json`:
```json
{
  "rule": {
    "dispatchRuleCallee": {
      "roomPrefix": "number-",
      "randomize": false
    }
  }
}
```

## API Endpoints

The system provides the following API endpoints:

- `POST /verify-twilio`: Verify Twilio credentials
- `POST /process`: Process documents/URLs and store embeddings

## Support

For assistance, please contact [parshva.daftari@softmaxai.com](mailto:parshva.daftari@softmaxai.com).

---

This README provides comprehensive instructions for setting up the VoiceBot system with LiveKit and Twilio integration, including database configuration and vector processing capabilities.