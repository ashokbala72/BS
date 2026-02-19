import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
from openai import AzureOpenAI

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config("Enterprise COBOL Modernization Engine", layout="wide")
st.title("🏭 Enterprise COBOL → Dynamics 365 Business Central Modernization Engine")

# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================
load_dotenv()

def clean_env(name):
    value = os.getenv(name)
    if value:
        return value.strip().strip('"').strip("'")
    return None

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
# SAFE MODEL CALL
# =========================================================
def safe_completion(messages, max_tokens=14000, retries=3):
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=messages,
                temperature=0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            st.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)

    st.error("Model failed after retries.")
    return {}

# =========================================================
# UTILITIES
# =========================================================
def split_into_chunks(text, max_lines=300):
    lines = text.splitlines()
    return ["\n".join(lines[i:i+max_lines]) for i in range(0, len(lines), max_lines)]

def dedupe_list(existing, new_items):
    for item in new_items:
        if item not in existing:
            existing.append(item)

# =========================================================
# PHASE 1 – EXTRACTION
# =========================================================
def extract_from_large_cobol(cobol_code):

    system_prompt = """
Extract ALL business-relevant logic from COBOL.

Return STRICT JSON:
{
  "purpose": "",
  "entities": [],
  "business_rules": [{"rule_id": "", "description": "", "source_lines": []}],
  "control_flow": [],
  "conditional_flags": [],
  "file_io_operations": [],
  "external_calls": [],
  "data_lineage": []
}
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
        "data_lineage": []
    }

    progress = st.progress(0)

    for i, chunk in enumerate(chunks):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk}
        ]

        result = safe_completion(messages)
        if not result:
            continue

        for key in aggregated:
            if key == "purpose":
                if not aggregated["purpose"]:
                    aggregated["purpose"] = result.get("purpose", "")
            else:
                dedupe_list(aggregated[key], result.get(key, []))

        progress.progress((i + 1) / len(chunks))

    return aggregated

# =========================================================
# PHASE 2 – SYNTHESIS
# =========================================================
def synthesize_model(extracted):

    system_prompt = """
Preserve ALL business rules exactly.

Return STRICT JSON:
{
  "process_map": [],
  "business_rules": [],
  "external_dependencies": [],
  "risk_areas": [],
  "data_lineage": []
}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(extracted)}
    ]

    return safe_completion(messages)

# =========================================================
# PHASE 3 – MODERNIZATION
# =========================================================
def generate_modernization_artifacts(synthesized):

    system_prompt = """
Generate BC modernization artifacts.

Return STRICT JSON:
{
  "bc_mapping": {
      "tables": [],
      "fields": [],
      "transactions": [],
      "validation_triggers": [],
      "integration_endpoints": [],
      "error_handlers": []
  },
  "al_code": "",
  "etl_script": "",
  "test_cases": [],
  "dependency_map": [],
  "data_lineage_map": [],
  "rule_traceability_matrix": [],
  "business_rule_preservation_percent": 0,
  "modernization_confidence_percent": 0
}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(synthesized)}
    ]

    return safe_completion(messages)

# =========================================================
# BC CONFIG GENERATION
# =========================================================
def generate_bc_configuration(synthesized, modernized):

    system_prompt = """
Generate required Business Central configuration checklist.

Return STRICT JSON:
{
  "environment_setup": [],
  "number_series_setup": [],
  "posting_setup": [],
  "dimension_setup": [],
  "permission_sets": [],
  "integration_setup": [],
  "data_migration_requirements": [],
  "job_queue_setup": [],
  "custom_setup_tables": [],
  "deployment_checklist": []
}
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({
            "synthesized": synthesized,
            "modernized": modernized
        })}
    ]

    return safe_completion(messages)



# =========================================================
# RULE COVERAGE
# =========================================================
def calculate_rule_coverage(extracted_rules, implemented_rules):

    if not extracted_rules:
        return 0

    extracted_ids = {r["rule_id"] for r in extracted_rules if "rule_id" in r}
    implemented_ids = {
        r["rule_id"] for r in implemented_rules
        if r.get("implemented") is True
    }

    if not extracted_ids:
        return 0

    return round(
        (len(extracted_ids & implemented_ids) / len(extracted_ids)) * 100,
        2
    )

# =========================================================
# UI TABS
# =========================================================
(
    tab_upload,
    tab_rules,
    tab_process,
    tab_dependencies,
    tab_bc,
    tab_bc_config,
    tab_al,
    tab_etl,
    tab_tests,
    tab_lineage,
    tab_metrics,
    tab_full
) = st.tabs([
    "📂 Upload",
    "📋 Business Rules",
    "🧭 Process Flow",
    "🔗 Dependencies",
    "🏗 BC Mapping",
    "⚙️ BC Config",
    "💻 AL Code",
    "🔄 ETL Script",
    "🧪 Test Cases",
    "📊 Data Lineage",
    "📈 Metrics",
    "🧠 Full Model"
])

# =========================================================
# UPLOAD
# =========================================================
with tab_upload:

    uploaded = st.file_uploader("Upload COBOL File", type=["cbl", "cob", "txt"])

    if uploaded:
        cobol_code = uploaded.read().decode("utf-8")
        st.code(cobol_code[:2000])

        if st.button("Run Enterprise Modernization", use_container_width=True):

            extracted = extract_from_large_cobol(cobol_code)
            synthesized = synthesize_model(extracted)
            modernized = generate_modernization_artifacts(synthesized)
            bc_config = generate_bc_configuration(synthesized, modernized)
            

            st.session_state["analysis"] = {
                "extracted": extracted,
                "synthesized": synthesized,
                "modernized": modernized,
                "bc_config": bc_config
                
            }

            st.success("Modernization Complete.")

# =========================================================
# LOAD DATA
# =========================================================
analysis = st.session_state.get("analysis", {})
extracted = analysis.get("extracted", {})
synthesized = analysis.get("synthesized", {})
modernized = analysis.get("modernized", {})
bc_config = analysis.get("bc_config", {})


# =========================================================
# RENDER TABS
# =========================================================
with tab_rules:
    st.json(extracted.get("business_rules", []))

with tab_process:
    st.json(synthesized.get("process_map", []))

with tab_dependencies:
    st.json(modernized.get("dependency_map", []))

with tab_bc:
    st.json(modernized.get("bc_mapping", {}))

with tab_bc_config:
    st.json(bc_config)

with tab_al:
    st.code(modernized.get("al_code", ""), language="al")

with tab_etl:
    st.code(modernized.get("etl_script", ""), language="python")

with tab_tests:
    st.json(modernized.get("test_cases", []))

with tab_lineage:
    st.json(modernized.get("data_lineage_map", []))

with tab_metrics:
    st.metric("Rule Preservation",
              modernized.get("business_rule_preservation_percent", 0))
    st.metric("Modernization Confidence",
              modernized.get("modernization_confidence_percent", 0))


with tab_full:
    st.json(analysis)

    st.download_button(
        "Download Full Model",
        data=json.dumps(analysis, indent=2),
        file_name="enterprise_modernization_model.json",
        mime="application/json"
    )

st.markdown("---")
st.markdown("⚠️ Enterprise validation required before production deployment.")
