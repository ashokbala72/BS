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
def safe_completion(messages, max_tokens=4000):
    try:
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

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            st.error("Model returned invalid JSON.")
            st.code(content[:3000])
            raise

    except Exception as e:
        st.error(f"Azure OpenAI call failed: {str(e)}")
        raise


# =========================================================
# CHUNKING LOGIC
# =========================================================
def split_into_chunks(text, max_chars=15000):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end
    return chunks


# =========================================================
# PHASE 1: EXTRACT STRUCTURE
# =========================================================
def extract_from_large_cobol(cobol_code):

    system_prompt = """
You are a COBOL modernization analyzer.

Extract ONLY:
{
    "purpose": "",
    "entities": [],
    "business_rules": []
}

Strict JSON only.
"""

    chunks = split_into_chunks(cobol_code)

    aggregated = {
        "purpose": "",
        "entities": [],
        "business_rules": []
    }

    progress = st.progress(0)

    for i, chunk in enumerate(chunks):

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk}
        ]

        try:
            result = safe_completion(messages)

            aggregated["entities"].extend(result.get("entities", []))
            aggregated["business_rules"].extend(result.get("business_rules", []))

            if not aggregated["purpose"]:
                aggregated["purpose"] = result.get("purpose", "")

        except Exception as e:
            return {"error": f"Chunk {i} failed: {str(e)}"}

        progress.progress((i + 1) / len(chunks))

    aggregated["entities"] = list(set(aggregated["entities"]))
    aggregated["business_rules"] = list(set(aggregated["business_rules"]))

    return aggregated


# =========================================================
# PHASE 2: SYNTHESIZE RULES
# =========================================================
def synthesize_business_rules(aggregated):

    system_prompt = """
You are a senior ERP architect.

Based on the extracted entities and business rules,
synthesize a comprehensive and complete business rule set.

Expand implicit logic.
Merge related rules.
Infer cross-process workflows.
Improve clarity and structure.

Return STRICT JSON:

{
    "purpose": "",
    "entities": [],
    "business_rules": []
}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(aggregated)}
    ]

    return safe_completion(messages)


# =========================================================
# PHASE 3: GENERATE MODERNIZATION ARTIFACTS
# =========================================================
def generate_full_modernization(aggregated_data):

    system_prompt = """
Using the extracted and synthesized business logic,
generate full modernization output.

JSON STRUCTURE:
{
    "bc_mapping": {},
    "al_code": "",
    "etl_script": "",
    "test_cases": []
}

Strict JSON only.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(aggregated_data)}
    ]

    return safe_completion(messages, max_tokens=4000)


# =========================================================
# STREAMLIT UI
# =========================================================
st.set_page_config("COBOL → D365 Modernization Platform", layout="wide")
st.title("🏭 COBOL → Dynamics 365 Business Central Modernization Engine")

tabs = st.tabs([
    "📂 Upload & Analyze",
    "📋 Business Rules",
    "🏗 BC Mapping",
    "💻 AL Code",
    "🔄 ETL Script",
    "🧪 Test Cases"
])


# =========================================================
# TAB 1: UPLOAD
# =========================================================
with tabs[0]:

    uploaded = st.file_uploader("Upload COBOL File", type=["cbl", "cob", "txt"])

    if uploaded:
        cobol_code = uploaded.read().decode("utf-8")

        st.subheader("COBOL Preview")
        st.code(cobol_code[:3000])

        if st.button("Run Large-File Modernization"):

            with st.spinner("Extracting structure from large COBOL..."):
                extracted = extract_from_large_cobol(cobol_code)

            if "error" in extracted:
                st.error(extracted["error"])
            else:
                with st.spinner("Synthesizing global business logic..."):
                    synthesized = synthesize_business_rules(extracted)

                with st.spinner("Generating modernization artifacts..."):
                    final = generate_full_modernization(synthesized)

                final.update(synthesized)
                st.session_state["analysis"] = final

                st.success("Large-file modernization complete")


# =========================================================
# TAB 2: BUSINESS RULES
# =========================================================
with tabs[1]:
    result = st.session_state.get("analysis")
    if result and "business_rules" in result:
        st.json(result["business_rules"])
    else:
        st.info("Run analysis first.")


# =========================================================
# TAB 3: BC MAPPING
# =========================================================
with tabs[2]:
    result = st.session_state.get("analysis")
    if result and "bc_mapping" in result:
        st.json(result["bc_mapping"])
    else:
        st.info("Run analysis first.")


# =========================================================
# TAB 4: AL CODE
# =========================================================
with tabs[3]:
    result = st.session_state.get("analysis")
    if result and "al_code" in result:
        st.code(result["al_code"], language="al")
        st.download_button(
            "Download extension.al",
            result["al_code"],
            file_name="extension.al"
        )
    else:
        st.info("Run analysis first.")


# =========================================================
# TAB 5: ETL SCRIPT
# =========================================================
with tabs[4]:
    result = st.session_state.get("analysis")
    if result and "etl_script" in result:
        st.code(result["etl_script"], language="python")
    else:
        st.info("Run analysis first.")


# =========================================================
# TAB 6: TEST CASES
# =========================================================
with tabs[5]:
    result = st.session_state.get("analysis")
    if result and "test_cases" in result:
        st.json(result["test_cases"])
    else:
        st.info("Run analysis first.")


st.markdown("---")
st.markdown("⚠️ Human validation required before production deployment.")
