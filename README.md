# 🔍 Repository Mirror

**Repository Mirror** is an AI-powered system that evaluates GitHub repositories and generates:

- ✅ A score from 0–100, with tier badges: 🥉 Bronze, 🥈 Silver, 🥇 Gold
- 📝 A summary of strengths and weaknesses
- 🛠️ A personalized roadmap for improvement

---

## 🚀 Features

- Analyze any public GitHub repository
- Get structured feedback on documentation, testing, version control, and structure
- Automatically generate improvement suggestions
- Tiered scoring system for visual clarity

---

## ⚙️ Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/repository-mirror.git
   cd repository-mirror

2. **Install dependencies**
pip install -r requirements.txt

3.**Run the backend server**
uvicorn main:app --reload

4.**Send a POST request to /analyze**
{
  "url": "https://github.com/owner/repo"
}
**🧪 Example**
🔶Input:

json
{
  "url": "https://github.com/fastapi/fastapi"
}
🔶Output:

Score: 79.2 🥈 Silver

Summary: Strong documentation, version control, structure, and tests

Roadmap:

Improve commit frequency and message quality

Add more unit tests with coverage reporting

