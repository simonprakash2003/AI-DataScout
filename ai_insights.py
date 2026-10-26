"""Hybrid AI insights: reliable local analytics plus optional LLM summaries."""
from __future__ import annotations
import os
import requests
import pandas as pd


def local_insights(df: pd.DataFrame) -> str:
    """Generate transparent insights without an external AI service."""
    if df.empty:
        return "No clinic records are available yet. Upload a permitted dataset or load the sample."
    lines = [
        f"- Records available: **{len(df)}**.",
        f"- States/territories represented: **{df['state'].replace('', pd.NA).dropna().nunique()}**.",
        f"- Records with a website: **{int(df['website'].fillna('').astype(str).str.strip().ne('').sum())}**.",
        f"- Records with a published phone number: **{int(df['phone'].fillna('').astype(str).str.strip().ne('').sum())}**.",
    ]
    states = df["state"].fillna("").astype(str).str.strip()
    counts = states[states.ne("")].value_counts()
    if not counts.empty:
        lines.append(f"- Most represented state in this dataset: **{counts.index[0]}** ({int(counts.iloc[0])} records).")
    services = df["services"].fillna("").astype(str).str.lower()
    if services.str.contains("general practice|general practitioner", regex=True).any():
        lines.append("- The dataset includes records whose listed services mention general practice.")
    lines.append("- These are descriptive statistics for the supplied dataset, not a complete census of Australian clinics.")
    return "\n".join(lines)


def ai_summary(df: pd.DataFrame, api_key: str | None = None) -> str:
    """Optional OpenAI API summary; falls back safely to local insights if no key is configured."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return local_insights(df) + "\n\n*AI API not configured; showing transparent local insights.*"
    sample = df.head(40).fillna("").astype(str).to_dict(orient="records")
    prompt = (
        "Summarize this small dataset of publicly listed healthcare clinic directory records. "
        "Only describe patterns supported by the supplied rows. Do not infer medical quality, "
        "recommend treatment, invent facts, or expose information beyond the provided fields. "
        "Mention limitations and missing data. Dataset sample (JSON): " + str(sample)
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [
                {"role": "system", "content": "You are a cautious data analyst. Do not invent facts."},
                {"role": "user", "content": prompt},
            ], "temperature": 0.2},
            timeout=25,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        return local_insights(df) + f"\n\n*AI API unavailable; local insights shown instead. Details: {type(exc).__name__}.*"
