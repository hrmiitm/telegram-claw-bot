# Project 1: A Bot with Big Claw

## Problem Statement
Build an advanced, multimodal Telegram/Discord chatbot that acts as an autonomous developer assistant. The bot must:
1. **Maintain context-aware conversations** with users.
2. Provision a **48-hour isolated workspace (VM/container)** for each user.
3. Use **agentic frameworks (OpenClaw/NemoClaw)** to autonomously write code, manage files, and execute scripts inside the user's workspace.
4. **Deploy web applications** on the fly and return live links or generated files directly to the chat.
5. Reliably and safely handle at least **4 simultaneous users**.

## Architecture & Flow

### 1. Task Execution Flow
```mermaid
sequenceDiagram
    participant User
    participant Bot as Chat Bot Interface
    participant Manager as Workspace Manager
    participant Agent as Agent (OpenClaw)
    participant VM as Isolated Workspace (48h TTL)

    User->>Bot: "Write a python script to plot a sine wave, run it, and send the image."
    Bot->>Manager: Check/Create Workspace for User
    Manager-->>VM: Provision Container
    Bot->>Agent: Delegate task with User Context
    Agent->>VM: Write `plot.py`
    Agent->>VM: Execute `python plot.py`
    VM-->>Agent: Returns `plot.png`
    Agent-->>Bot: Task Complete + File
    Bot-->>User: "Here is your plot!" (Attaches `plot.png`)
```

### 2. System Architecture
```mermaid
graph TD
    A[User Interfaces] -->|Text, Files, Images| B(Bot Backend)
    B --> C{Workspace Manager}
    
    C -->|User 1| D1[Workspace 1<br/>TTL: 48h]
    C -->|User 2| D2[Workspace 2<br/>TTL: 48h]
    C -->|User 3| D3[Workspace 3<br/>TTL: 48h]
    C -->|User 4+| D4[Workspace n<br/>TTL: 48h]

    B -->|Task Delegation| E[OpenClaw/NemoClaw Agent]
    E -.->|Writes Code & Runs Scripts| D1
    E -.->|Deploys Web Apps| D2
    
    D2 -.->|Exposed via Tunnel| F((Live Web App Link))
    F -.-> B
```

## Example Input / Output
- **User Input:** "Create a React app with a dark mode toggle, run it, and give me the link."
- **Bot Action:** 
  1. Creates the React app in the user's VM.
  2. Edits code to implement the dark mode logic.
  3. Runs the dev server (`npm run dev`).
  4. Exposes the local port via a tunnel (e.g., Ngrok, Cloudflare).
- **Bot Output:** "App deployed! Access it here: `https://dark-mode-xyz.trycloudflare.com`"

## Evaluation Criteria (Student Deliverables)
1. **Source Code**: Complete bot logic, agent integration, and containerized workspace management logic.
2. **Setup Instructions**: Detailed `README.md` and `.env.example` file.
3. **Concurrency Proof**: Clear implementation showing how 4+ parallel user sessions are isolated and handled (e.g., async, multi-threading).
4. **Demo Video**: A 2-3 minute video demonstrating:
   - History/context awareness.
   - File generation and returning the file to chat.
   - A live web application deployment with a working URL.
   - Multiple users interacting simultaneously without collision.
