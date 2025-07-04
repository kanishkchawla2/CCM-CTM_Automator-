import pandas as pd
import time
import google.generativeai as genai
from tqdm import tqdm
import re
import sys
import os

# 🔐 Gemini API Setup
try:
    genai.configure(api_key="AIzaSyDQItObHG6C80KP1-0-ZyaGZehcvHPN4tY")
    model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

    # 🔍 Test Gemini initialization
    test = model.generate_content("Say OK").text.strip()
    if "OK" not in test:
        raise RuntimeError("Gemini model responded but not as expected.")
    print("✅ Gemini is successfully initialized and responding.")

except Exception as e:
    print(f"❌ Failed to initialize Gemini model: {e}")
    sys.exit(1)

# ✏️ Target company BD
target_bd = """
"ABC is a global merchant and processor of agricultural goods. It's a leading company in the agricultural sector, sourcing, transporting, and transforming products for customers worldwide. It operates across various business lines, including Coffee, Cotton, Freight, Food & Feed Solutions, Grains & Oilseeds, Juice, Rice, and Sugar. The company has a significant presence in India "
"""

# 📂 Load Excel
df = pd.read_excel("BD_EV.xlsx")  # Must have "Company Name" and "Business Description"

# Debug: Print column names and first few rows
print("📊 Excel file columns:", df.columns.tolist())
print("📊 First 3 rows of data:")
print(df.head(3))

# 🗂️ Output setup
output_file = "matched_comparables.xlsx"
results = []
chunk_count = 0  # To track and name chunks

# 🔁 Loop through each company
for idx, row in tqdm(df.iterrows(), total=len(df), desc="🔍 Matching Companies"):

    comp_name = row["Company Name"]
    comp_bd = row["Business Description"]

    # Debug: Print current company info
    print(f"\n🔍 Processing: {comp_name}")
    print(f"📝 BD Preview: {str(comp_bd)[:100]}..." if pd.notna(comp_bd) else "📝 BD: [BLANK/NaN]")

    # Handle NaN or empty business descriptions
    if pd.isna(comp_bd) or comp_bd == "" or str(comp_bd).strip() == "":
        comp_bd = "No business description available"
        print(f"⚠️ Warning: Empty BD for {comp_name}, using default text")

    # 🔁 Prompt with score + explanation
    prompt = f"""
You are an equity research analyst evaluating potential acquisition targets for Louis Dreyfus, which is looking to expand it's operations into edible oils.

The objective is to acquire a company that operates in one or more of the following:
- Processing/refining of edible oils (e.g., palm, soybean, sunflower, mustard, groundnut)
- Bulk or packaged oil distribution (domestic or export markets)
- Crude oil import and refining infrastructure
- Contract manufacturing or white-label edible oil brands
- Integrated value chain: from oilseed crushing to packaging and B2B/B2C distribution

{target_bd}

Comparable Company: {comp_name}
Comparable Company Description:
{comp_bd}

Instructions:
1. Use your internal understanding and search capability to verify the comparable company.
2. Give a similarity score from 0% to 100% with decimal precision (e.g., 91.35%).
3. After the score, write a short 1–2 line reason explaining why you gave that score.
4. Return 0 if you can't find a match and give reason.
4. Format your response like this:
91.35%

"""

    score = "Error"
    reason = ""
    retries = 0
    max_retries = 3

    while retries < max_retries:
        try:
            response = model.generate_content(prompt)
            full_response = response.text.strip()

            # 📢 Print Gemini's full response for debugging
            print(f"\n🤖 Gemini Response for {comp_name}:")
            print("=" * 80)
            print(full_response)
            print("=" * 80)

            # ✅ Try to extract a % score using regex
            match = re.search(r"(\d{1,3}(?:\.\d+)?)[ ]?%", full_response)
            if match:
                score = round(float(match.group(1)), 2)
                reason = full_response[match.end():].strip()
                print(f"✅ Extracted Score: {score}%")
                print(f"✅ Extracted Reason: {reason}")
            else:
                score = 0.00
                reason = "No valid score found, defaulted to 0.00%."
                print(f"⚠️ No score pattern found in response, defaulting to 0.00%")
            break

        except Exception as e:
            retries += 1
            print(f"⚠️ Error with {comp_name} (attempt {retries}/3): {e}")
            time.sleep(10)

    # Store results with explicit handling of BD
    result_entry = {
        "Company Name": str(comp_name) if pd.notna(comp_name) else "Unknown",
        "Business Description": str(comp_bd) if pd.notna(comp_bd) else "No description available",
        "Similarity Score (%)": score if score != "Error" else "Error",
        "Reason for Score": reason if score != "Error" else "N/A"
    }

    results.append(result_entry)

    # Debug: Print what we're storing
    print(f"💾 Storing BD: {result_entry['Business Description'][:50]}...")

    # 💾 Save chunk after every 10 rows
    if (idx + 1) % 10 == 0 or idx == len(df) - 1:
        chunk_count += 1
        chunk_file = f"matched_chunk_{chunk_count}.xlsx"
        chunk_df = pd.DataFrame(results)

        # Debug: Print chunk info before saving
        print(f"📊 Chunk {chunk_count} has {len(chunk_df)} rows")
        if len(chunk_df) > 0:
            sample_bd = chunk_df.iloc[0]['Business Description']
            if pd.notna(sample_bd):
                print(f"📊 Sample BD from chunk: {str(sample_bd)[:50]}...")
            else:
                print("📊 Sample BD from chunk: [NaN/Empty]")

        chunk_df.to_excel(chunk_file, index=False)
        print(f"💾 Saved chunk: {chunk_file}")
        results = []  # Clear the chunk list

        # ⏱️ Wait after chunk save
        print("⏱️ Waiting 5 seconds after saving chunk...")
        time.sleep(5)

    # 🕒 Sleep after each company
    time.sleep(1)

# 🧩 Combine all chunks into final output
print("📦 Combining all chunks into final output...")
chunk_files = [f for f in os.listdir() if f.startswith("matched_chunk_") and f.endswith(".xlsx")]
if chunk_files:
    combined_df = pd.concat([pd.read_excel(f) for f in chunk_files], ignore_index=True)

    # Debug: Check final combined data
    print(f"📊 Final combined data has {len(combined_df)} rows")
    print(f"📊 Columns: {combined_df.columns.tolist()}")

    # Safe way to check sample BD (handle potential NaN/float values)
    if len(combined_df) > 0:
        sample_bd = combined_df.iloc[0]['Business Description']
        if pd.notna(sample_bd):
            print(f"📊 Sample final BD: {str(sample_bd)[:50]}...")
        else:
            print("📊 Sample final BD: [NaN/Empty]")

    # Clean up any remaining NaN values before saving
    combined_df['Business Description'] = combined_df['Business Description'].fillna("No description available")

    combined_df.to_excel(output_file, index=False)
    print(f"✅ Done. Final file saved: {output_file}")
else:
    print("⚠️ No chunk files found to combine!")

# 🧹 Clean up chunk files
for f in chunk_files:
    try:
        os.remove(f)
        print(f"🗑️ Deleted chunk file: {f}")
    except Exception as e:
        print(f"⚠️ Could not delete {f}: {e}")
