import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from tqdm import tqdm
import re
import json
import io
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Business Classification Tool",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling and hiding GitHub button
st.markdown("""
<style>
    /* Hide GitHub button - comprehensive approach */
    button[aria-label="View the source code of this app in a repository"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        top: -9999px !important;
    }
    
    /* Hide GitHub button by class */
    .stToolbarButton {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        top: -9999px !important;
    }
    
    /* Hide the entire toolbar */
    .stToolbar {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        top: -9999px !important;
    }
    
    /* Hide any element with GitHub-related text */
    button:contains("GitHub"), button:contains("github") {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        top: -9999px !important;
    }
    
    /* Hide elements with specific data attributes */
    [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        top: -9999px !important;
    }
    
    /* Hide the main menu (hamburger menu) */
    #MainMenu {
        display: none;
    }
    
    /* Hide footer */
    footer {
        display: none;
    }
    
    /* Hide "Made with Streamlit" footer */
    .streamlit-footer {
        display: none;
    }
    
    /* Hide sidebar completely */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Style for collapsible sections */
    .collapsible-header {
        background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    
    /* Style for toggle buttons */
    .toggle-button {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .toggle-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
    }

    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }

    .stButton > button {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
    }

    .metric-container {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4f46e5;
        margin: 1rem 0;
    }

    .success-message {
        background: #dcfce7;
        color: #166534;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    .error-message {
        background: #fef2f2;
        color: #dc2626;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'api_keys' not in st.session_state:
    st.session_state.api_keys = []
if 'show_api_config' not in st.session_state:
    st.session_state.show_api_config = True


# Utility Functions
def clean_relevance_score(score):
    """Convert relevance score to float, handling various input types"""
    if pd.isna(score):
        return 0.00

    if isinstance(score, (int, float)):
        return float(score)

    if isinstance(score, str):
        cleaned = re.sub(r'[^\d.]', '', str(score))
        try:
            return float(cleaned) if cleaned else 0.00
        except ValueError:
            return 0.00

    return 0.00


def load_gemini_model(api_key, key_index):
    """Load Gemini model with given API key"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

        # Test the model
        test = model.generate_content("Say OK").text.strip()
        if "OK" not in test:
            raise RuntimeError("Unexpected Gemini response")

        return model
    except Exception as e:
        raise Exception(f"Failed to initialize Gemini model: {e}")


def process_batch(batch_df, batch_num, model, target_bd, api_keys, current_key_index, calls_with_current_key,
                  key_usage_limit):
    """Process a single batch of companies"""

    # Prepare batch data
    companies_data = []
    for idx, row in batch_df.iterrows():
        comp_name = row["Company Name"]
        comp_bd = row["Business Description"]

        if pd.isna(comp_bd) or comp_bd == "" or str(comp_bd).strip() == "":
            comp_bd = "No business description available"

        companies_data.append({
            "name": str(comp_name) if pd.notna(comp_name) else "Unknown",
            "description": str(comp_bd)
        })

    # Create prompt
    prompt = f"""
You are a business analyst tasked with analyzing companies and comparing them to a target company for potential business opportunities, partnerships, or market relevance.

**TARGET COMPANY REFERENCE:**
{target_bd}

**COMPANIES TO ANALYZE:**
{chr(10).join([f"{i + 1}. {comp['name']}: {comp['description']}" for i, comp in enumerate(companies_data)])}

For each company, analyze and return the following information:

1. **Business Summary**: A clear, concise 1-2 sentence summary of what the company actually does.
2. **Industry Classification**: Primary industry/sector.
3. **Business Model**: How the company makes money.
4. **Key Products/Services**: Main products or services offered.s
5. **Market Focus**: Geographic or market segment focus.
6. **Relevance Score**: A numerical score from 1.00–100.00 representing the company's relevance/similarity to the target company.
7. **Relevance Reason**: A detailed 1-2 sentence explanation for the relevance score.

**Required Response Format:**
```json
{{
  "companies": [
    {{
      "company_name": "Company Name",
      "business_summary": "Clear summary of what they do",
      "industry_classification": "Primary industry",
      "business_model": "How they make money",
      "key_products_services": "Main products/services",
      "market_focus": "Geographic/market focus",
      "relevance_score": 75.50,
      "relevance_reason": "Detailed reason comparing to target company"
    }}
  ]
}}
```

IMPORTANT: The relevance_score MUST be a numeric value (like 75.50), not text or string.
"""

    # Rotate API key if needed
    calls_with_current_key += 1
    if calls_with_current_key > key_usage_limit:
        current_key_index = (current_key_index + 1) % len(api_keys)
        model = load_gemini_model(api_keys[current_key_index], current_key_index)
        calls_with_current_key = 1

    # Make API call
    max_retries = 3
    for retry in range(max_retries):
        try:
            response = model.generate_content(prompt)
            full_response = response.text.strip()

            # Extract JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_start = full_response.find('{')
                json_end = full_response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = full_response[json_start:json_end]
                else:
                    raise ValueError("No JSON found in response")

            # Parse JSON
            parsed_data = json.loads(json_str)
            companies_analysis = parsed_data.get('companies', [])

            # Process results
            batch_results = []
            for i, comp_data in enumerate(companies_data):
                if i < len(companies_analysis):
                    analysis = companies_analysis[i]
                    result_entry = {
                        "Company Name": comp_data["name"],
                        "Original Business Description": comp_data["description"],
                        "Business Summary": analysis.get("business_summary", "No summary available"),
                        "Industry Classification": analysis.get("industry_classification", "Not classified"),
                        "Business Model": analysis.get("business_model", "Not specified"),
                        "Key Products/Services": analysis.get("key_products_services", "Not specified"),
                        "Market Focus": analysis.get("market_focus", "Not specified"),
                        "Relevance Score": analysis.get("relevance_score", 0.00),
                        "Relevance Reason": analysis.get("relevance_reason", "No reason provided")
                    }
                else:
                    result_entry = {
                        "Company Name": comp_data["name"],
                        "Original Business Description": comp_data["description"],
                        "Business Summary": "Analysis not available",
                        "Industry Classification": "Not classified",
                        "Business Model": "Not specified",
                        "Key Products/Services": "Not specified",
                        "Market Focus": "Not specified",
                        "Relevance Score": 0.00,
                        "Relevance Reason": "Analysis incomplete"
                    }

                batch_results.append(result_entry)

            return batch_results

        except Exception as e:
            if retry < max_retries - 1:
                time.sleep(5)
                continue
            else:
                # Return error entries
                return [{
                    "Company Name": comp["name"],
                    "Original Business Description": comp["description"],
                    "Business Summary": "Processing failed",
                    "Industry Classification": "Error",
                    "Business Model": "Error",
                    "Key Products/Services": "Error",
                    "Market Focus": "Error",
                    "Relevance Score": 0.00,
                    "Relevance Reason": f"Processing error: {str(e)}"
                } for comp in companies_data]


def process_companies(df, target_bd, batch_size, key_usage_limit):
    """Process companies using Gemini API"""

    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        api_keys = st.session_state.api_keys
        current_key_index = 0
        calls_with_current_key = 0

        # Load first model
        model = load_gemini_model(api_keys[current_key_index], current_key_index)

        total_batches = (len(df) + batch_size - 1) // batch_size
        all_results = []

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]

            status_text.text(f"Processing batch {batch_num + 1}/{total_batches}")

            # Process batch
            batch_results = process_batch(batch_df, batch_num + 1, model, target_bd,
                                          api_keys, current_key_index, calls_with_current_key, key_usage_limit)

            all_results.extend(batch_results)

            # Update progress
            progress = (batch_num + 1) / total_batches
            progress_bar.progress(progress)

            # Brief pause between batches
            if batch_num < total_batches - 1:
                time.sleep(1)

        # Create final results dataframe
        final_df = pd.DataFrame(all_results)
        final_df['Relevance Score'] = final_df['Relevance Score'].apply(clean_relevance_score)
        final_df['Relevance Score'] = final_df['Relevance Score'].clip(0, 100)
        final_df = final_df.sort_values('Relevance Score', ascending=False)

        # Store results in session state
        st.session_state.results_df = final_df
        st.session_state.processing_complete = True

        status_text.text("✅ Processing complete!")
        st.success(f"🎉 Successfully processed {len(final_df)} companies!")

        # Switch to results tab
        st.balloons()

    except Exception as e:
        st.error(f"❌ Error during processing: {str(e)}")
        progress_bar.empty()
        status_text.empty()


# Header
st.markdown("""
<div class="main-header">
    <h1>🏢 Business Classification Tool</h1>
    <p>Analyze and classify companies using AI-powered business intelligence</p>
</div>
""", unsafe_allow_html=True)

# Collapsible API Configuration Section

# Compact header with inline toggle
st.markdown("""
<div style="display: flex; align-items: center; gap: 10px; margin: 0;">
    <div style="display: inline-block;">
""", unsafe_allow_html=True)

toggle_text = "🔐 API Configuration" if st.session_state.show_api_config else "🔐 API Configuration"
if st.button(toggle_text, key="toggle_api_config"):
    st.session_state.show_api_config = not st.session_state.show_api_config
    st.rerun()

st.markdown("""
    </div>
</div>
""", unsafe_allow_html=True)

# Show/hide API configuration based on state
if st.session_state.show_api_config:
    # Add API key input
    new_api_key = st.text_input("Add Gemini API Key", type="password", placeholder="Enter your Gemini API key")

    # Buttons below the input field
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Key", use_container_width=True):
            if new_api_key and new_api_key not in st.session_state.api_keys:
                st.session_state.api_keys.append(new_api_key)
                st.success("API key added!")
                st.rerun()

    with col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.api_keys = []
            st.success("All keys cleared!")
            st.rerun()

    # Display current API keys
    if st.session_state.api_keys:
        st.write(f"**Current Keys:** {len(st.session_state.api_keys)}")
        for i, key in enumerate(st.session_state.api_keys):
            key_col1, key_col2 = st.columns([3, 1])
            with key_col1:
                st.code(f"Key {i + 1}: {key[:8]}...{key[-4:]}", language="text")
            with key_col2:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.api_keys.pop(i)
                    st.rerun()
    else:
        st.warning("No API keys added yet")

    # Processing Configuration
    st.subheader("⚙️ Processing Settings")
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=3,
                               help="Number of companies to process in each batch")
    with config_col2:
        key_usage_limit = st.slider("Key Usage Limit", min_value=5, max_value=50, value=15,
                                    help="Number of API calls per key before rotation")

st.markdown("---")

# Main content area
tab1, tab2, tab3 = st.tabs(["📁 Upload & Process", "📊 Results", "📈 Analytics"])

with tab1:
    st.header("📁 File Upload & Processing")

    # Target company description
    st.subheader("🎯 Target Company Reference")
    target_bd = st.text_area(
        "Enter target company business description (for relevance scoring)",
        placeholder="Enter the business description of your target company for comparison...",
        height=100
    )

    # File upload
    st.subheader("📤 Upload Excel File")
    uploaded_file = st.file_uploader(
        "Choose an Excel file",
        type=['xlsx', 'xls'],
        help="File must contain 'Company Name' and 'Business Description' columns"
    )

    if uploaded_file is not None:
        try:
            # Read the uploaded file
            df = pd.read_excel(uploaded_file)

            # Display file info
            st.success(f"✅ File uploaded successfully!")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Companies", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")

            # Show column info
            st.subheader("📋 File Preview")
            st.write("**Columns found:**", df.columns.tolist())

            # Check for required columns
            required_cols = ['Company Name', 'Business Description']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                st.error(f"❌ Missing required columns: {missing_cols}")
                st.info("Please ensure your Excel file has 'Company Name' and 'Business Description' columns")
            else:
                st.success("✅ All required columns found!")

                # Show preview
                st.dataframe(df.head(10), use_container_width=True)

                # Processing button
                if st.session_state.api_keys and target_bd.strip():
                    if st.button("🚀 Start Processing", type="primary"):
                        process_companies(df, target_bd, batch_size, key_usage_limit)
                else:
                    if not st.session_state.api_keys:
                        st.warning("⚠️ Please add at least one API key in the sidebar")
                    if not target_bd.strip():
                        st.warning("⚠️ Please enter a target company description")

        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")

# Results tab
with tab2:
    st.header("📊 Processing Results")

    if st.session_state.processing_complete and st.session_state.results_df is not None:
        df_results = st.session_state.results_df

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", len(df_results))
        with col2:
            high_relevance = len(df_results[df_results['Relevance Score'] >= 70])
            st.metric("High Relevance (70+)", high_relevance)
        with col3:
            medium_relevance = len(
                df_results[(df_results['Relevance Score'] >= 50) & (df_results['Relevance Score'] < 70)])
            st.metric("Medium Relevance (50-69)", medium_relevance)
        with col4:
            avg_score = df_results['Relevance Score'].mean()
            st.metric("Average Score", f"{avg_score:.2f}")

        # Filters
        st.subheader("🔍 Filter Results")
        col1, col2 = st.columns(2)
        with col1:
            min_score = st.slider("Minimum Relevance Score", 0.0, 100.0, 0.0, 5.0)
        with col2:
            selected_industries = st.multiselect(
                "Filter by Industry",
                options=df_results['Industry Classification'].unique(),
                default=[]
            )

        # Apply filters
        filtered_df = df_results[df_results['Relevance Score'] >= min_score]
        if selected_industries:
            filtered_df = filtered_df[filtered_df['Industry Classification'].isin(selected_industries)]

        # Display results
        st.subheader(f"📋 Results ({len(filtered_df)} companies)")
        st.dataframe(filtered_df, use_container_width=True, height=400)

        # Download buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            # Full results
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="📥 Download Full Results (CSV)",
                data=csv,
                file_name=f"business_classifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        with col2:
            # Excel download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_results.to_excel(writer, sheet_name='All_Companies', index=False)

                # High relevance sheet
                high_rel = df_results[df_results['Relevance Score'] >= 70]
                if len(high_rel) > 0:
                    high_rel.to_excel(writer, sheet_name='High_Relevance_70+', index=False)

                # Medium relevance sheet
                medium_rel = df_results[(df_results['Relevance Score'] >= 50) & (df_results['Relevance Score'] < 70)]
                if len(medium_rel) > 0:
                    medium_rel.to_excel(writer, sheet_name='Medium_Relevance_50-69', index=False)

            output.seek(0)
            st.download_button(
                label="📥 Download Excel (Multi-sheet)",
                data=output,
                file_name=f"business_classifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col3:
            # Filtered results
            if len(filtered_df) != len(df_results):
                filtered_csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Filtered Results (CSV)",
                    data=filtered_csv,
                    file_name=f"filtered_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

    else:
        st.info("📋 No results available yet. Please process some companies first.")

# Analytics tab
with tab3:
    st.header("📈 Analytics Dashboard")

    if st.session_state.processing_complete and st.session_state.results_df is not None:
        df_results = st.session_state.results_df

        # Score distribution
        st.subheader("📊 Relevance Score Distribution")
        col1, col2 = st.columns(2)

        with col1:
            # Histogram
            fig_hist = st.bar_chart(df_results['Relevance Score'].value_counts().sort_index())

        with col2:
            # Industry distribution
            industry_counts = df_results['Industry Classification'].value_counts().head(10)
            st.bar_chart(industry_counts)

        # Top companies
        st.subheader("🏆 Top Companies by Relevance Score")
        top_companies = df_results.head(10)[
            ['Company Name', 'Relevance Score', 'Industry Classification', 'Business Summary']]
        st.dataframe(top_companies, use_container_width=True)

        # Business model analysis
        st.subheader("💼 Business Model Distribution")
        model_counts = df_results['Business Model'].value_counts().head(8)
        st.bar_chart(model_counts)

    else:
        st.info("📈 Analytics will be available after processing companies.")

# Footer
st.markdown("---")
st.markdown("**Built with Streamlit** | Business Classification Tool v1.0")
