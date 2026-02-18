import streamlit as st
import json
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# =========================================================
# LOAD ENV
# =========================================================
load_dotenv()

def clean_env(name):
    value = os.getenv(name)
    if value:
        return value.strip().strip('"').strip("'")
    return value

AZURE_ENDPOINT = clean_env("AZURE_OPENAI_ENDPOINT")
AZURE_KEY = clean_env("AZURE_OPENAI_API_KEY")
AZURE_VERSION = clean_env("AZURE_OPENAI_API_VERSION")
DEPLOYMENT_NAME = clean_env("AZURE_OPENAI_DEPLOYMENT_NAME")

if not all([AZURE_ENDPOINT, AZURE_KEY, AZURE_VERSION, DEPLOYMENT_NAME]):
    st.error("Azure OpenAI environment variables are not configured correctly.")
    st.stop()

client = AzureOpenAI(
    api_key=AZURE_KEY,
    api_version=AZURE_VERSION,
    azure_endpoint=AZURE_ENDPOINT
)

# =========================================================
# SAFE MODEL CALL WRAPPER
# =========================================================
def safe_completion(messages, max_tokens=12000):
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Model returned empty content")

    return json.loads(content.strip())


# =========================================================
# CHUNKING LOGIC
# =========================================================
def split_into_chunks(text, max_chars=15000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]


# =========================================================
# PHASE 1: DEEP STRUCTURAL EXTRACTION
# =========================================================
def extract_from_large_cobol(cobol_code):

    system_prompt = """
You are a senior COBOL reverse engineering expert.

Perform deep structural extraction.

Return STRICT JSON:

{
  "purpose": "",
  "entities": [],
  "business_rules": [],
  "control_flow": [],
  "conditional_flags": [],
  "file_io_operations": [],
  "external_calls": [],
  "data_lineage": [],
  "update_logic": []
}

Capture:
- IF nesting and PERFORM chains
- CICS READ/WRITE/REWRITE/DELETE
- CALL statements
- Indicator/flag-driven behavior
- Variable derivation and usage
- Amendment/update logic
"""

    chunks = split_into_chunks(cobol_code)

    aggregated = {
        "purpose": "",
        "entities": [],
        "business_rules": [],
        "control_flow": [],
        "conditional_flags": [],
        "file_io_operations": [],
        "external_calls": [],
        "data_lineage": [],
        "update_logic": []
    }

    progress = st.progress(0)

    for i, chunk in enumerate(chunks):

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk}
        ]

        result = safe_completion(messages)

        for key in aggregated.keys():
            if key == "purpose":
                if not aggregated["purpose"]:
                    aggregated["purpose"] = result.get("purpose", "")
            else:
                aggregated[key].extend(result.get(key, []))

        progress.progress((i + 1) / len(chunks))

    return aggregated


# =========================================================
# PHASE 2: FLOW-AWARE SYNTHESIS
# =========================================================
def synthesize_business_rules(aggregated):

    system_prompt = """
You are an enterprise modernization architect.

Synthesize a traceable, flow-aware system model.

- Map business rules to control paths
- Associate rules with flags and indicators
- Link file operations to validations
- Connect external calls to process steps
- Preserve data lineage
- Detail update/amendment behavior

Return STRICT JSON:

{
  "purpose": "",
  "process_map": [],
  "business_rules": [],
  "control_flow": [],
  "external_dependencies": [],
  "data_lineage": [],
  "risk_areas": []
}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(aggregated)}
    ]

    return safe_completion(messages)


# =========================================================
# PHASE 3: FULL MODERNIZATION OUTPUT
# =========================================================
def generate_full_modernization(synthesized_data):

    system_prompt = """
Generate enterprise-grade modernization artifacts.

Return STRICT JSON:

{
  "bc_mapping": {},
  "al_code": "",
  "etl_script": "",
  "test_cases": [],
  "dependency_map": [],
  "data_lineage_map": []
}

Ensure:
- Flow-aware BC mapping
- Dependency mapping
- Traceable AL logic
- Data lineage documentation
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(synthesized_data)}
    ]

    return safe_completion(messages, max_tokens=12000)


# =========================================================
# STREAMLIT UI
# =========================================================
st.set_page_config("Enterprise COBOL Modernization Engine", layout="wide")
st.title("🏭 Enterprise COBOL → Dynamics 365 Modernization Platform")

tabs = st.tabs([
    "📂 Upload & Analyze",
    "📋 Business Rules",
    "🧭 Process Flow",
    "🔗 Dependencies",
    "🏗 BC Mapping",
    "💻 AL Code",
    "🔄 ETL Script",
    "🧪 Test Cases",
    "📊 Data Lineage"
])

# =========================================================
# TAB 1: UPLOAD
# =========================================================
with tabs[0]:

    uploaded = st.file_uploader("Upload COBOL File(s)", type=["cbl", "cob", "txt"])

    if uploaded:
        cobol_code = uploaded.read().decode("utf-8")
        st.code(cobol_code[:2000])

        if st.button("Run Enterprise Modernization"):

            with st.spinner("Deep structural extraction..."):
                extracted = extract_from_large_cobol(cobol_code)

            with st.spinner("Flow-aware synthesis..."):
                synthesized = synthesize_business_rules(extracted)

            with st.spinner("Generating modernization artifacts..."):
                final = generate_full_modernization(synthesized)

            final.update(synthesized)
            st.session_state["analysis"] = final
            st.success("Enterprise-grade analysis complete")


# =========================================================
# TABS DISPLAY
# =========================================================
result = st.session_state.get("analysis")

with tabs[1]:
    if result:
        st.json(result.get("business_rules", []))

with tabs[2]:
    if result:
        st.json(result.get("control_flow", result.get("process_map", [])))

with tabs[3]:
    if result:
        st.json(result.get("dependency_map", result.get("external_dependencies", [])))

with tabs[4]:
    if result:
        st.json(result.get("bc_mapping", {}))

with tabs[5]:
    if result:
        st.code(result.get("al_code", ""), language="al")

with tabs[6]:
    if result:
        st.code(result.get("etl_script", ""), language="python")

with tabs[7]:
    if result:
        st.json(result.get("test_cases", []))

with tabs[8]:
    if result:
        st.json(result.get("data_lineage_map", result.get("data_lineage", [])))

st.markdown("---")
st.markdown("⚠️ Human validation required before production deployment.")
