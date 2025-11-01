# Dynamic Business Landing Page - Project Description

## Overview

A microservices-based application that dynamically generates business landing pages using AI agents, with separate containers for each service component.

## Server Stack

### 1. Frontend Service (Port 5173)

- **Technology**: React + TypeScript + Vite
- **Purpose**: User interface for submitting business information and viewing generated landing pages
- **Communication**: Makes HTTP requests to the Backend API

### 2. Backend API (Port 8000)

- **Technology**: FastAPI (Python)
- **Purpose**: API gateway that orchestrates requests between frontend and agents service
  - Receives build requests from frontend
  - Fetches business data from Google Maps API
  - Manages artifacts and session state
  - Provides Server-Sent Events (SSE) for real-time progress updates
- **Communication**:
  - Receives requests from Frontend
  - Sends build requests to Agents Service
  - Receives events from Agents Service via `/api/events`

### 3. Agents Service (Port 8001)

- **Technology**: FastAPI (Python)
- **Purpose**: AI orchestration service that generates landing pages
  - Orchestrates mapper, generator, and validator agents
  - Uses OpenAI API for AI operations
  - Manages build workflows with retry logic
- **Communication**:
  - Receives build requests from Backend API
  - Communicates with MCP Server via MCP protocol (RPC)
  - Sends progress events to Backend API

### 4. MCP Server (Port 8003)

- **Technology**: Python (FastMCP + Starlette/Uvicorn)
- **Purpose**: Model Context Protocol server providing tools for agents
  - File bundling operations (HTML, CSS, JS)
  - Quality assurance validation
  - Network operations (HTTP requests with adaptive policies)
  - Workspace and cache management
- **Communication**: Receives RPC calls from Agents Service via stdio/JSON-RPC protocol

## Communication Flow

1. **User Request Flow**:

   ```
   Frontend → Backend API → Agents Service → MCP Server
   ```

2. **Progress Updates**:

   ```
   Agents Service → Backend API (events) → Frontend (SSE)
   ```

3. **Build Response**:
   ```
   Agents Service → Backend API → Frontend
   ```

## Docker Network

All services run in a shared Docker bridge network (`landing-network`), enabling service discovery via container names (e.g., `http://agents:8001`, `http://mcp:8003`).

## Data Storage

- **MCP Server**: Persistent volumes for workspace and cache
- **Backend API**: Persistent volumes for artifacts and logs
- **Agents Service**: Volume for logs




