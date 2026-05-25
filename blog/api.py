"""
151 Blog — AI API Server
Run with: python blog/api.py
Serves the blog at http://localhost:5000 and provides AI endpoints.
"""

import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=str(Path(__file__).parent))
CORS(app)

BLOG_DIR = Path(__file__).parent

SYSTEM_BASE = """You are the AI research assistant for 151 — an independent investment research \
publication. 151 covers global markets, macro, current affairs, and investment ideas with sharp, \
witty, intellectually honest analysis.

Voice guidelines:
- Confident but humble — acknowledge uncertainty where it exists
- Sharp and direct — no filler, no hedging without reason
- Intellectually curious — entertain counter-arguments seriously
- Think Matt Levine meets an independent analyst: smart, a bit sardonic, always useful

Keep responses concise (2-4 short paragraphs max) unless depth is genuinely needed. \
Never recommend specific securities as financial advice."""


def get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


@app.route("/api/chat", methods=["POST"])
def chat():
    client = get_client()
    if not client:
        return jsonify({"error": "API key not configured"}), 503

    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    article_context = data.get("articleContext", "")

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    system = SYSTEM_BASE
    if article_context:
        system += f"\n\nYou are answering questions about this specific article from 151:\n\n---\n{article_context[:6000]}\n---\n\nStay grounded in the article content but bring your own analysis when relevant."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=messages[-20:],  # keep last 20 turns
        )
        return jsonify({"response": response.content[0].text})
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summary", methods=["POST"])
def summary():
    client = get_client()
    if not client:
        return jsonify({"error": "API key not configured"}), 503

    content = (request.get_json(silent=True) or {}).get("content", "")
    if not content:
        return jsonify({"error": "No content provided"}), 400

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system="You are a sharp financial analyst. Summarize the article in exactly 3 bullet points. Each bullet is one punchy sentence capturing a key insight. Format: • [insight]",
            messages=[{"role": "user", "content": f"Summarize:\n\n{content[:6000]}"}],
        )
        return jsonify({"summary": response.content[0].text})
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/debate", methods=["POST"])
def debate():
    client = get_client()
    if not client:
        return jsonify({"error": "API key not configured"}), 503

    content = (request.get_json(silent=True) or {}).get("content", "")
    if not content:
        return jsonify({"error": "No content provided"}), 400

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system="You are a sharp devil's advocate investor. Given an article's thesis, argue the strongest possible counter-case with 2-3 short paragraphs. Be specific, cite real risks, and don't strawman the original argument. End with what would change your mind.",
            messages=[{"role": "user", "content": f"Counter-argument to this thesis:\n\n{content[:6000]}"}],
        )
        return jsonify({"debate": response.content[0].text})
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/explain", methods=["POST"])
def explain():
    client = get_client()
    if not client:
        return jsonify({"error": "API key not configured"}), 503

    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"error": "No content provided"}), 400

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system="You are explaining a finance article to someone smart but new to investing. Rewrite the core ideas in plain English with a concrete analogy. No jargon. 2-3 short paragraphs.",
            messages=[{"role": "user", "content": f"Explain this simply:\n\n{content[:6000]}"}],
        )
        return jsonify({"explain": response.content[0].text})
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def status():
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    return jsonify({"ai_ready": has_key})


# Serve the blog static files
@app.route("/")
def index():
    return send_from_directory(BLOG_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    try:
        return send_from_directory(BLOG_DIR, path)
    except Exception:
        return send_from_directory(BLOG_DIR, "index.html")


if __name__ == "__main__":
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("\n⚠  No ANTHROPIC_API_KEY found. AI features will show a setup prompt.")
        print("   Add your key to .env to enable them.\n")
    else:
        print("\n✦ AI features enabled.\n")
    print("Starting 151 blog at http://localhost:5000\n")
    app.run(debug=True, port=5000, host="0.0.0.0")
