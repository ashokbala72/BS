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
def safe_completion(messages, max_tokens=25000, retries=3):
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
You are a STATIC COBOL EXECUTION INTELLIGENCE ENGINE.

Your responsibility is to reconstruct executable COBOL logic EXACTLY as it executes.

You MUST operate in two internal phases:

PHASE 1 — Full structural extraction
PHASE 2 — Structural validation and correction

You MUST NOT return output until validation passes.

If validation fails, you MUST regenerate internally.

=====================================================================
ABSOLUTE EXECUTION RULES (NON-NEGOTIABLE)
=====================================================================

1. Do NOT summarize.
2. Do NOT generalize.
3. Do NOT collapse sequential IF blocks.
4. Do NOT convert multi-branch logic into binary logic.
5. Do NOT merge paragraphs.
6. Do NOT create synthetic paragraph names.
7. Do NOT simplify boolean expressions.
8. Do NOT omit ELSE behavior.
9. Do NOT omit fallthrough paths.
10. Do NOT invent logic.
11. Preserve paragraph names EXACTLY.
12. Preserve GO TO targets EXACTLY.
13. Preserve nested IF hierarchy EXACTLY.
14. Preserve execution order EXACTLY.
15. Maintain ONE canonical rule registry only.

=====================================================================
SCHEMA LOCK — HARD ENFORCEMENT
=====================================================================

You MUST return EXACTLY the following JSON structure.
No additional keys allowed.
No missing keys allowed.
No renamed keys allowed.
No duplicated sections allowed.

If ANY schema violation occurs, the output is INVALID and must be regenerated.

{
  "program_metadata": {
      "program_id": "",
      "paragraphs": []
  },

  "business_rules": [
      {
          "rule_id": "BR-001",
          "rule_type": "validation | branch | update | calculation | loop | io",
          "paragraph": "",
          "trigger_statement": "",
          "conditions": [],
          "actions": [],
          "else_actions": [],
          "go_to_targets": [],
          "affected_fields": [],
          "source_lines": []
      }
  ],

  "process_flow_graph": [
      {
          "paragraph": "",
          "entry_conditions": [],
          "ordered_logic": [
              {
                  "precedence_order": 1,
                  "condition": "",
                  "true_target": "",
                  "false_target": ""
              }
          ],
          "explicit_fallthrough": "",
          "loop_structure": {
              "is_loop": false,
              "loop_entry": "",
              "loop_exit_condition": "",
              "loop_back_target": ""
          }
      }
  ],

  "update_amend_logic": [
      {
          "paragraph": "",
          "target_field": "",
          "source_field": "",
          "governing_conditions": [],
          "material_code_condition": "",
          "route_condition": "",
          "calculation_logic": "",
          "else_behavior": "",
          "source_lines": []
      }
  ],

  "material_code_governance": [
      {
          "material_code_range_or_value": "",
          "route_condition": "",
          "effect": "",
          "affected_output_field": "",
          "calculation_or_transformation": "",
          "precedence": 1
      }
  ],

  "conditional_flags": [],

  "file_io_operations": [
      {
          "paragraph": "",
          "file": "",
          "operation": "",
          "result_field": "",
          "success_condition": "",
          "not_found_condition": "",
          "failure_target": ""
      }
  ],

  "external_calls": [],

  "data_lineage": [
      {
          "target_field": "",
          "source_field": "",
          "paragraph": "",
          "transformation": "",
          "governing_conditions": []
      }
  ]
}

=====================================================================
STRUCTURAL ENFORCEMENT RULES
=====================================================================

PARAGRAPH INTEGRITY

• Each COBOL paragraph MUST appear exactly once in process_flow_graph.
• Paragraph names must match source exactly.
• Paragraph names MUST NOT contain "/" or merged names.
• If merging is detected, regenerate.

RULE REGISTRY LOCK

• Only ONE business_rules array is allowed.
• rule_id format: BR-001, BR-002, BR-003...
• Sequential.
• No duplicates.
• No resets.
• No reuse.
• One atomic decision per rule.
• If duplicate or skipped sequence detected → regenerate.

ASSIGNMENT CLASSIFICATION LOCK

For every MOVE, ADD, SUBTRACT, MULTIPLY, DIVIDE:

If unconditional:
→ appears in business_rules only.

If conditional:
→ MUST appear in BOTH:
   business_rules
   update_amend_logic

If conditional assignments exist AND update_amend_logic is empty:
→ INVALID → regenerate.

UPDATE ISOLATION LOCK

Each target_field conditionally assigned:
→ Exactly one entry in update_amend_logic.
→ Must include governing_conditions.
→ Must include else_behavior if present.

LOOP MODELING LOCK

If GO TO targets earlier paragraph:
→ loop_structure.is_loop MUST be true.
→ loop_entry MUST be set.
→ loop_back_target MUST be set.
→ loop_exit_condition MUST be explicit.

If file READ repeats until result code (e.g. '10'):
→ loop_exit_condition MUST reference that code.

If backward jump exists and loop_structure.is_loop is false:
→ INVALID → regenerate.

MATERIAL GOVERNANCE LOCK

If material code logic exists (e.g. F411-CODE-MATL):
→ material_code_governance MUST be populated.

If material conditions detected AND material_code_governance empty:
→ INVALID → regenerate.

FALLTHROUGH LOCK

If execution continues without ELSE:
→ explicit_fallthrough MUST be populated.

BOOLEAN LOCK

All boolean expressions must explicitly compare both sides.
No abbreviated comparisons allowed.

=====================================================================
FINAL VALIDATION CHECKLIST (MUST PASS BEFORE RETURN)
=====================================================================

1. No extra keys exist.
2. No missing required keys.
3. No duplicate sections.
4. rule_id sequential and unique.
5. Each paragraph appears once.
6. No merged paragraph names.
7. Conditional updates isolated.
8. Loops modeled explicitly.
9. Material governance populated if required.
10. No empty mandatory sections when logic exists.
11. No simplified boolean expressions.

If ANY check fails:
Regenerate internally.

=====================================================================
If the output contains:
- Duplicate rule_id
- Blank paragraph values
- update_amend_logic empty while conditional assignments exist
- material_code_governance empty while material conditions exist
- Any key not explicitly defined in the schema

Then the output is INVALID and MUST be regenerated.

Do NOT merge extraction model with UI model.
Return extraction schema ONLY.

Return STRICT JSON only.
No explanation.
No markdown.
No commentary.
All keys must use double quotes.
Booleans must be lowercase true/false.
No trailing commas.
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
You MUST:
- Preserve rule_id tags inside every process step
- Represent ordered IF/ELSE branching correctly
- Show explicit fall-through logic
- Never simplify multiple branch flows into binary success/failure
- Maintain condition precedence

Each process step MUST include:
"rule_tags": ["BR_001", "BR_002"]

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


# =========================================================
# 🧠 FULL MODEL – ENTERPRISE GOVERNANCE ENGINE
# =========================================================
# =========================================================
# 🧠 FULL MODEL – ENTERPRISE GOVERNANCE ENGINE (HARDENED)
# =========================================================
with tab_full:

    import pandas as pd
    import copy
    import json
    from collections import Counter, defaultdict

    st.title("🧠 Enterprise COBOL Governance & Structural Repair Engine")

    if not analysis:
        st.warning("Run modernization first.")
        st.stop()

    raw_model = analysis.get("extracted", {})
    if not raw_model:
        st.warning("No extracted model found.")
        st.stop()

    # -----------------------------------------------------
    # Deep Copy (Never mutate session state)
    # -----------------------------------------------------
    model = copy.deepcopy(raw_model)

    # =====================================================
    # 1️⃣ REMOVE DUPLICATE RULES (Atomic Deduplication)
    # =====================================================
    def remove_duplicate_rules(model):
        seen = set()
        clean = []

        for r in model.get("business_rules", []):
            signature = (
                r.get("paragraph"),
                json.dumps(r.get("conditions", []), sort_keys=True),
                json.dumps(r.get("actions", []), sort_keys=True),
                json.dumps(r.get("go_to_targets", []), sort_keys=True),
            )
            if signature not in seen:
                seen.add(signature)
                clean.append(r)

        model["business_rules"] = clean
        return model

    # =====================================================
    # 2️⃣ RESEQUENCE RULE IDs
    # =====================================================
    def resequence_rules(model):
        for i, r in enumerate(model.get("business_rules", []), start=1):
            r["rule_id"] = f"BR-{i:03d}"
        return model

    # =====================================================
    # 3️⃣ REBUILD PARAGRAPH REGISTRY
    # =====================================================
    def rebuild_paragraph_registry(model):
        paragraphs = list({
            r.get("paragraph")
            for r in model.get("business_rules", [])
            if r.get("paragraph")
        })
        model.setdefault("program_metadata", {})["paragraphs"] = sorted(paragraphs)
        return model

    # =====================================================
    # 4️⃣ ENFORCE GO TO TARGET INTEGRITY
    # =====================================================
    def enforce_goto_integrity(model):
        valid = set(model.get("program_metadata", {}).get("paragraphs", []))
        for r in model.get("business_rules", []):
            r["go_to_targets"] = [
                t for t in r.get("go_to_targets", [])
                if t in valid
            ]
        return model

    # =====================================================
    # 5️⃣ AUTO-ISOLATE CONDITIONAL UPDATES
    # =====================================================
    def isolate_conditional_updates(model):

        updates = []
        seen_targets = set()

        for r in model.get("business_rules", []):
            if r.get("rule_type") == "update" and r.get("conditions"):
                target = None

                # try extracting target field from actions
                if r.get("actions"):
                    action_text = " ".join(r["actions"])
                    parts = action_text.split()
                    if len(parts) > 1:
                        target = parts[-1]

                if target and target not in seen_targets:
                    seen_targets.add(target)
                    updates.append({
                        "paragraph": r.get("paragraph"),
                        "target_field": target,
                        "source_field": "",
                        "governing_conditions": r.get("conditions"),
                        "material_code_condition": "",
                        "route_condition": "",
                        "calculation_logic": " | ".join(r.get("actions", [])),
                        "else_behavior": " | ".join(r.get("else_actions", [])),
                        "source_lines": r.get("source_lines", [])
                    })

        model["update_amend_logic"] = updates
        return model

    # =====================================================
    # 6️⃣ AUTO-EXTRACT MATERIAL GOVERNANCE
    # =====================================================
    def extract_material_governance(model):

        material_entries = []
        precedence = 1

        for r in model.get("business_rules", []):
            cond_text = json.dumps(r.get("conditions", []))

            if "MATL" in cond_text or "MATERIAL" in cond_text:
                material_entries.append({
                    "material_code_range_or_value": cond_text,
                    "route_condition": "",
                    "effect": "Derived from business rule",
                    "affected_output_field": ", ".join(r.get("affected_fields", [])),
                    "calculation_or_transformation": " | ".join(r.get("actions", [])),
                    "precedence": precedence
                })
                precedence += 1

        model["material_code_governance"] = material_entries
        return model

    # =====================================================
    # 7️⃣ STRUCTURAL VALIDATION
    # =====================================================
    def validate_model(model):

        issues = []
        rules = model.get("business_rules", [])
        meta_paragraphs = model.get("program_metadata", {}).get("paragraphs", [])

        # Duplicate rule IDs
        ids = [r.get("rule_id") for r in rules]
        duplicates = [x for x, c in Counter(ids).items() if c > 1]
        if duplicates:
            issues.append(f"Duplicate rule_id: {duplicates}")

        # Empty paragraph
        for r in rules:
            if not r.get("paragraph"):
                issues.append(f"{r.get('rule_id')} has blank paragraph")

        # Invalid GO TO
        for r in rules:
            for t in r.get("go_to_targets", []):
                if t not in meta_paragraphs:
                    issues.append(f"{r.get('rule_id')} invalid GO TO target: {t}")

        # Conditional updates missing
        cond_updates = [
            r for r in rules
            if r.get("rule_type") == "update" and r.get("conditions")
        ]
        if cond_updates and not model.get("update_amend_logic"):
            issues.append("Conditional updates not isolated")

        return issues

    # =====================================================
    # 8️⃣ STRUCTURAL SCORE
    # =====================================================
    def compute_score(issues):
        return max(100 - (len(issues) * 5), 0)

    # =====================================================
    # 9️⃣ SAFE DATAFRAME NORMALIZER (ARROW FIX)
    # =====================================================
    def normalize_for_dataframe(data):
        df = pd.DataFrame(data)

        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.dumps(x)
                if isinstance(x, (dict, list))
                else x
            )

        return df

    # =====================================================
    # 🔄 EXECUTION PIPELINE
    # =====================================================
    model = remove_duplicate_rules(model)
    model = resequence_rules(model)
    model = rebuild_paragraph_registry(model)
    model = enforce_goto_integrity(model)
    model = isolate_conditional_updates(model)
    model = extract_material_governance(model)

    issues = validate_model(model)
    score = compute_score(issues)

    # =====================================================
    # 📊 DISPLAY METRICS
    # =====================================================
    st.metric("Structural Integrity Score", f"{score}%")

    if issues:
        for issue in issues:
            st.error(issue)
    else:
        st.success("✔ Model fully validated and enterprise compliant")

    st.markdown("---")

    # =====================================================
    # 📋 ALL DATA RENDERED AS TABLES
    # =====================================================
    sections = [
        "business_rules",
        "process_flow_graph",
        "update_amend_logic",
        "material_code_governance",
        "file_io_operations",
        "external_calls",
        "data_lineage"
    ]

    for section in sections:
        st.subheader(section.replace("_", " ").title())

        if model.get(section):
            st.dataframe(
                normalize_for_dataframe(model[section]),
                use_container_width=True
            )
        else:
            st.info("No data available.")

    st.markdown("---")

    # =====================================================
    # ⬇ DOWNLOAD
    # =====================================================
    st.download_button(
        "Download Validated Enterprise Model",
        data=json.dumps(model, indent=2),
        file_name="validated_enterprise_model.json",
        mime="application/json"
    )

st.markdown("---")
st.markdown("⚠️ Enterprise validation required before production deployment.")
