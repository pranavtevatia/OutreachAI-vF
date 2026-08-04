"""
AI Engine using Groq API (Llama models).
Dynamic query generation, signal extraction, hook selection, B2B-grade draft generation.
"""

import streamlit as st
import json
import re
import time
import requests


def _call_llm(prompt, max_retries=3):
    """Call Groq API with retry logic."""
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("Groq API key not found in secrets.toml")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    time.sleep(1)
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            elif resp.status_code in [429, 413]:
                wait = 30  # Wait full minute for TPM reset
                time.sleep(wait)
            else:
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    st.error(f"Groq API error: {resp.status_code} — {resp.text[:200]}")
                    return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                st.error(f"Groq API error: {str(e)}")
                return None
    return None


def _parse_json(text, fallback=None):
    """Safely parse JSON from AI response."""
    if not text:
        return fallback
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for pattern in [r'\[.*\]', r'\{.*\}']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    continue
    return fallback


def format_research(research_data):
    """Convert research results into readable text for prompts."""
    sections = []
    for source in research_data["research_sources"]:
        if source["status"] == "success" and source["results"]:
            section = f"\n--- {source['source']} ---\n"
            for r in source["results"]:
                section += f"* {r.get('title', 'No title')}\n  {r.get('content', '')[:400]}\n  URL: {r.get('url', '')}\n\n"
            sections.append(section)
    return "\n".join(sections) if sections else "No research results found."


# ════════════════════════════════════════════════════════════════
# DYNAMIC QUERY GENERATION
# ════════════════════════════════════════════════════════════════

def generate_search_queries(company_name, campaign, prospect_name=None, specific_source=None, industry=None):
    """
    Generate tailored search queries based on campaign profile.
    All queries are anchored to pain points, not generic company news.
    """
    industry_hint = f"\nCOMPANY INDUSTRY: {industry}" if industry else "\nCOMPANY INDUSTRY: Not specified — figure it out from the company name."
    prompt = f"""You are a B2B sales research strategist. Generate search queries to find information about a target company that is relevant to what the seller is offering.

SELLER PROFILE:
- Company: {campaign.get('company_name', 'N/A')}
- What they sell: {campaign.get('value_prop', 'N/A')}
- Pain points they solve: {campaign.get('pain_points', 'N/A')}
- Signals that indicate need: {campaign.get('signals', 'N/A')}
- Target persona titles: {campaign.get('target_persona', 'N/A')}
- Target industries: {campaign.get('target_industries', 'N/A')}
- How an expert would research: {campaign.get('dream_research', 'N/A')}

TARGET COMPANY: {company_name}{industry_hint}
PROSPECT NAME: {prospect_name or 'Not specified'}

Generate search queries in these exact tiers:

TIER 1 - COMPANY + PAIN POINT (exactly 3 queries):
Search for evidence of the SPECIFIC problems the seller solves at this company.
Think: does this company show signs of the pain points listed above?
Example for an employee engagement seller targeting Zomato:
- "Zomato attrition rate employee turnover"
- "Zomato employee satisfaction Glassdoor reviews"
- "Zomato work culture burnout employee engagement"
Example for a cybersecurity seller targeting Razorpay:
- "Razorpay data breach security incident"
- "Razorpay SOC2 compliance audit"
- "Razorpay cloud security infrastructure"

TIER 2 - COMPANY + LEADERSHIP (exactly 1 query):
Search for relevant decision-makers at this company matching the target persona.
Example: "Zomato CHRO VP People Head HR" or "Razorpay CISO security team"

TIER 3 - INDUSTRY + PAIN POINT TRENDS (exactly 1 query):
Search for industry-wide trends related to the pain points. This ALWAYS provides usable signals even if the company has no direct data.
{"Use the industry: " + industry + " for this query." if industry else f"Figure out what industry {company_name} is in and search for pain point trends there."}
Example: "food delivery India employee attrition trends 2026"
Example: "fintech India cybersecurity threats compliance 2026"

TIER 4 - PROSPECT + TOPIC (exactly 1 query, only if prospect name given):
Has this person publicly spoken about the relevant topic?
Example: "Priya Sharma employee engagement attrition culture"
If no prospect name, set this to empty array.

RULES:
- Each query should be 4-7 words. No quotes in the query. No OR operators.
- Every query must relate to the seller's pain points or signals. NO generic searches.
- Do NOT search for general company news, funding, or acquisitions unless directly related to the pain points.

Return ONLY JSON:
{{
    "tier1_pain_point": ["query1", "query2", "query3"],
    "tier2_leadership": ["query"],
    "tier3_industry": ["query"],
    "tier4_prospect": ["query"] or []
}}"""

    text = _call_llm(prompt)
    queries = _parse_json(text, None)

    if not queries:
        # Fallback: generate basic queries from campaign keywords
        pain_words = campaign.get('pain_points', '')[:50].replace('\n', ' ')
        persona = campaign.get('target_persona', '')[:30]
        queries = {
            "tier1_pain_point": [
                f"{company_name} {pain_words}",
                f"{company_name} Glassdoor employee reviews",
                f"{company_name} employee challenges problems",
            ],
            "tier2_leadership": [f"{company_name} {persona}"],
            "tier3_industry": [f"{industry or 'industry'} challenges trends 2026"],
            "tier4_prospect": [f"{prospect_name} {pain_words}"] if prospect_name else [],
        }

    # Add custom source if provided
    if specific_source:
        if "." in specific_source:
            queries["custom_source"] = [f"site:{specific_source} {company_name}"]
        else:
            queries["custom_source"] = [f"{company_name} {specific_source}"]
    else:
        queries["custom_source"] = []

    return queries


# ════════════════════════════════════════════════════════════════
# PROSPECT PARSING & VERIFICATION
# ════════════════════════════════════════════════════════════════

def parse_linkedin_prospects(raw_results, company_name):
    """Parse LinkedIn search results into structured prospect data."""
    if not raw_results:
        return []

    results_text = "\n".join([
        f"Title searched: {r['title_searched']}\nResult: {r['result_title']}\nSnippet: {r['snippet']}\nURL: {r['url']}"
        for r in raw_results
    ])

    prompt = f"""Parse these LinkedIn search results and extract real people who work at {company_name}.

SEARCH RESULTS:
{results_text}

Return ONLY a JSON array of people found. Deduplicate by name. Only include people who clearly work at {company_name}.
[
  {{
    "name": "Full Name",
    "title": "Their job title",
    "linkedin_url": "URL if available",
    "confidence": "HIGH/MEDIUM/LOW that they currently work at {company_name}"
  }}
]
Return empty array [] if no clear matches found."""

    text = _call_llm(prompt)
    return _parse_json(text, [])


def check_prospect_company_match(research_data):
    """Check if prospect still works at the stated company."""
    research_text = format_research(research_data)
    prospect = research_data.get("prospect_name", "Unknown")
    company = research_data.get("company_name", "Unknown")

    prompt = f"""Analyze this research about {prospect} at {company}.

RESEARCH:
{research_text}

Check:
1. Is {prospect} still at {company}, or did they move to another company?
2. Is there conflicting information about where they work?

Return ONLY JSON:
{{
  "match": true,
  "current_company": "{company}",
  "new_company": null,
  "confidence": "MEDIUM",
  "warning": null
}}"""

    text = _call_llm(prompt)
    return _parse_json(text, {"match": True, "warning": None})


# ════════════════════════════════════════════════════════════════
# SIGNAL EXTRACTION
# ════════════════════════════════════════════════════════════════

def extract_signals(research_data, campaign):
    """Extract and score signals from research data against campaign context."""
    research_text = format_research(research_data)
    tier1_had_results = research_data.get("tier1_had_results", True)
    industry_count = research_data.get("industry_results_count", 0)

    context_note = ""
    if not tier1_had_results and industry_count > 0:
        context_note = """
IMPORTANT: No company-specific pain point data was found. 
Use the INDUSTRY TRENDS data to identify relevant signals. 
Frame signals as industry-wide patterns that likely affect this company too.
These are still valuable — the outreach will reference industry context instead of company-specific events.
"""

    prompt = f"""Extract outreach signals from this research.

SELLER: {campaign.get('company_name', 'N/A')} — {campaign.get('value_prop', 'N/A')}
PAIN POINTS: {campaign.get('pain_points', 'N/A')}
SIGNALS TO FIND: {campaign.get('signals', 'N/A')}
SENSITIVE TOPICS: {campaign.get('sensitive_topics', 'N/A')}
PROSPECT: {research_data.get('prospect_name', 'Not specified')} at {research_data['company_name']}
{context_note}

RESEARCH:
{research_text}

Find signals connecting this company to the seller's value prop. Prioritize: direct pain point evidence > circumstantial evidence > industry trends.

Source quality: major news/Glassdoor/app stores = high credibility (boost score). Complaint sites like pissedconsumer = low credibility (reduce score 2-3 points).

Sensitivity: "none" = safe, "low" = careful, "high" = avoid as hook.

Return ONLY JSON array:
[{{"signal": "what happened", "source": "where from", "source_url": "url", "relevance_score": 7, "connection": "why it matters for seller", "sensitivity": "none", "recency": "how recent"}}]

Score 1-10. Return at least 2 signals. Use industry data if company data is thin."""

    text = _call_llm(prompt)
    signals = _parse_json(text, [])
    if isinstance(signals, list):
        signals.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return signals


# ════════════════════════════════════════════════════════════════
# HOOK SELECTION & CONFIDENCE
# ════════════════════════════════════════════════════════════════

def select_hook_and_confidence(signals, campaign, research_data):
    """Select best hook and determine confidence level."""
    total_results = research_data.get("total_results", 0)
    company_results = research_data.get("company_results_count", 0)
    prospect_results = research_data.get("prospect_results_count", 0)
    industry_results = research_data.get("industry_results_count", 0)
    num_signals = len(signals) if signals else 0

    if not signals:
        return {
            "selected_hook": None,
            "confidence": "LOW",
            "reasoning": "No signals identified from research. Insufficient data for personalized outreach.",
            "warnings": ["Very limited public information available."],
            "data_quality": {
                "total_results": total_results,
                "signals_found": 0,
                "company_data": "thin" if company_results < 3 else "adequate",
                "prospect_data": "none" if prospect_results == 0 else "available",
            },
        }

    prompt = f"""Select the BEST signal as outreach hook.

SELLER: {campaign.get('company_name', 'N/A')} — {campaign.get('value_prop', 'N/A')}
SENSITIVE TOPICS TO AVOID: {campaign.get('sensitive_topics', 'N/A')}
PROSPECT: {research_data.get('prospect_name', 'N/A')} at {research_data['company_name']}

SIGNALS:
{json.dumps(signals, indent=2)}

DATA QUALITY:
- Total research results: {total_results}
- Company-level results: {company_results}
- Industry-level results: {industry_results}
- Prospect-level results: {prospect_results}
- Signals found: {num_signals}

SELECTION PRIORITY: 
1. Company-specific pain point evidence (strongest)
2. Circumstantial evidence at company
3. Industry trend (good fallback)
4. Avoid high-sensitivity as primary hook

CONFIDENCE RULES:
- HIGH: Company-specific signal with score >= 7 AND 3+ signals AND no high-sensitivity on hook
- MEDIUM: Industry-level signal used OR only 1-2 signals OR prospect data thin
- LOW: No relevant signals OR all signals high-sensitivity OR very thin data overall

Return ONLY JSON:
{{
  "selected_hook": "signal description chosen",
  "confidence": "HIGH/MEDIUM/LOW",
  "reasoning": "Why this hook, 2-3 sentences",
  "warnings": [],
  "alternative_hooks": []
}}"""

    text = _call_llm(prompt)
    result = _parse_json(text, None)
    if result:
        result["data_quality"] = {
            "total_results": total_results,
            "signals_found": num_signals,
            "company_data": "thin" if company_results < 3 else "adequate",
            "prospect_data": "none" if prospect_results == 0 else "available",
            "industry_data": "available" if industry_results > 0 else "none",
        }
        return result

    return _fallback_hook(signals, research_data)


def _fallback_hook(signals, research_data):
    """Fallback when AI hook selection fails."""
    if signals:
        top = signals[0]
        score = top.get("relevance_score", 0)
        conf = "HIGH" if score >= 7 else "MEDIUM" if score >= 4 else "LOW"
        return {
            "selected_hook": top["signal"],
            "confidence": conf,
            "reasoning": "Auto-selected highest scoring signal.",
            "warnings": ["Hook was auto-selected — review carefully."],
        }
    return {
        "selected_hook": None,
        "confidence": "LOW",
        "reasoning": "No signals available.",
        "warnings": ["No data found."],
    }


# ════════════════════════════════════════════════════════════════
# DRAFT GENERATION — B2B SALES GRADE
# ════════════════════════════════════════════════════════════════

def generate_draft(hook_data, signals, research_data, campaign):
    """Generate B2B sales-grade outreach email draft."""
    hook_text = hook_data.get("selected_hook") if hook_data else None
    confidence = hook_data.get("confidence", "LOW") if hook_data else "LOW"

    if not hook_text:
        approach = "industry-level"
        hook_text = f"General relevance to their role at {research_data['company_name']}"
    elif research_data.get("company_results_count", 0) > 0 and research_data.get("prospect_results_count", 0) > 0:
        approach = "fully-personalized"
    elif research_data.get("company_results_count", 0) > 0:
        approach = "company-signal-only"
    else:
        approach = "industry-level"

    sample_email = campaign.get("sample_email", "")
    sample_instruction = ""
    if sample_email:
        sample_instruction = f"\nSTYLE REFERENCE ONLY (match tone and structure, DO NOT copy any company names or specifics):\n{sample_email}\n"

    prospect_name = research_data.get("prospect_name", "the prospect")

    prompt = f"""Write a B2B outreach email for {research_data['company_name']} ONLY. Never use names or specifics from the style reference.

SELLER: {campaign.get('company_name', 'N/A')} — {campaign.get('value_prop', 'N/A')}
SENDER: {campaign.get('sender_name', 'N/A')}
PROSPECT: {prospect_name} at {research_data['company_name']}
APPROACH: {approach}
HOOK: {hook_text}
HOOK REASONING: {hook_data.get('reasoning', '') if hook_data else ''}
CONFIDENCE: {confidence}
PURPOSE: {campaign.get('purpose', 'First touch cold outreach')}
{sample_instruction}

STRUCTURE:
1. OPENING: Reference the specific hook with a real detail. No "Hope this finds you well."
2. BRIDGE: Connect hook to their pain. 1-2 sentences. Don't sell yet.
3. VALUE: What you do, framed as THEIR outcome. One sentence.
4. CTA: Soft ask — "worth a quick chat?" Not "schedule a demo."
5. SIGN-OFF: First name, title, company on next line. No elaborate signature.

RULES:
- 4-6 sentences total. Short paragraphs. Mobile-friendly.
- Subject: 3-7 lowercase words, specific, like a text from a colleague.
- Sound human. No "synergies", "circle back", "leverage", "I came across your profile."
- If company-signal-only: focus on company context, don't pretend you know the person.
- If industry-level: frame around industry trends, acknowledge you're inferring.

Return ONLY JSON:
{{"subject_line": "subject", "body": "email body with \\n for line breaks", "approach_note": "angle taken"}}"""

    text = _call_llm(prompt)
    return _parse_json(text, {
        "subject_line": "Draft generation issue",
        "body": "The AI couldn't generate a draft. Try again or write manually based on the signals.",
        "approach_note": "Error in generation",
    })
