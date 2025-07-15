import pandas as pd
import time
import google.generativeai as genai
from tqdm import tqdm
import re
import sys
import os
import json

# 🔐 List of Gemini API Keys
api_keys = [
     Enter Your API Keys
]

KEY_USAGE_LIMIT = 15
current_key_index = 0
calls_with_current_key = 0


# 🔄 Function to load Gemini model with a given key
def load_gemini_model(api_key, key_index):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
    try:
        test = model.generate_content("Say OK").text.strip()
        if "OK" not in test:
            raise RuntimeError("Unexpected Gemini response")
        print(f"✅ Gemini initialized with API key #{key_index + 1}")
        return model
    except Exception as e:
        print(f"❌ Failed to initialize Gemini model with key #{key_index + 1}: {e}")
        sys.exit(1)


# ⏳ Load first model
model = load_gemini_model(api_keys[current_key_index], current_key_index)

# ✏️ Target company business description for relevance scoring
target_bd = """Target Company:Gabriel India Limited manufactures and sells ride control products to the automotive industry in India, the Netherlands, and internationally. The company provides canister shock absorbers, telescopic front fork, inverted front fork, canister and big piston design, mono shox, shock absorbers, rear shock absorbers, strut assemblies, FSD suspension; and axle, cabin, and seat dampers. It also offers double-acting hydraulic shock absorbers for conventional coach, shock absorber for EMU/ MEMU/ DMU coach, dampers for diesel locomotive, dampers for rajdhani and shatabadi coach, damper for ICF train 18- vande bharat coach, damper for electric locomotive, and damper for vande bharat coach. In addition, the company provides Macpherson struts, gas springs, brake pads, drive shafts, suspension parts, suspension and strut bush kits, OC springs, coolants, brake fluids, front fork components, oil seals, front fork oil wheel rims, spokes cone sets, and tyres and tubes, as well as offers mountain bikes and modern e-bikes products. Its products are used in two and three wheelers, passenger cars, commercial vehicles, railways, off highway, aftermarkets, and sunroof applications. The company sells its products through carrying and forwarding agents, retailers, and distributors. It also exports its products. The company was incorporated in 1961 and is headquartered in Pune, India. Gabriel India Limited is a subsidiary of Asia Investments Private Limited."""

# 📂 Load Excel
df = pd.read_excel("BD_Oil2.xlsx")  # Must have "Company Name" and "Business Description"

print("📊 Excel file columns:", df.columns.tolist())
print("📊 First 3 rows of data:")
print(df.head(3))
print(f"📊 Total companies to process: {len(df)}")

# 🗂️ Output setup
output_file = "business_classifications.xlsx"
results = []
batch_size = 3  # Process companies in batches


# Function to clean and convert relevance score to float
def clean_relevance_score(score):
    """Convert relevance score to float, handling various input types"""
    if pd.isna(score):
        return 0.00

    # If it's already a number, return it
    if isinstance(score, (int, float)):
        return float(score)

    # If it's a string, try to extract numeric value
    if isinstance(score, str):
        # Remove any non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', str(score))
        try:
            return float(cleaned) if cleaned else 0.00
        except ValueError:
            return 0.00

    return 0.00


# Function to process a batch of companies
def process_batch(batch_df, batch_num):
    global current_key_index, calls_with_current_key, model

    print(f"\n🔄 Processing batch {batch_num} ({len(batch_df)} companies)")

    # Prepare batch data for prompt
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

    # Create batch prompt
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
4. **Key Products/Services**: Main products or services offered.
5. **Market Focus**: Geographic or market segment focus.
6. **Relevance Score**: A numerical score from 1.00%–100.00% representing the company's relevance/similarity to the target company. Consider factors like:
   - Similar products or services
   - Overlapping market segments
   - Complementary business activities
   - Potential for partnerships or competition
   - Industry alignment
   Make sure the score is precise to two decimal points and MUST be a number (not text).
7. **Relevance Reason**: A detailed 1-2 sentence explanation for the relevance score, specifically comparing the company to target company.

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
Ensure the JSON is properly formatted and includes all companies listed above.
"""

    # 🔄 Rotate API key if limit exceeded
    calls_with_current_key += 1
    if calls_with_current_key > KEY_USAGE_LIMIT:
        current_key_index = (current_key_index + 1) % len(api_keys)
        model = load_gemini_model(api_keys[current_key_index], current_key_index)
        calls_with_current_key = 1

    retries = 0
    max_retries = 3

    while retries < max_retries:
        try:
            print(f"🤖 Sending batch {batch_num} to Gemini...")
            response = model.generate_content(prompt)
            full_response = response.text.strip()

            print(f"🤖 Gemini Response for batch {batch_num}:")
            print("=" * 80)
            print(full_response[:500] + "..." if len(full_response) > 500 else full_response)
            print("=" * 80)

            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_start = full_response.find('{')
                json_end = full_response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = full_response[json_start:json_end]
                else:
                    raise ValueError("No JSON found in response")

            # Parse JSON
            try:
                parsed_data = json.loads(json_str)
                companies_analysis = parsed_data.get('companies', [])

                if len(companies_analysis) != len(companies_data):
                    print(f"⚠️ Warning: Expected {len(companies_data)} companies, got {len(companies_analysis)}")

                # Process results
                batch_results = []
                for i, comp_data in enumerate(companies_data):
                    if i < len(companies_analysis):
                        analysis = companies_analysis[i]

                        # Clean and convert relevance score
                        raw_score = analysis.get("relevance_score", 0.00)
                        cleaned_score = clean_relevance_score(raw_score)

                        result_entry = {
                            "Company Name": comp_data["name"],
                            "Original Business Description": comp_data["description"],
                            "Business Summary": analysis.get("business_summary", "No summary available"),
                            "Industry Classification": analysis.get("industry_classification", "Not classified"),
                            "Business Model": analysis.get("business_model", "Not specified"),
                            "Key Products/Services": analysis.get("key_products_services", "Not specified"),
                            "Market Focus": analysis.get("market_focus", "Not specified"),
                            "Relevance Score": cleaned_score,
                            "Relevance Reason": analysis.get("relevance_reason", "No reason provided")
                        }
                    else:
                        # Fallback for missing analysis
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

                print(f"✅ Successfully processed batch {batch_num}")
                return batch_results

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                raise ValueError(f"Invalid JSON format: {e}")

        except Exception as e:
            retries += 1
            print(f"⚠️ Error processing batch {batch_num} (attempt {retries}/3): {e}")
            if retries < max_retries:
                time.sleep(10)
            else:
                print(f"❌ Failed to process batch {batch_num} after {max_retries} attempts")
                # Return default entries for failed batch
                return [{
                    "Company Name": comp["name"],
                    "Original Business Description": comp["description"],
                    "Business Summary": "Processing failed",
                    "Industry Classification": "Error",
                    "Business Model": "Error",
                    "Key Products/Services": "Error",
                    "Market Focus": "Error",
                    "Relevance Score": 0.00,
                    "Relevance Reason": "Processing error"
                } for comp in companies_data]


# 🔁 Process companies in batches
total_batches = (len(df) + batch_size - 1) // batch_size
all_results = []

for batch_num in range(total_batches):
    start_idx = batch_num * batch_size
    end_idx = min((batch_num + 1) * batch_size, len(df))
    batch_df = df.iloc[start_idx:end_idx]

    batch_results = process_batch(batch_df, batch_num + 1)
    all_results.extend(batch_results)

    # Save intermediate results
    if (batch_num + 1) % 5 == 0 or batch_num == total_batches - 1:
        intermediate_df = pd.DataFrame(all_results)
        intermediate_file = f"intermediate_classifications_{batch_num + 1}.xlsx"
        intermediate_df.to_excel(intermediate_file, index=False)
        print(f"💾 Saved intermediate results: {intermediate_file}")

    # Brief pause between batches
    if batch_num < total_batches - 1:
        time.sleep(2)

# 📊 Create final output
print("📦 Creating final output...")
final_df = pd.DataFrame(all_results)

print(f"📊 Final dataset contains {len(final_df)} companies")
print(f"📊 Columns: {final_df.columns.tolist()}")

# Fill any NaN values
final_df = final_df.fillna("Not specified")

# FIXED: Clean relevance scores before sorting
print("🔧 Cleaning relevance scores...")
final_df['Relevance Score'] = final_df['Relevance Score'].apply(clean_relevance_score)

# Ensure all relevance scores are within valid range (0-100)
final_df['Relevance Score'] = final_df['Relevance Score'].clip(0, 100)

# Sort by relevance score (highest first)
final_df = final_df.sort_values('Relevance Score', ascending=False)

# Create output with multiple sheets for better organization
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Main results
    final_df.to_excel(writer, sheet_name='All_Companies', index=False)

    # High relevance companies (score >= 70)
    high_relevance = final_df[final_df['Relevance Score'] >= 70.00]
    if len(high_relevance) > 0:
        high_relevance.to_excel(writer, sheet_name='High_Relevance_70+', index=False)

    # Medium relevance companies (score 50-69.99)
    medium_relevance = final_df[(final_df['Relevance Score'] >= 50.00) & (final_df['Relevance Score'] < 70.00)]
    if len(medium_relevance) > 0:
        medium_relevance.to_excel(writer, sheet_name='Medium_Relevance_50-69', index=False)

    # Low relevance companies (score < 50)
    low_relevance = final_df[final_df['Relevance Score'] < 50.00]
    if len(low_relevance) > 0:
        low_relevance.to_excel(writer, sheet_name='Low_Relevance_Below_50', index=False)

print(f"✅ Final results saved: {output_file}")

# 🧹 Clean up intermediate files
intermediate_files = [f for f in os.listdir() if f.startswith("intermediate_classifications_") and f.endswith(".xlsx")]
for f in intermediate_files:
    try:
        os.remove(f)
        print(f"🗑️ Deleted intermediate file: {f}")
    except Exception as e:
        print(f"⚠️ Could not delete {f}: {e}")

# 📊 Print summary statistics
print("\n🎉 Processing complete!")
print(f"📋 Summary:")
print(f"   • Total companies processed: {len(final_df)}")
print(f"   • Output file: {output_file}")
print(
    f"   • Columns created: Business Summary, Industry Classification, Business Model, Key Products/Services, Market Focus, Relevance Score, Relevance Reason")

# Relevance score distribution
high_count = len(final_df[final_df['Relevance Score'] >= 70.00])
medium_count = len(final_df[(final_df['Relevance Score'] >= 50.00) & (final_df['Relevance Score'] < 70.00)])
low_count = len(final_df[final_df['Relevance Score'] < 50.00])

print(f"\n📊 Relevance Score Distribution:")
print(f"   • High Relevance (70+): {high_count} companies")
print(f"   • Medium Relevance (50-69): {medium_count} companies")
print(f"   • Low Relevance (<50): {low_count} companies")

if high_count > 0:
    avg_high = final_df[final_df['Relevance Score'] >= 70.00]['Relevance Score'].mean()
    print(f"   • Average high relevance score: {avg_high:.2f}")

if len(final_df) > 0:
    overall_avg = final_df['Relevance Score'].mean()
    print(f"   • Overall average relevance score: {overall_avg:.2f}")
