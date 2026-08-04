"""
AI Outreach Engine — Personalized B2B outreach powered by AI research.
Zamp AI Solutions Associate Case Study (PS-3).
"""

import streamlit as st
import json
import time
import urllib.parse
from datetime import datetime
from utils.research import run_research_with_queries, find_prospects_via_linkedin, get_tavily_client
from utils.ai_engine import (
    extract_signals,
    select_hook_and_confidence,
    generate_draft,
    check_prospect_company_match,
    parse_linkedin_prospects,
    format_research,
    generate_search_queries,
)
from utils.hunter import verify_email, find_email, domain_search

# ─── Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="AI Outreach Engine", page_icon="🎯", layout="wide")

# ─── Session State ─────────────────────────────────────────────
defaults = {
    "campaign": None,
    "run_history": [],
    "current_run": None,
    "discovered_prospects": [],
    "discovered_company": "",
    "discovered_domain": "",
    "prospect_flow": "initial",
    "continue_without": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("🎯 AI Outreach Engine")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["⚙️ Campaign Setup", "🚀 New Prospect Run", "📊 Dashboard"])

if st.session_state.campaign:
    c = st.session_state.campaign
    st.sidebar.markdown("---")
    st.sidebar.success(f"✅ **{c['campaign_name']}**\n\n{c['company_name']}")
    st.sidebar.caption(f"Runs: {len(st.session_state.run_history)}")
else:
    st.sidebar.markdown("---")
    st.sidebar.warning("⚠️ Set up a campaign first")


# ════════════════════════════════════════════════════════════════
# SCREEN 1: CAMPAIGN SETUP
# ════════════════════════════════════════════════════════════════
if page == "⚙️ Campaign Setup":
    st.title("⚙️ Outbound Campaign Setup")
    st.markdown("Configure your company profile and campaign in one place. This shapes all AI research and drafting.")

    cp = st.session_state.campaign or {}

    st.markdown("### 🏢 About Your Company")
    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("Company Name *", value=cp.get("company_name", ""), placeholder="e.g. TalentPulse")
    with col2:
        value_prop = st.text_input("What do you sell? (one-line) *", value=cp.get("value_prop", ""), placeholder="e.g. Employee engagement platform reducing attrition via real-time sentiment analytics")

    pain_points = st.text_area("Pain points you solve", value=cp.get("pain_points", ""), placeholder="e.g.\n- High attrition they can't explain\n- No real-time pulse on employee sentiment\n- HR decisions made on gut feel, not data", height=100)

    st.markdown("### 🎯 Campaign Details")
    col1, col2 = st.columns(2)
    with col1:
        campaign_name = st.text_input("Campaign Name *", value=cp.get("campaign_name", ""), placeholder="e.g. Q3 CHRO Cold Outreach")
    with col2:
        target_persona = st.text_input("Target persona (titles) *", value=cp.get("target_persona", ""), placeholder="e.g. CHRO, VP People, Head of HR")

    purpose = st.text_area(
        "Purpose of this outreach *",
        value=cp.get("purpose", ""),
        placeholder="Describe what you want to achieve.\n\nExamples:\n• First touch to introduce our product to HR leaders who haven't heard of us\n• Re-engage prospects who went silent with our new feature\n• Follow up after People Matters TechHR conference\n• Reach out to companies using [competitor] and show them a better way",
        height=120,
    )

    st.markdown("### 📡 Signals & Research")

    signals_help = """**Example signals from real companies:**

🔹 **TalentPulse** (employee engagement SaaS):
"Rapid hiring surges, leadership turnover, return-to-office announcements, Glassdoor rating drops, culture initiatives, DE&I programs, new CHRO appointment"

🔹 **ShieldNet** (cybersecurity):
"Data breaches, SOC2/ISO compliance deadlines, cloud migration, new CISO hire, regulatory changes, M&A activity"

🔹 **PayFlow** (B2B payments fintech):
"International expansion, vendor/supplier partnerships, payment processing complaints, CFO hire, funding rounds, ERP migration"
"""
    signals = st.text_area(
        "Signals that indicate a prospect might need your product",
        value=cp.get("signals", ""),
        placeholder="Describe in your own words — what events, situations, or changes suggest they might need what you sell?",
        height=100,
        help=signals_help,
    )

    dream_research = st.text_area(
        "💡 What and how would you research if you had unlimited time? Explain in detail so our AI employee understands from the expert.",
        value=cp.get("dream_research", ""),
        placeholder="e.g. I'd check their LinkedIn for posts about culture challenges. Then Glassdoor reviews for patterns — burnout, management complaints. Check if they hired or lost senior HR leaders recently. Look at careers page for open roles. Search for press — funding, layoffs, DE&I initiatives...",
        height=140,
    )

    sensitive_topics = st.text_area("Topics to handle carefully or avoid", value=cp.get("sensitive_topics", ""), placeholder="e.g. Don't reference layoffs directly, avoid mentioning lawsuits, don't name competitors", height=80)

    st.markdown("### ✉️ Email Style")

    sample_email = st.text_area(
        "Paste a sample email that worked well (teaches the AI your voice & style)",
        value=cp.get("sample_email", ""),
        placeholder="Paste an outreach email you've sent before that got replies. The AI will match this tone and structure.",
        height=140,
    )

    st.markdown("### 👤 Sender Info")
    col1, col2 = st.columns(2)
    with col1:
        sender_name = st.text_input("Your name (SDR sending emails)", value=cp.get("sender_name", ""), placeholder="e.g. Rahul")
    with col2:
        sender_email = st.text_input("Your email (for sending)", value=cp.get("sender_email", ""), placeholder="e.g. rahul@talentpulse.com")

    st.markdown("---")
    if st.button("💾 Save Campaign", type="primary", use_container_width=True):
        if not all([company_name, value_prop, campaign_name, target_persona, purpose]):
            st.error("Please fill in all required fields (marked with *)")
        else:
            st.session_state.campaign = {
                "company_name": company_name, "value_prop": value_prop, "pain_points": pain_points,
                "campaign_name": campaign_name, "target_persona": target_persona, "purpose": purpose,
                "signals": signals, "dream_research": dream_research, "sensitive_topics": sensitive_topics,
                "sample_email": sample_email, "sender_name": sender_name, "sender_email": sender_email,
                "created_at": datetime.now().isoformat(),
            }
            st.success(f"✅ Campaign **{campaign_name}** saved! Go to 'New Prospect Run' to start.")
            st.balloons()


# ════════════════════════════════════════════════════════════════
# SCREEN 2: NEW PROSPECT RUN
# ════════════════════════════════════════════════════════════════
elif page == "🚀 New Prospect Run":
    st.title("🚀 New Prospect Run")

    if not st.session_state.campaign:
        st.warning("⚠️ Set up a campaign first.")
        st.stop()

    camp = st.session_state.campaign
    st.markdown(f"**Campaign:** {camp['campaign_name']}  ·  **Selling:** {camp['value_prop']}")
    st.markdown("---")

    # ── Input Form ──
    st.markdown("### Prospect Details")
    st.caption("Only company name is required. Click 'Show Prospects' to find people, or go straight to drafting.")

    col1, col2 = st.columns(2)
    with col1:
        input_company = st.text_input("Company Name *", placeholder="e.g. Razorpay")
    with col2:
        input_industry = st.text_input("Industry *", placeholder="e.g. Food delivery, Fintech (2-3 words)")

    col1, col2 = st.columns(2)
    with col1:
        input_domain = st.text_input("Company Domain", placeholder="e.g. razorpay.com (helps find emails)")
    with col2:
        # Dropdown if prospects were discovered, otherwise text input
        if st.session_state.discovered_prospects:
            prospect_options = ["(No prospect — company-only research)"] + [
                f"{p['name']} — {p.get('title', '?')}" for p in st.session_state.discovered_prospects
            ]
            selected = st.selectbox("Select Prospect", prospect_options)
            if not selected.startswith("(No prospect"):
                idx = prospect_options.index(selected) - 1
                input_name = st.session_state.discovered_prospects[idx].get("name", "")
            else:
                input_name = ""
        else:
            input_name = st.text_input("Prospect Name", placeholder="Leave blank or click Show Prospects")

    col1, col2 = st.columns(2)
    with col1:
        input_title = st.text_input("Title", placeholder="e.g. VP Customer Experience")
    with col2:
        input_email = st.text_input("Email", placeholder="Leave blank — we'll find it")

    input_linkedin = st.text_input("LinkedIn URL", placeholder="Optional")
    input_source = st.text_input("Any specific source to research this company?", placeholder="e.g. yourstory.com, a subreddit, specific blog URL")

    st.markdown("---")

    # ── TWO TOP-LEVEL BUTTONS ──
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        show_prospects_clicked = st.button("👤 Show Prospects", use_container_width=True, disabled=bool(input_name))
    with col_btn2:
        run_clicked = st.button("🔍 Research & Generate Draft", type="primary", use_container_width=True)

    # ── SHOW PROSPECTS LOGIC (lightweight, separate from main pipeline) ──
    if show_prospects_clicked:
        if not input_company:
            st.error("Enter a company name first.")
            st.stop()
        with st.spinner("Searching for prospects..."):
            tavily_client = get_tavily_client()
            if tavily_client:
                linkedin_raw = find_prospects_via_linkedin(tavily_client, input_company, camp["target_persona"])
                parsed = parse_linkedin_prospects(linkedin_raw, input_company) if linkedin_raw else []
                if parsed:
                    st.session_state.discovered_prospects = parsed[:6]
                    st.session_state.discovered_company = input_company
                    st.rerun()
                else:
                    st.warning("No prospects found. You can enter a name manually or click 'Research & Generate Draft' for company-only research.")
            else:
                st.error("Tavily API key not configured.")
        st.stop()

    # ── MAIN PIPELINE ──
    if run_clicked:
        if not input_company:
            st.error("Company name is required.")
            st.stop()
        if not input_industry:
            st.error("Industry is required (2-3 words).")
            st.stop()

        # ── Company Disambiguation ──
        # Check if company name is ambiguous (common name, multiple companies)
        if not input_domain:
            with st.status("🔍 Verifying company identity...", expanded=True) as s_disambig:
                tavily_check = get_tavily_client()
                if tavily_check:
                    from utils.research import _search
                    check_result = _search(tavily_check, f"{input_company} company official website", "Company Check")
                    if check_result["results"]:
                        # Use Groq to check if results point to multiple different companies
                        results_text = "\n".join([
                            f"- {r.get('title', '')}: {r.get('content', '')[:200]} ({r.get('url', '')})"
                            for r in check_result["results"][:5]
                        ])
                        disambig_prompt = f"""These are search results for "{input_company} company":

{results_text}

Are these results about ONE clear company, or do they refer to MULTIPLE DIFFERENT companies with similar names?

Rules:
- If one company dominates (appears in 3+ results) and others are obscure, treat it as ONE company.
- Only flag as MULTIPLE if there are 2+ genuinely distinct, well-known companies with this name.

Return ONLY JSON:
{{
  "ambiguous": false,
  "primary_company": "Full company name and what they do",
  "primary_domain": "domain.com",
  "alternatives": []
}}

If ambiguous:
{{
  "ambiguous": true,
  "options": [
    {{"name": "CRED (fintech app)", "domain": "cred.club", "description": "Indian fintech credit card bill payment app"}},
    {{"name": "CRED (crypto)", "domain": "cred.com", "description": "Crypto lending platform"}}
  ]
}}"""
                        from utils.ai_engine import _call_llm, _parse_json
                        disambig_text = _call_llm(disambig_prompt)
                        disambig_result = _parse_json(disambig_text, {"ambiguous": False})

                        if disambig_result and disambig_result.get("ambiguous") and disambig_result.get("options"):
                            s_disambig.update(label="⚠️ Multiple companies found with this name", state="complete")
                            st.warning(f"⚠️ **\"{input_company}\"** matches multiple companies:")
                            options = disambig_result["options"]
                            for j, opt in enumerate(options):
                                col_info, col_btn = st.columns([3, 1])
                                with col_info:
                                    st.markdown(f"**{opt['name']}** — {opt.get('description', '')}\n\n🌐 {opt.get('domain', '')}")
                                with col_btn:
                                    def _select_company(opt=opt):
                                        st.session_state.auto_run = True
                                        st.session_state.auto_run_company = opt["name"].split("(")[0].strip()
                                        st.session_state.auto_run_domain = opt.get("domain", "")
                                        st.session_state.auto_run_source = ""
                                        st.session_state.selected_prospect = {"name": "", "email": "", "title": ""}
                                    st.button(f"Select", key=f"disambig_{j}", on_click=_select_company)
                            st.stop()
                        else:
                            # Not ambiguous — auto-fill domain if found
                            if disambig_result and disambig_result.get("primary_domain"):
                                input_domain = disambig_result["primary_domain"]
                                domain = input_domain
                                st.write(f"✅ Identified: **{disambig_result.get('primary_company', input_company)}** ({input_domain})")
                            s_disambig.update(label=f"✅ Company verified: {input_company}", state="complete")
                    else:
                        s_disambig.update(label="✅ Company check complete", state="complete")

        # Initialize run data
        run = {
            "input_company": input_company,
            "input_domain": input_domain,
            "input_industry": input_industry,
            "input_name": input_name,
            "input_title": input_title,
            "input_email": input_email,
            "campaign": camp["campaign_name"],
            "started_at": datetime.now().isoformat(),
            "stages": {},
        }

        prospect_name = input_name if input_name else None
        prospect_email = input_email
        domain = input_domain

        st.markdown("### 🔄 Live Run View")
        progress = st.progress(0)

        # ────────────────────────────────────────────────
        # STAGE 0: INPUT ENRICHMENT
        # ────────────────────────────────────────────────
        with st.status("📋 Stage 0: Input Enrichment", expanded=True) as s0:

            # Auto-infer domain if not provided
            if not domain:
                st.write(f"Inferring domain for {input_company}...")
                domain = input_company.lower().replace(" ", "") + ".com"
                st.write(f"Using domain: **{domain}** (verify if incorrect)")

            if prospect_name:
                st.write(f"✅ Prospect: **{prospect_name}** at **{input_company}**")
                s0.update(label=f"✅ Stage 0: {prospect_name} at {input_company}", state="complete")
            else:
                st.write(f"No prospect specified — running **company-only research** for **{input_company}**")
                s0.update(label=f"✅ Stage 0: Company-only research for {input_company}", state="complete")

        progress.progress(10)

        # ────────────────────────────────────────────────
        # STAGE 1: EMAIL VERIFICATION / FINDING
        # ────────────────────────────────────────────────
        with st.status("📧 Stage 1: Email Verification", expanded=True) as s1:
            email_status = "unknown"

            if prospect_email:
                st.write(f"Verifying **{prospect_email}**...")
                v = verify_email(prospect_email)
                email_status = v.get("status", "unknown")

                if email_status == "valid":
                    st.write(f"✅ Email verified — valid and deliverable")
                    s1.update(label="✅ Stage 1: Email verified", state="complete")
                elif email_status == "invalid":
                    st.write(f"❌ Email invalid — attempting to find correct email...")
                    # Try to find via Hunter
                    parts = prospect_name.split()
                    if len(parts) >= 2 and domain:
                        found = find_email(parts[0], parts[-1], domain)
                        if found:
                            prospect_email = found["email"]
                            st.write(f"✅ Found alternative: **{prospect_email}** (confidence: {found['confidence']}%)")
                            email_status = "found"
                        else:
                            st.write("⚠️ Could not find alternate email. Draft will be generated without email.")
                            email_status = "not_found"
                    s1.update(label=f"⚠️ Stage 1: Original email invalid, {'found alternative' if email_status == 'found' else 'no alternative found'}", state="complete")
                else:
                    st.write(f"⚠️ Email status: {email_status} — proceed with caution")
                    s1.update(label=f"⚠️ Stage 1: Email status — {email_status}", state="complete")
            else:
                st.write("No email provided — attempting to find...")
                if prospect_name:
                    parts = prospect_name.split()
                else:
                    parts = []
                if len(parts) >= 2 and domain:
                    found = find_email(parts[0], parts[-1], domain)
                    if found:
                        prospect_email = found["email"]
                        st.write(f"✅ Found: **{prospect_email}** (confidence: {found['confidence']}%)")
                        email_status = "found"
                        s1.update(label=f"✅ Stage 1: Email found — {prospect_email}", state="complete")
                    else:
                        st.write("⚠️ Email not found. Searching company directory...")
                        contacts = domain_search(domain, limit=3)
                        if contacts:
                            st.write(f"Found {len(contacts)} contacts at {domain}:")
                            for c_item in contacts:
                                name = f"{c_item.get('first_name', '')} {c_item.get('last_name', '')}".strip()
                                st.write(f"  • {name} — {c_item.get('position', '?')} — {c_item.get('email', '?')}")
                        email_status = "not_found"
                        s1.update(label="⚠️ Stage 1: Email not found", state="complete")
                else:
                    st.write("⚠️ Need full name and domain to find email. Continuing without.")
                    email_status = "not_found"
                    s1.update(label="⚠️ Stage 1: Insufficient data for email lookup", state="complete")

            run["stages"]["email"] = {"email": prospect_email, "status": email_status}
            run["prospect_email"] = prospect_email

        progress.progress(20)

        # ────────────────────────────────────────────────
        # STAGE 2: QUERY GENERATION & RESEARCH
        # ────────────────────────────────────────────────
        with st.status("🧠 Stage 2: Generating research strategy...", expanded=True) as s2:
            st.write(f"Analyzing campaign profile to generate targeted queries...")
            st.write(f"Focus: **{camp.get('pain_points', 'N/A')[:80]}...**")

            generated_queries = generate_search_queries(
                company_name=input_company,
                campaign=camp,
                prospect_name=prospect_name,
                specific_source=input_source if input_source else None,
                industry=input_industry if input_industry else None,
            )

            if generated_queries:
                st.write("**Generated queries:**")
                for tier, queries in generated_queries.items():
                    if queries:
                        for q in queries:
                            st.write(f"  🔍 {q}")

            s2.update(label="✅ Stage 2: Research strategy generated", state="complete")

        progress.progress(30)

        with st.status("🔍 Stage 3: Executing research...", expanded=True) as s3:
            research_data = run_research_with_queries(
                generated_queries=generated_queries,
                prospect_name=prospect_name,
                company_name=input_company,
            )

            if not research_data:
                st.error("Research failed. Check your Tavily API key.")
                st.stop()

            company_count = research_data["company_results_count"]
            prospect_count = research_data["prospect_results_count"]
            industry_count = research_data.get("industry_results_count", 0)
            total = research_data["total_results"]

            st.write(f"📊 Company + Pain Point data: **{company_count} results**")
            st.write(f"🌍 Industry trends: **{industry_count} results**")
            st.write(f"👤 Prospect data: **{prospect_count} results**")

            # Ghost company detection
            if company_count == 0 and industry_count > 0:
                st.warning(f"⚠️ **No company-specific data found** — using industry trends as primary signal source.")
                run["edge_case"] = "ghost_company"
            elif company_count == 0 and industry_count == 0:
                st.warning(f"⚠️ **Ghost company detected** — very limited data available.")
                run["edge_case"] = "ghost_company"

            s3.update(label=f"✅ Stage 3: Research complete — {total} results (Company: {company_count}, Industry: {industry_count}, Prospect: {prospect_count})", state="complete")
            run["stages"]["research"] = {"total": total, "company": company_count, "prospect": prospect_count, "industry": industry_count}

        progress.progress(45)

        # ────────────────────────────────────────────────
        # STAGE 3: PROSPECT-COMPANY MATCH CHECK
        # ────────────────────────────────────────────────
        with st.status("🔎 Stage 4: Prospect-Company Match", expanded=True) as s3:
            match_data = {"match": True, "warning": None}

            if prospect_name and prospect_count > 0:
                st.write(f"Checking if **{prospect_name}** is still at **{input_company}**...")
                match_data = check_prospect_company_match(research_data)

                if match_data and not match_data.get("match", True):
                    new_co = match_data.get("new_company", "another company")
                    st.error(f"⚠️ **{prospect_name}** appears to have left **{input_company}** → now at **{new_co}**")
                    run["edge_case"] = "prospect_left"

                    # Find replacements via Tavily LinkedIn search
                    st.write(f"Finding replacement contacts at {input_company}...")
                    tavily_repl = get_tavily_client()
                    repl_prospects = []
                    if tavily_repl:
                        repl_raw = find_prospects_via_linkedin(tavily_repl, input_company, camp["target_persona"])
                        repl_prospects = parse_linkedin_prospects(repl_raw, input_company) if repl_raw else []

                    if repl_prospects:
                        # Store replacements for dropdown on next run
                        st.session_state.discovered_prospects = repl_prospects[:5]
                        st.session_state.discovered_company = input_company

                        st.write(f"Found {len(repl_prospects)} alternative contacts:")
                        for rp in repl_prospects[:5]:
                            st.write(f"  • **{rp['name']}** — {rp.get('title', '?')}")

                        st.info(f"💡 Original prospect may now be at **{new_co}**. Select a replacement from the dropdown above and click Run again.")
                        st.stop()

                    # Continue but downgrade
                    prospect_name = None  # Reset to company-only mode
                    s3.update(label=f"⚠️ Stage 4: Prospect left company — switched to company-only mode", state="complete")
                elif match_data and match_data.get("warning"):
                    st.warning(f"⚠️ {match_data['warning']}")
                    s3.update(label="⚠️ Stage 3: Match uncertain", state="complete")
                else:
                    st.write(f"✅ {prospect_name} verified at {input_company}")
                    s3.update(label="✅ Stage 3: Prospect-company match confirmed", state="complete")
            else:
                st.write("Skipped — no prospect-specific data to verify")
                s3.update(label="⏭️ Stage 3: Skipped (no prospect data)", state="complete")

            run["stages"]["match"] = match_data

        progress.progress(55)

        # ────────────────────────────────────────────────
        # STAGE 4: SIGNAL EXTRACTION
        # ────────────────────────────────────────────────
        with st.status("🧠 Stage 5: Extracting & Scoring Signals", expanded=True) as s4:
            st.write(f"Analyzing research through **{camp['campaign_name']}** lens...")
            signals = extract_signals(research_data, camp)

            if signals:
                st.write(f"✅ **{len(signals)} signals** identified:")
                for i, sig in enumerate(signals[:5]):
                    score = sig.get("relevance_score", 0)
                    icon = "🟢" if score >= 7 else "🟡" if score >= 4 else "🔴"
                    st.write(f"  {icon} {sig['signal'][:80]}... (score: {score}/10)")
                s4.update(label=f"✅ Stage 4: {len(signals)} signals extracted", state="complete")
            else:
                st.write("⚠️ No clear signals found — will attempt industry-level approach")
                s4.update(label="⚠️ Stage 4: No signals found", state="complete")

            run["stages"]["signals"] = {"count": len(signals) if signals else 0, "data": signals}

        progress.progress(70)

        # ────────────────────────────────────────────────
        # STAGE 5: HOOK SELECTION & CONFIDENCE
        # ────────────────────────────────────────────────
        with st.status("🎯 Stage 6: Selecting Hook & Confidence", expanded=True) as s5:
            hook_data = select_hook_and_confidence(signals, camp, research_data)

            conf = hook_data.get("confidence", "LOW") if hook_data else "LOW"
            conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf, "⚪")

            if hook_data and hook_data.get("selected_hook"):
                st.write(f"**Hook:** {hook_data['selected_hook']}")
                st.write(f"**Confidence:** {conf_emoji} {conf}")
                st.write(f"**Reasoning:** {hook_data.get('reasoning', 'N/A')}")
                if hook_data.get("warnings"):
                    for w in hook_data["warnings"]:
                        if w:
                            st.write(f"⚠️ {w}")

                # Sensitive situation check
                if signals:
                    high_sens = [s for s in signals if s.get("sensitivity") == "high"]
                    if high_sens:
                        st.warning(f"🛑 **Sensitive situation detected:** {len(high_sens)} high-sensitivity signal(s) found. These were {'avoided' if hook_data.get('selected_hook') not in [s['signal'] for s in high_sens] else 'used with caution'} in hook selection.")
                        run["edge_case"] = run.get("edge_case", "") + " sensitive_situation"

            s5.update(label=f"✅ Stage 5: Hook selected — {conf_emoji} {conf}", state="complete")
            run["stages"]["hook"] = hook_data

        progress.progress(85)

        # ────────────────────────────────────────────────
        # STAGE 6: DRAFT GENERATION
        # ────────────────────────────────────────────────
        with st.status("✍️ Stage 7: Generating Draft", expanded=True) as s6:
            # Update research data with final prospect name
            research_data["prospect_name"] = prospect_name or f"Contact at {input_company}"

            st.write("Pausing briefly to avoid rate limits...")
            time.sleep(4)
            st.write("Generating draft...")

            draft = generate_draft(hook_data, signals, research_data, camp)
            if draft and draft.get("subject_line") and "issue" not in draft.get("subject_line", "").lower():
                st.write("✅ Draft ready for review")
                s6.update(label="✅ Stage 7: Draft generated", state="complete")
            else:
                st.write("⚠️ Draft generation had issues — try rerunning")
                s6.update(label="⚠️ Stage 7: Draft generation partial", state="complete")

            run["stages"]["draft"] = draft

        progress.progress(100)

        # ── Store final run data in session state ──
        run["prospect_name"] = prospect_name or f"Contact at {input_company}"
        run["prospect_company"] = input_company
        run["prospect_email"] = prospect_email
        run["confidence"] = hook_data.get("confidence", "LOW") if hook_data else "LOW"
        run["completed_at"] = datetime.now().isoformat()
        st.session_state.current_run = run

        # ════════════════════════════════════════════════
        # OUTPUT SECTION
        # ════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("## 📋 Results")

        # Confidence banner
        if conf == "HIGH":
            st.success(f"🟢 **HIGH CONFIDENCE** — Strong signal, clear connection. Light review and send.")
        elif conf == "MEDIUM":
            st.warning(f"🟡 **MEDIUM CONFIDENCE** — Decent signal, review before sending.")
        else:
            st.error(f"🔴 **LOW CONFIDENCE** — Weak signals or data gaps. Manual review required.")

        # Edge case alerts
        edge = run.get("edge_case", "")
        if "ghost_company" in edge:
            st.info("👻 **Ghost Company:** Limited public data. Draft uses industry-level signals.")
        if "prospect_left" in edge:
            st.info("🔄 **Prospect Left:** Contact may have left the company. Draft uses company-only signals.")
        if "sensitive" in edge:
            st.info("🛑 **Sensitive Situation:** High-sensitivity signals detected. Review hook carefully.")
        if match_data and match_data.get("warning"):
            st.info(f"⚠️ {match_data['warning']}")

        # ── Results Tabs ──
        tab_draft, tab_signals, tab_research = st.tabs(["📧 Email Draft", "📡 Signals", "🔍 Research Data"])

        with tab_draft:
            if draft:
                st.markdown(f"**To:** {prospect_email or '(email not found)'}")
                st.markdown(f"**Subject:** {draft.get('subject_line', 'N/A')}")
                st.markdown("---")
                body_text = draft.get("body", "").replace("\\n", "\n\n")
                st.markdown(body_text)
                st.markdown("---")
                st.caption(f"💡 Approach: {draft.get('approach_note', 'N/A')}")

                # Gmail mailto link
                if prospect_email and draft.get("subject_line"):
                    subject = urllib.parse.quote(draft["subject_line"])
                    body_for_mail = urllib.parse.quote(draft.get("body", "").replace("\\n", "\n"))
                    mailto = f"mailto:{prospect_email}?subject={subject}&body={body_for_mail}"
                    st.markdown(f'<a href="{mailto}" target="_blank"><button style="width:100%;padding:0.5em;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer;">📨 Send via Gmail</button></a>', unsafe_allow_html=True)

        with tab_signals:
            if signals:
                for i, sig in enumerate(signals):
                    score = sig.get("relevance_score", 0)
                    icon = "🟢" if score >= 7 else "🟡" if score >= 4 else "🔴"
                    is_hook = hook_data and hook_data.get("selected_hook") == sig.get("signal")
                    marker = " ← **SELECTED HOOK**" if is_hook else ""
                    sens = sig.get("sensitivity", "none")
                    sens_badge = " 🛑 HIGH SENSITIVITY" if sens == "high" else ""

                    with st.expander(f"{icon} Signal {i+1}: {sig['signal'][:80]}... ({score}/10){marker}{sens_badge}", expanded=is_hook):
                        st.markdown(f"**Signal:** {sig['signal']}")
                        st.markdown(f"**Source:** {sig.get('source', 'N/A')}")
                        st.markdown(f"**Relevance:** {score}/10")
                        st.markdown(f"**Connection:** {sig.get('connection', 'N/A')}")
                        st.markdown(f"**Sensitivity:** {sens}")
                        st.markdown(f"**Recency:** {sig.get('recency', 'Unknown')}")
                        if sig.get("source_url"):
                            st.markdown(f"[View source]({sig['source_url']})")
            else:
                st.info("No signals identified.")

        with tab_research:
            for src in research_data.get("research_sources", []):
                icon = "✅" if src["status"] == "success" else "❌"
                with st.expander(f"{icon} {src['source']} — {src['count']} results"):
                    st.caption(f"Query: `{src['query']}`")
                    for r in src.get("results", []):
                        st.markdown(f"**{r.get('title', 'Untitled')}**")
                        st.caption(r.get("content", "")[:300])
                        if r.get("url"):
                            st.markdown(f"[Link]({r['url']})")
                        st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # ACTION BUTTONS (outside the run block — persists across reruns)
    # ════════════════════════════════════════════════════════════════
    if st.session_state.current_run:
        cr = st.session_state.current_run
        if not cr.get("status"):
            st.markdown("---")
            st.markdown("### ✅ Save this run")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve Draft", type="primary", use_container_width=True):
                    cr["status"] = "Approved"
                    st.session_state.run_history.append(cr)
                    st.session_state.current_run = None
                    st.success("✅ Draft approved and saved!")
                    st.rerun()
            with col2:
                if st.button("✏️ Needs Edit", use_container_width=True):
                    cr["status"] = "Needs Edit"
                    st.session_state.run_history.append(cr)
                    st.session_state.current_run = None
                    st.info("Marked for editing and saved.")
                    st.rerun()
            with col3:
                if st.button("❌ Reject", use_container_width=True):
                    cr["status"] = "Rejected"
                    st.session_state.run_history.append(cr)
                    st.session_state.current_run = None
                    st.warning("Rejected and saved.")
                    st.rerun()

    # ════════════════════════════════════════════════════════════════
    # DRAFTS HISTORY (on the same page)
    # ════════════════════════════════════════════════════════════════
    if st.session_state.run_history:
        st.markdown("---")
        st.markdown("## 📜 Drafts History")

        for i, past_run in enumerate(reversed(st.session_state.run_history)):
            conf_past = past_run.get("confidence", "N/A")
            conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf_past, "⚪")
            status = past_run.get("status", "?")
            status_emoji = {"Approved": "✅", "Needs Edit": "✏️", "Rejected": "❌"}.get(status, "⏳")
            edge_past = past_run.get("edge_case", "")
            edge_badge = ""
            if "ghost" in edge_past:
                edge_badge += " 👻"
            if "left" in edge_past:
                edge_badge += " 🔄"
            if "sensitive" in edge_past:
                edge_badge += " 🛑"

            draft_past = past_run.get("stages", {}).get("draft", {})
            campaign_name = past_run.get("campaign", "N/A")

            with st.expander(f"{status_emoji} {past_run.get('prospect_name', '?')} @ {past_run.get('prospect_company', '?')} — {conf_emoji} {conf_past}{edge_badge}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Campaign:** {campaign_name}")
                    st.markdown(f"**Prospect:** {past_run.get('prospect_name', 'N/A')}")
                    st.markdown(f"**Company:** {past_run.get('prospect_company', 'N/A')}")
                    st.markdown(f"**Email:** {past_run.get('prospect_email', 'N/A')}")
                with col2:
                    st.markdown(f"**Confidence:** {conf_emoji} {conf_past}")
                    st.markdown(f"**Status:** {status_emoji} {status}")
                    st.markdown(f"**Date:** {past_run.get('completed_at', 'N/A')[:16]}")

                if draft_past and isinstance(draft_past, dict):
                    st.markdown("---")
                    st.markdown(f"**Subject:** {draft_past.get('subject_line', 'N/A')}")
                    st.markdown(draft_past.get("body", "N/A").replace("\\n", "\n\n"))

                    # Send button for approved drafts
                    p_email = past_run.get("prospect_email", "")
                    if status == "Approved" and p_email and draft_past.get("subject_line"):
                        subj = urllib.parse.quote(draft_past["subject_line"])
                        bod = urllib.parse.quote(draft_past.get("body", "").replace("\\n", "\n"))
                        ml = f"mailto:{p_email}?subject={subj}&body={bod}"
                        st.markdown(f'<a href="{ml}" target="_blank"><button style="padding:0.4em 1em;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer;">📨 Send via Gmail</button></a>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# SCREEN 3: DASHBOARD
# ════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.title("📊 Dashboard")

    runs = st.session_state.run_history
    if not runs:
        st.info("No runs yet. Go to 'New Prospect Run' to start.")
        st.stop()

    # ── Metrics ──
    total = len(runs)
    approved = sum(1 for r in runs if r.get("status") == "Approved")
    edits = sum(1 for r in runs if r.get("status") == "Needs Edit")
    rejected = sum(1 for r in runs if r.get("status") == "Rejected")
    high = sum(1 for r in runs if r.get("confidence") == "HIGH")
    med = sum(1 for r in runs if r.get("confidence") == "MEDIUM")
    low = sum(1 for r in runs if r.get("confidence") == "LOW")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs", total)
    col2.metric("✅ Approved", approved)
    col3.metric("✏️ Needs Edit", edits)
    col4.metric("❌ Rejected", rejected)

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 High Confidence", high)
    col2.metric("🟡 Medium Confidence", med)
    col3.metric("🔴 Low Confidence", low)

    # Edge case summary
    edge_cases = [r.get("edge_case", "") for r in runs if r.get("edge_case")]
    if edge_cases:
        st.markdown("---")
        st.markdown("### 🔍 Edge Cases Detected")
        ghost_co = sum(1 for e in edge_cases if "ghost_company" in e)
        left = sum(1 for e in edge_cases if "prospect_left" in e)
        sensitive = sum(1 for e in edge_cases if "sensitive" in e)
        if ghost_co:
            st.write(f"👻 Ghost Company: {ghost_co} run(s)")
        if left:
            st.write(f"🔄 Prospect Left Company: {left} run(s)")
        if sensitive:
            st.write(f"🛑 Sensitive Situation: {sensitive} run(s)")

    st.markdown("---")
    st.markdown("### Run History")

    for i, run in enumerate(reversed(runs)):
        conf = run.get("confidence", "N/A")
        conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf, "⚪")
        status = run.get("status", "Completed")
        status_emoji = {"Approved": "✅", "Needs Edit": "✏️", "Rejected": "❌"}.get(status, "⏳")
        edge = run.get("edge_case", "")
        edge_badge = ""
        if "ghost" in edge:
            edge_badge += " 👻"
        if "left" in edge:
            edge_badge += " 🔄"
        if "sensitive" in edge:
            edge_badge += " 🛑"

        hook_text = ""
        h = run.get("stages", {}).get("hook")
        if h and isinstance(h, dict) and h.get("selected_hook"):
            hook_text = h["selected_hook"][:60] + "..."

        email_status = run.get("stages", {}).get("email", {}).get("status", "?")
        email_icon = {"valid": "✅", "found": "✅", "invalid": "❌", "not_found": "⚠️"}.get(email_status, "❓")

        with st.expander(f"{status_emoji} {run.get('prospect_name', '?')} @ {run.get('prospect_company', '?')} — {conf_emoji} {conf} {edge_badge}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Prospect:** {run.get('prospect_name', 'N/A')}")
                st.markdown(f"**Company:** {run.get('prospect_company', 'N/A')}")
                st.markdown(f"**Email:** {run.get('prospect_email', 'N/A')} {email_icon}")
                st.markdown(f"**Campaign:** {run.get('campaign', 'N/A')}")
            with col2:
                st.markdown(f"**Confidence:** {conf_emoji} {conf}")
                st.markdown(f"**Status:** {status_emoji} {status}")
                st.markdown(f"**Hook:** {hook_text}")
                st.markdown(f"**Run:** {run.get('started_at', 'N/A')[:16]}")
                if edge:
                    st.markdown(f"**Edge Cases:** {edge}")

            # Draft
            draft = run.get("stages", {}).get("draft")
            if draft and isinstance(draft, dict):
                st.markdown("---")
                st.markdown(f"**Subject:** {draft.get('subject_line', 'N/A')}")
                st.markdown(draft.get("body", "N/A").replace("\\n", "\n\n"))

            # Signals summary
            sig_data = run.get("stages", {}).get("signals", {})
            res_data = run.get("stages", {}).get("research", {})
            st.caption(f"📡 {sig_data.get('count', 0)} signals from {res_data.get('total', 0)} research results (Company: {res_data.get('company', 0)} · Prospect: {res_data.get('prospect', 0)})")

    st.markdown("---")
    if st.button("🗑️ Clear All History"):
        st.session_state.run_history = []
        st.rerun()
