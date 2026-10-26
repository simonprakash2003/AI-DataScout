from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from data_pipeline import clean_clinics, quality_report, extract_clinic_jsonld, extract_clinic_listing_html, scrape_wikipedia_category
from ai_insights import ai_summary

BASE_DIR = Path(__file__).parent
SAMPLE_PATH = BASE_DIR / "sample_data.csv"

st.set_page_config(page_title="AI DataScout", page_icon="🔎", layout="wide")
st.title("🔎 AI DataScout")
st.caption("Public-data intelligence for permitted and responsibly sourced Australian GP clinic listings.")
st.info("Demo note: sample_data.csv contains fictional example records and example.org URLs. Replace it only with data you are authorized to use.")

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload an authorized CSV", type=["csv"])
    use_sample = st.checkbox("Load included demo data", value=uploaded is None)
    st.divider()
    st.subheader("Optional one-page extractor")
    extraction_mode = st.selectbox(
    "Extraction method",
    ["JSON-LD structured data", "HTML clinic listing"],)
    source_url = st.text_input("Authorized page URL", placeholder="https://permitted-source.example/page")
    permission = st.checkbox("I verified the source terms and have permission to fetch this page.")
    st.caption("Single-page only. Fetching is blocked unless robots.txt permits it. This check does not replace source permission.")
    run_extract = st.button("Extract", disabled=not (source_url and permission))
    


st.subheader("Live web data collection — Wikipedia")

max_pages = st.slider(
    "Maximum article records",
    min_value=5,
    max_value=30,
    value=10,
)

if st.button("Collect live Wikipedia data"):
    try:
        with st.spinner("Collecting live category records..."):
            records = scrape_wikipedia_category(max_pages)

        st.session_state["wikipedia_records"] = records

        st.success(
            f"Collected {len(records)} live article records."
        )
    except Exception as exc:
        st.error(f"Collection failed: {exc}")

wiki_records = st.session_state.get("wikipedia_records", [])

if wiki_records:
    wiki_df = pd.DataFrame(wiki_records)

    st.metric("Live records collected", len(wiki_df))
    st.dataframe(wiki_df, use_container_width=True)

    st.download_button(
        "Download Wikipedia data as CSV",
        data=wiki_df.to_csv(index=False).encode("utf-8"),
        file_name="wikipedia_category_data.csv",
        mime="text/csv",
    )

# Use the HTML extraction method when selected.

if run_extract and extraction_mode == "HTML clinic listing":
    try:
        records = extract_clinic_listing_html(
            source_url,
            confirmed_permission=permission,
        )

        if records:
            st.session_state["extracted_records"] = records
            st.success(f"Found {len(records)} candidate links.")
        else:
            st.warning("No candidate links found.")

    except Exception as exc:
        st.error(f"Extraction stopped: {exc}")


if run_extract and extraction_mode == "JSON-LD structured data":
    try:
        records = extract_clinic_jsonld(source_url, confirmed_permission=permission)
        if records:
            st.session_state["extracted_records"] = records
            st.success(f"Extracted {len(records)} structured record(s).")
        else:
            st.warning("No supported clinic/business JSON-LD records were found on that page.")
    except Exception as exc:
        st.error(f"Extraction stopped: {exc}")


if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded, dtype=str).fillna("")
        data_source_label = f"Uploaded file: {uploaded.name}"
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()

elif st.session_state.get("extracted_records"):
    raw = pd.DataFrame(
        st.session_state["extracted_records"]
    ).fillna("")
    data_source_label = "Authorized web extraction"

elif use_sample:
    raw = pd.read_csv(SAMPLE_PATH, dtype=str).fillna("")
    data_source_label = "Fictional demo dataset"

else:
    st.warning("Upload a CSV, extract web data, or load the demo dataset.")
    st.stop()


df = clean_clinics(raw)

# --------------------------------
# Optional Filters
# --------------------------------
with st.sidebar:
    st.divider()
    st.subheader("Optional Filters")

    enable_filters = st.checkbox(
        "Enable filters",
        value=False,
    )

    states = sorted(
        x for x in df["state"].fillna("").astype(str).unique()
        if x.strip()
    )

    selected_states = states
    search_text = ""

    if enable_filters:
        selected_states = st.multiselect(
            "State/territory",
            options=states,
            default=states,
        )
        search_text = st.text_input(
            "Search clinic, suburb, or services"
        )

# Show all cleaned data unless filters are enabled
if enable_filters:
    filtered = df[df["state"].isin(selected_states)].copy()

    if search_text.strip():
        mask = filtered[
            ["clinic_name", "suburb", "services"]
        ].fillna("").astype(str).apply(
            lambda col: col.str.contains(
                search_text.strip(),
                case=False,
                regex=False,
            )
        ).any(axis=1)

        filtered = filtered[mask]
else:
    filtered = df.copy()

# --------------------------------
# Data Intelligence Dashboard
# --------------------------------
st.subheader("Data Intelligence Dashboard")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Clinic Records", f"{len(filtered):,}")
c2.metric(
    "States Represented",
    filtered["state"].replace("", pd.NA).dropna().nunique(),
)
c3.metric(
    "Websites Listed",
    int(filtered["website"].fillna("").astype(str).str.strip().ne("").sum()),
)
c4.metric(
    "Phones Listed",
    int(filtered["phone"].fillna("").astype(str).str.strip().ne("").sum()),
)

left, right = st.columns([1.5, 1])

with left:
    st.subheader("Clinic Directory")
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
    )

with right:
    st.subheader("Records by State")
    counts = (
        filtered[filtered["state"].str.strip().ne("")]["state"]
        .value_counts()
        .rename_axis("state")
        .reset_index(name="records")
    )

    if counts.empty:
        st.info("No state information is available for this selection.")
    else:
        st.plotly_chart(
            px.bar(
                counts,
                x="state",
                y="records",
                title="Clinic Records by State",
            ),
            use_container_width=True,
        )

# --------------------------------
# Data Quality
# --------------------------------
st.subheader("Data Quality")

quality = quality_report(filtered)
q1, q2 = st.columns(2)

q1.metric("Field Completeness", f"{quality['completeness_pct']}%")
q2.metric("Rows Analyzed", quality["rows"])

with st.expander("Missing Fields by Column"):
    st.json(quality["missing_by_column"])

# --------------------------------
# AI Data Insights
# --------------------------------
st.subheader("AI-Generated Data Insights")

st.caption(
    "Insights describe the selected dataset and do not assess "
    "medical quality or provide medical advice."
)

if st.button("Generate Insights"):
    with st.spinner("Analyzing data..."):
        st.markdown(ai_summary(filtered))

# --------------------------------
# Download
# --------------------------------
st.download_button(
    "Download Cleaned Results (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="ai_datascout_cleaned.csv",
    mime="text/csv",
)

st.caption(
    "Retain source URLs and verification dates. "
    "Clearly identify fictional demo records."
)
