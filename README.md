# Gemini AI Telegram Bot

An AI-powered Telegram bot that leverages Google Gemini AI, MongoDB, and SERP API for generating text responses, sentiment analysis, image description, file summarization, and web searches. Additionally, the project includes a Power BI dashboard for visualizing collected data.

## Features
- AI-powered text generation
- Sentiment analysis
- Image description
- File summarization (PDF, TXT, DOCX)
- Web search integration with SERP API
- MongoDB database for storing user interactions
- Power BI dashboard for data visualization
  ![image](https://github.com/user-attachments/assets/369fa96f-f421-4cf9-9668-15ee681df7e7)

## Setup Guide

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/gemini-telegram-bot.git
cd gemini-telegram-bot
```

### 2. Configure `config.py`
Create a `config.py` file in the root directory and add the following credentials:

```python
# MongoDB URL
MONGO_URI = ""

# Program setup
API_ID = ""  # Replace this API ID with your actual API ID
API_HASH = ""  # Replace this API HASH with your actual API HASH
BOT_TOKEN = ""  # Replace this BOT_TOKEN

# Google API Key
GOOGLE_API_KEY = ""  # Replace this Google API Key
MODEL_NAME = "gemini-1.5-flash" # Don't Change this model

SERP_API_KEY = ""  # Replace this with your SERP API Key
```

### 3. Set Up a Virtual Environment
It's recommended to use a virtual environment to manage dependencies.

```bash
python -m venv venv  # Create a virtual environment
source venv/bin/activate  # Activate on macOS/Linux
venv\Scripts\activate  # Activate on Windows
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Bot
```bash
python bot.py
```

## Power BI Dashboard
A Power BI dashboard is available to visualize data collected from user interactions. The dashboard includes:
- User engagement metrics
- Sentiment analysis insights
- Web search trends
- Image and file analysis summaries
- File categories breakdown
- Chat activity over time

### Dashboard Highlights:
- **Total Users:** Displays the number of users who have interacted with the bot.
- **Total Files Uploaded:** Shows the number of files processed.
- **Total Prompts:** Indicates the total number of text and file prompts received.
- **Sentiment Analysis:** Pie chart depicting sentiment distribution in user queries.
- **File Categories:** Breakdown of different types of files uploaded (PDF, images, etc.).
- **Chats Over Time:** Line chart displaying user activity trends over time.

  ![image](https://github.com/user-attachments/assets/75a91d43-b829-415d-8ada-0d2f00b98b46)

To access the Power BI dashboard:
1. Open Power BI and import the dataset from MongoDB.
2. Use the provided Power BI template file (`powerbi_dashboard.pbix`) to visualize the collected data.
3. Analyze insights and improve bot interactions based on user engagement trends.

## Contributing
Feel free to contribute to this project by submitting issues, feature requests, or pull requests!

## License
This project is licensed under the MIT License.

