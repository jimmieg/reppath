# RepPath

RepPath is an AI-powered training plan generator. It conducts a multi-turn intake conversation to learn your goal, schedule, experience level, equipment access, and any injuries, then generates a personalized weekly training plan rendered as a visual calendar. After generation, you can ask for adjustments in plain English and the calendar updates immediately.

## Prerequisites

- Python 3.11+
- Node.js 20+
- An OpenAI API key

## Setup

**1. Clone the repo**

    git clone https://github.com/jimmieg/reppath.git
    cd reppath

**2. Create your environment file**

    cp .env.example .env

Open .env and add your OpenAI API key:

    OPENAI_API_KEY=sk-your-key-here

**3. Create and activate a Python virtual environment**

    python3 -m venv venv
    source venv/bin/activate

**4. Install Python dependencies**

    pip install -r requirements.txt

**5. Install frontend dependencies**

    cd frontend && npm install && cd ..

## Running the App

Start both the backend and frontend with a single command:

    ./start.sh

- Backend runs at: http://localhost:8000
- Frontend runs at: http://localhost:5173

Open http://localhost:5173 in your browser.

## Running the Eval

Make sure the backend is running, then in a separate terminal:

    source venv/bin/activate
    python eval/eval.py

Results are saved to eval/results.json.

## Known Limitations

- When requesting an exercise swap, specify the exact day. If the exercise is not found on that day, RepPath will find the nearest match elsewhere in the plan.
- Plan generation occasionally produces one extra training day on 5+ day requests. If this happens, ask RepPath to remove the extra day in chat.
- Corpus retrieval occasionally surfaces off-topic chunks in backend logs. This does not affect plan quality.
