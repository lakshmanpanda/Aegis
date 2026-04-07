import streamlit as st
import requests
import json
import time

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="AEGIS | Market Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a sleek, "Command Center" look
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0px; }
    .sub-header { font-size: 1.2rem; color: #64748B; margin-bottom: 30px; }
    .metric-card { background-color: #F8FAFC; padding: 20px; border-radius: 10px; border-left: 5px solid #1E3A8A; }
    .insight-bullet { font-size: 1.1rem; margin-bottom: 10px; }
    div[data-testid="stForm"] { border: none; padding: 0; background-color: transparent; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# HEADER SECTION
# ==========================================
st.markdown('<p class="main-header">🛡️ AEGIS Core Command Center</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-Agent GraphRAG & Causal Market Strategy</p>', unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# COMMAND CENTER TABS
# ==========================================
tab1, tab2 = st.tabs(["📊 Tactical Dashboard (Manual Scan)", "🤖 Autonomous Sentinel (Background Monitor)"])

# ------------------------------------------
# TAB 1: MANUAL SCANNER
# ------------------------------------------
with tab1:
    # Using st.form prevents edge cases where clicking elsewhere triggers a rerun!
    with st.form(key="manual_scan_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            target_keyword = st.text_input(
                "Enter Target Product (Keyword or SKU):", 
                placeholder="e.g., ASUS Dual GeForce RTX 5060 8GB",
                label_visibility="collapsed"
            )
        with col2:
            deploy_button = st.form_submit_button("🚀 Deploy Aegis Swarm", use_container_width=True, type="primary")

    # ==========================================
    # EXECUTION LOGIC (TAB 1)
    # ==========================================
    if deploy_button and target_keyword:
        
        # 1. The Loading State
        with st.status("Initiating Aegis Swarm Pipeline...", expanded=True) as status:
            st.write("📡 Connecting to Scraper API (Port 8000)...")
            time.sleep(1) # Visual delay for effect
            st.write("🚦 Checking Neo4j AuraDB for existing Knowledge Graph...")
            st.write("🧠 Dispatching Gemini 3.1 Flash-Lite Agents...")
            st.write("🧮 Wargaming Strategist calculating C_pivot Score...")
            
            # 2. The API Call
            try:
                # Hit your Gateway API
                api_url = "http://127.0.0.1:8001/analyze"
                response = requests.post(api_url, json={"keyword": target_keyword}, timeout=200)
                response.raise_for_status()
                
                data = response.json()
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                
            except requests.exceptions.RequestException as e:
                status.update(label="System Failure", state="error", expanded=True)
                st.error(f"Failed to connect to Aegis Core: {e}")
                st.stop()

        # ==========================================
        # RESULTS DASHBOARD
        # ==========================================
        c_pivot = data.get("c_pivot_score", 0.0)
        payload = data.get("execution_payload", {})
        target_sku = data.get("target_sku", target_keyword)

        # Top Metrics Row
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric(label="Target Asset", value=target_sku[:25] + "..." if len(target_sku) > 25 else target_sku)
            
        with m2:
            # Color code the score
            score_color = "normal"
            if c_pivot > 0.6: score_color = "inverse"
            elif c_pivot < 0.2: score_color = "off"
            st.metric(label="C_Pivot Score (Volatility)", value=f"{c_pivot:.3f}", delta="Action Threshold: 0.1", delta_color=score_color)
            
        with m3:
            status_text = "🟢 MONITOR ONLY" if c_pivot <= 0.1 else "🔴 ACTION REQUIRED"
            st.metric(label="System Directive", value=status_text)

        st.markdown("<br>", unsafe_allow_html=True)

        # The Executive Report
        if "executive_summary" in payload:
            st.subheader("📑 Executive Summary")
            st.info(payload.get("executive_summary"))
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader("🔍 Key Insights (GraphRAG Context)")
                for insight in payload.get("key_insights", []):
                    st.markdown(f"- {insight}")
                    
            with col_right:
                st.subheader("⚡ Tactical Execution Steps")
                for step in payload.get("tactical_steps", []):
                    st.checkbox(step, value=False) 
                    
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.subheader("💰 Resource Allocation")
            st.warning(payload.get("resource_allocation"))
            
            st.subheader("📈 Projected Outcome")
            st.success(payload.get("projected_outcome"))

        else:
            st.error("Execution Payload generation failed or returned raw data.")
            st.json(payload)

        with st.expander("🛠️ View Raw System JSON & Graph Data"):
            st.json(data)


# ------------------------------------------
# TAB 2: AUTONOMOUS SENTINEL
# ------------------------------------------
with tab2:
    st.markdown("### 🕵️ Deploy Background Sentinel")
    st.info("The Sentinel will autonomously scan the market, build the Knowledge Graph, calculate C_pivot scores, and email the Executive Report at your specified interval.")

    # --- ACTIVATION FORM ---
    with st.form(key="sentinel_form"):
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            sent_keyword = st.text_input("Target Product (Keyword or SKU):", placeholder="e.g., iPhone 17 Pro Max")
            sent_interval = st.number_input("Scan Interval (Minutes):", min_value=1, max_value=1440, value=60, help="How often should the AI run in the background?")
        with s_col2:
            sent_email = st.text_input("Recipient Email Address:", placeholder="executive@company.com")
            
        st.markdown("<br>", unsafe_allow_html=True)
        sentinel_button = st.form_submit_button("🛡️ Activate Sentinel", use_container_width=True, type="primary")

    if sentinel_button:
        if not sent_keyword or not sent_email:
            st.warning("⚠️ Please provide both a keyword and an email address.")
        else:
            with st.status("Configuring Background Cron Job...", expanded=True) as status:
                st.write("📡 Registering background task with Aegis Core...")
                try:
                    # Hit the new Sentinel Start Endpoint
                    api_url = "http://127.0.0.1:8001/monitor/start"
                    payload = {
                        "keyword": sent_keyword,
                        "email": sent_email,
                        "interval_minutes": sent_interval
                    }
                    
                    response = requests.post(api_url, json=payload, timeout=10)
                    response.raise_for_status()
                    
                    status.update(label="Sentinel Deployed Successfully!", state="complete", expanded=False)
                    st.success(f"✅ **Mission Locked.** The Sentinel is now monitoring **{sent_keyword}**.")
                    st.markdown(f"**Interval:** Every {sent_interval} minute(s).")
                    st.markdown(f"**Reporting To:** `{sent_email}`")
                    st.info("The first analysis run has been triggered. Check your email shortly!")
                    
                except requests.exceptions.RequestException as e:
                    status.update(label="Deployment Failed", state="error", expanded=True)
                    st.error(f"Failed to connect to Aegis Core Scheduler: {e}")

    st.markdown("---")
    
    # --- DEACTIVATION FORM ---
    st.markdown("### 🛑 Deactivate Sentinel")
    with st.form(key="stop_sentinel_form"):
        stop_keyword = st.text_input("Product to Stop Monitoring:", placeholder="Type the exact product name here...")
        stop_button = st.form_submit_button("🛑 Stop Sentinel", use_container_width=True)

    if stop_button:
        if not stop_keyword:
            st.warning("⚠️ Please provide the keyword of the active Sentinel you want to stop.")
        else:
            try:
                # Hit the new Sentinel Stop Endpoint
                stop_url = "http://127.0.0.1:8001/monitor/stop"
                stop_response = requests.post(stop_url, json={"keyword": stop_keyword}, timeout=10)
                stop_data = stop_response.json()
                
                if stop_data.get("status") == "success":
                    st.success(stop_data.get("message"))
                else:
                    st.warning(stop_data.get("message"))
            except Exception as e:
                st.error(f"Failed to communicate with the server to stop Sentinel: {e}")