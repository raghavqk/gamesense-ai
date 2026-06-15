# GameSense AI v2.0 - Tactical Analytics Engine

GameSense AI is a full-stack AI-powered gameplay analytics platform for CS2 and Valorant. 
The system analyzes uploaded MP4 gameplay footage, extracts accurate match statistics using Groq Vision AI to read the kill feed, clusters spatial points using DBSCAN, predicts performance using LSTM, and provides personalized AI coaching via Gemini.

## Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API Key
- Google Gemini API Key

## Setup Instructions

### 1. Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Verify your `.env` file in the `backend` directory has the necessary API keys:
   ```env
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   PORT=8000
   ```
5. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the frontend development server:
   ```bash
   npm run dev
   ```

## Usage
- Access the web interface at `http://localhost:5173` (or the URL provided by Vite).
- Upload an MP4 video of your CS2 or Valorant gameplay.
- Wait for the analysis pipeline to complete.
- Explore your interactive Cyber Arena dashboard.
- Chat with the AI Coach to get actionable insights based on your stats.

## Architecture Highlights
- **Groq Vision API:** Reads the actual kill feed and scoreboard for perfect accuracy instead of relying on generic object detection.
- **FastAPI Backend:** Handles video processing, async ML tasks, and provides the API routes.
- **React + Vite Frontend:** Modern, fast frontend with a dark "Cyber Arena" aesthetic, interactive Recharts, and dynamic components.
- **Gemini AI Coach:** Context-aware chatbot providing detailed coaching based on actual match performance.
