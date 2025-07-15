# 🚀 Business Classification Tool

> *Turn your Excel spreadsheet into a smart business intelligence goldmine with AI-powered company analysis*

## 🎯 What This Tool Does

Imagine having a brilliant business analyst who can read through hundreds of company descriptions and instantly tell you:
- Which companies are most relevant to YOUR business
- What each company actually does (in plain English)
- How they make money and who they serve
- Why they matter to you (or don't)

That's exactly what this tool does, but faster and without coffee breaks.

## 🔥 Key Features

### 🧠 **Smart AI Analysis**
- Uses Google's Gemini AI to understand business descriptions
- Compares every company against your target business
- Generates relevance scores from 0-100%

### ⚡ **Production-Ready Performance**
- Processes companies in batches of 3 for efficiency
- Handles 4 API keys with automatic rotation
- Built-in retry logic for reliable operation
- Saves progress every 5 batches

### 📊 **Organized Output**
- Creates multiple Excel sheets by relevance score
- High relevance (70%+), Medium (50-69%), Low (<50%)
- Detailed analysis columns for each company

## 🛠️ Quick Start

### Prerequisites
```bash
pip install pandas google-generativeai tqdm openpyxl
```

### Setup Your API Keys
```python
api_keys = [
    "YOUR_GEMINI_API_KEY_1",
    "YOUR_GEMINI_API_KEY_2", 
    "YOUR_GEMINI_API_KEY_3",
    "YOUR_GEMINI_API_KEY_4"
]
```

### Input File Format
Your Excel file (`BD_Oil2.xlsx`) needs:
- **Company Name** column
- **Business Description** column

### Run the Analysis
```bash
python business_classification.py
```

## 📊 What You Get

### Generated Columns
- **Business Summary**: Clear 1-2 sentence explanation
- **Industry Classification**: Primary sector/industry
- **Business Model**: How they make money
- **Key Products/Services**: What they actually sell
- **Market Focus**: Geographic/segment focus
- **Relevance Score**: 0-100% match to your target
- **Relevance Reason**: Why this score makes sense

### Output Sheets
- **All_Companies**: Complete results sorted by relevance
- **High_Relevance_70+**: Your top prospects
- **Medium_Relevance_50-69**: Worth a second look
- **Low_Relevance_Below_50**: Probably not relevant

## 🎯 Target Company Configuration

Currently set for **Gabriel India Limited** (automotive components). To change:

```python
target_bd = """Your target company description here..."""
```

The AI will compare all companies against this reference.

## ⚙️ Configuration Options

```python
batch_size = 3              # Companies per API call
KEY_USAGE_LIMIT = 15        # Requests per key before rotation
input_file = "BD_Oil2.xlsx" # Your input file
output_file = "business_classifications.xlsx"
```

## 🔄 How It Works

1. **Loads and validates** your Excel data
2. **Processes in batches** of 3 companies at a time
3. **Sends structured prompts** to Gemini AI
4. **Parses JSON responses** into clean data
5. **Handles errors** with automatic retries
6. **Rotates API keys** to avoid rate limits
7. **Saves organized results** to Excel with multiple sheets

## 🛡️ Error Handling

- **API Failures**: 3 retry attempts with delays
- **JSON Parsing**: Multiple extraction methods
- **Rate Limits**: Automatic key rotation
- **Data Validation**: Ensures clean relevance scores
- **Progress Saves**: Intermediate backups every 5 batches

## 📈 Performance Stats

- **Speed**: ~3 companies per API call
- **Reliability**: Built-in retry and failover logic
- **Memory**: Efficient batch processing
- **Monitoring**: Real-time progress tracking

## 🔍 Sample Output

```
Company: TechCorp Solutions
Business Summary: Provides cloud-based inventory management software for retail businesses
Industry: Software/Technology
Relevance Score: 15.50%
Relevance Reason: Different industry focus (software vs automotive components) with no overlap in target markets
```

## 🚨 Important Notes

- **API Keys**: Keep your Gemini API keys secure
- **Rate Limits**: Tool handles this automatically
- **Data Privacy**: Review company data handling policies
- **Accuracy**: AI results should be validated for critical decisions
- **Costs**: Monitor your Google Cloud API usage

## 🔧 Troubleshooting

### Common Issues
| Problem | Solution |
|---------|----------|
| API Key Error | Verify keys are active in Google AI Studio |
| File Not Found | Ensure `BD_Oil2.xlsx` is in script directory |
| Column Missing | Check for "Company Name" and "Business Description" columns |
| JSON Parse Error | Usually resolves with retry, check for special characters |

### Error Messages
- `❌ Failed to initialize`: Check API key validity
- `⚠️ Expected X, got Y`: Partial API response (will retry)
- `❌ JSON parsing error`: Response format issue (will retry)

## 📊 Output Statistics

The tool provides detailed stats:
```
📋 Summary:
   • Total companies processed: 150
   • High Relevance (70+): 12 companies
   • Medium Relevance (50-69): 28 companies  
   • Low Relevance (<50): 110 companies
   • Overall average score: 34.56
```

## 🔄 Version Notes

- **Current**: Enhanced error handling and organized output
- **Features**: Batch processing, multi-key support, progress saves
- **Reliability**: Production-ready with comprehensive error handling

---

*This tool transforms raw business data into actionable intelligence. Perfect for market research, partnership discovery, and competitive analysis.*
