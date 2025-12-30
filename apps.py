from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import re
from dotenv import load_dotenv
import os

load_dotenv()  


# -------------------- APP SETUP --------------------
app = Flask(__name__, template_folder="templates")

# -------------------- SCRAPE WEBSITE ONCE --------------------
URL = "https://computervalleyit.com/about-us"
MAX_CHARS = 15000

response = requests.get(URL, timeout=15)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
    tag.decompose()

text = soup.get_text(separator="\n")
lines = [line.strip() for line in text.splitlines() if line.strip()]
clean_text = re.sub(r"\s+", " ", "\n".join(dict.fromkeys(lines)))

if len(clean_text) > MAX_CHARS:
    clean_text = clean_text[:MAX_CHARS] + " ...[TRUNCATED]..."

# -------------------- MODEL CONFIG --------------------
API_KEY = os.getenv("API_KEY")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY  # 🔐 move to env variable later
)

SYSTEM_PROMPT = (
    "You are a strict QA assistant. Follow these rules exactly:\n"
    "1) You MUST only use the WEBSITE CONTENT provided in the user message to answer.\n"
    "2) If the website contains a clear answer, provide a short paragraph summarizing that information.\n"
    "3) If the website mentions an OPTION or feature exists but provides NO details, reply EXACTLY:\n"
    "   contact computervally for further information\n"
    "4) If limited info exists, answer and append exactly:\n"
    "   If you want to get more information please contact computervally it solution\n"
    "5) If NO relevant answer exists, reply EXACTLY:\n"
    "   contact computervally it solution\n"
    "6) Do NOT guess or invent information.\n"
)

# -------------------- ROUTES --------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json

    # 1️⃣ Validate JSON
    if not data or "datas" not in data:
        return jsonify({"result": "No message received"})

    user_message = str(data["datas"]).strip()

    # 2️⃣ Simple greeting handling
    if user_message.lower() in ("hi", "hello", "hai", "halo", "good morning"):
        return jsonify({"result": "halo, how can i help you"})

    # 3️⃣ Prepare prompt
    user_content = f"""
WEBSITE CONTENT:
{clean_text}

USER QUESTION:
{user_message}
"""

    # 4️⃣ Call LLM
    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0.1
    )

    # 5️⃣ Send response back to frontend
    vast = completion.choices[0].message.content
    return jsonify({"result": vast})

# -------------------- RUN SERVER --------------------
if __name__ == "__main__":
    app.run(debug=True)
