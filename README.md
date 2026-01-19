## 📘 CourseLens

An AI-powered course intelligence platform for smarter academic planning

CourseLens helps university students make better course decisions by turning scattered academic data into clear, evidence-backed insights. Instead of guessing workload, difficulty, or prerequisites from outdated forums or PDFs, students can query CourseLens and get structured, explainable answers powered by agentic AI and retrieval-augmented generation.

# 🚀 What Problem Does CourseLens Solve?

University course selection is surprisingly hard.

Students often juggle:

Dense course catalog PDFs

Unclear prerequisite chains

Conflicting student reviews on Reddit and forums

No visibility into how one course unlocks future options

CourseLens was built to fix this. It centralizes fragmented academic information and uses AI to analyze, compare, and explain courses in a way that actually supports real planning decisions.

# 🧠 What CourseLens Does

CourseLens allows students to:

Search and compare courses using natural language

Understand workload, difficulty, and assessment style

See prerequisite chains and downstream course unlocks

Read summarized insights from real student discussions

Make planning decisions backed by retrieved evidence, not guesses

All responses are grounded in retrieved sources like course catalogs, PDFs, and student reviews.

🏗️ System Architecture (High Level)

CourseLens is built using a multi-agent architecture, where each agent handles a specific responsibility and collaborates to generate a final response.

Core Agents

Catalog Agent
Parses official course catalogs and prerequisite rules from PDFs and structured data.

Review Mining Agent
Extracts and embeds student discussions and reviews (e.g., Reddit, forums).

Planner Agent
Builds and reasons over a course dependency graph to understand progression paths.

Synthesis Agent
Combines retrieved evidence into a clear, student-friendly answer.

🔍 Retrieval-Augmented Generation (RAG)

CourseLens uses a full RAG pipeline to ensure accuracy and explainability:

Course PDFs and reviews are chunked into semantic segments

Text is converted into vector embeddings

Relevant chunks are retrieved at query time

The LLM generates answers grounded only in retrieved context

This prevents hallucinations and ensures responses can be traced back to real academic sources.

🧰 Tech Stack
Backend

FastAPI – API layer and orchestration

Python – Core logic and agents

PostgreSQL – Structured course and metadata storage

Vector Database (e.g., Chroma / FAISS) – Semantic search

LLMs – Reasoning and synthesis

AI & Data

Retrieval-Augmented Generation (RAG)

Text chunking and embeddings

Semantic search over unstructured data

Course dependency graph modeling

Frontend (Optional / Extensible)

Interactive web interface for querying and comparison

Visual course dependency exploration

🔄 Typical Workflow

User asks a question like:
“Is CMPUT 301 manageable with CMPUT 366?”

Relevant agents retrieve:

Course descriptions

Prerequisites

Student workload discussions

The planner agent evaluates dependency and overlap

The synthesis agent generates a grounded response

The user receives a clear, evidence-based answer

📊 Real-World Impact

CourseLens reduces guesswork in academic planning by:

Saving time spent browsing PDFs and forums

Preventing poor course combinations

Helping students plan long-term degree paths

Making academic information accessible and explainable

It turns fragmented academic data into actionable insight.

🛠️ Setup (High Level)
# Clone the repository
git clone https://github.com/your-username/CourseLens.git
cd CourseLens

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn app.main:app --reload


(Exact setup may vary depending on vector DB and API keys.)

📈 Future Enhancements

Personalized recommendations based on degree program

GPA and workload simulation

Instructor-specific analysis

Term-by-term academic planning assistant

Deeper integration with university APIs
