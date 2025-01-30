import os
import io
import docx
import time
import PyPDF2
import asyncio
import logging
import PIL.Image
from datetime import datetime
from textblob import TextBlob
from pymongo import MongoClient
from serpapi import GoogleSearch
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve values from .env
MONGO_URI = os.getenv("MONGO_URI")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
SERP_API_KEY = os.getenv("SERP_API_KEY")


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pyrogram Client
app = Client(
    "gemini_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.MARKDOWN
)

# Check Google API Key
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY is missing! Please check your config.")
    exit(1)

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# MongoDB Connection
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

# Verify MongoDB connection
try:
    client.admin.command('ping')
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    exit(1)

# Database and collections
db = client["telegram_bot"]
users_collection = db["users"]
chat_history_collection = db["chat_history"]
file_metadata_collection = db["file_metadata"]
websearch_history_collection = db["websearch_history"]
sentiment_history = db["sentiment_history"]

#BotCommands
HELP_TEXT = """
🤖 **Bot Commands:**  

🚀 **/start** - Start the bot and register yourself.  
💬 **/text <prompt>** - Generate AI-powered responses for any query.  
🖼 **/img** - Analyze and describe images using AI.  
📄 **/file** - Upload a document to get a summarized version.  
📊 **/sentiment <text>** – Analyze the sentiment of the given text.  
🌍 **/websearch <query>** - Search the web and get top results instantly.  
ℹ️ **/help** - View this command list anytime. 
"""

def append_help(func):
    async def wrapper(client: Client, message: Message):
        await func(client, message)
        await message.reply_text(HELP_TEXT)
    return wrapper

def get_sentiment(text):
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity

    if polarity > 0:
        return "positive"
    elif polarity < 0:
        return "negative"
    else:
        return "neutral"

# Command Handler for /help
@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply_text(HELP_TEXT)
    
@app.on_message(filters.command("start"))
@append_help
async def start_handler(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        user_data = users_collection.find_one({"chat_id": user_id})

        if not user_data:
            users_collection.insert_one({
                "chat_id": user_id,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "username": message.from_user.username,
                "phone_number": None
            })

            keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton("Share Phone Number", request_contact=True)]],
                resize_keyboard=True
            )

            await message.reply_text("Welcome! Please share your phone number.", reply_markup=keyboard)
        else:
            await message.reply_text("Welcome back!")

    except Exception as e:
        logger.error(f"Error in start_handler: {e}")

@app.on_message(filters.contact)
async def save_phone_number(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        contact_number = message.contact.phone_number

        users_collection.update_one({"chat_id": user_id}, {"$set": {"phone_number": contact_number}})
        await message.reply_text("✅ Your phone number has been saved successfully!")

    except Exception as e:
        logger.error(f"Error in save_phone_number: {e}")
        
        
@app.on_message(filters.command("text"))
@append_help
async def gemi_handler(client: Client, message: Message):
    loading_message = await message.reply_text("**Generating response, please wait...**")

    try:
        if len(message.text.strip()) <= 5:
            await message.reply_text("**Provide a prompt after the command.**")
            return

        prompt = message.text.split(maxsplit=1)[1]
        response = model.generate_content(prompt)

        response_text = response.text
        
        # Perform sentiment analysis
        sentiment = get_sentiment(prompt)

        # Store in MongoDB
        chat_history_collection.insert_one({
            "chat_id": message.from_user.id,
            "user_query": prompt,
            "bot_response": response_text,
            "sentiment": sentiment,
            "timestamp": datetime.utcnow()
        })
        
        # Adjust the response based on sentiment
        sentiment_responses = {
            "positive": "😊 Great! Here’s what I came up with::",
            "negative": "😞 I sense that things might be tough. Here's something that might help:",
            "neutral": "🤔 Here’s the information you requested:"
        }
        response_text = f"{sentiment_responses.get(sentiment, '')}\n\n{response_text}"

        # Send response
        await message.reply_text(response_text if len(response_text) <= 4000 else response_text[:4000] + "...")

    except Exception as e:
        await message.reply_text(f"**An error occurred: {str(e)}**")
    finally:
        await loading_message.delete()


@app.on_message(filters.command("img") & filters.photo)
@append_help
async def analyze_image(client: Client, message: Message):
    processing_message = await message.reply_text("🖼 **Analyzing image, please wait...**")

    try:
        img_data = await client.download_media(message.photo, in_memory=True)
        img = PIL.Image.open(io.BytesIO(img_data.getbuffer()))

        prompt = message.caption or "Describe this image."
        response = model.generate_content([prompt, img])
        response_text = response.text

        # Store metadata in MongoDB
        file_metadata_collection.insert_one({
            "chat_id": message.from_user.id,
            "file_name": "photo.jpg",
            "file_type": "image",
            "description": response_text,
            "timestamp": datetime.utcnow()
        })

        await message.reply_text(f"🖼 **Image Analysis:**\n{response_text}")

    except Exception as e:
        await message.reply_text(f"❌ Error analyzing image: {str(e)}")
    finally:
        await processing_message.delete()
        

@app.on_message(filters.command("file") & filters.document)
@append_help
async def analyze_file(client: Client, message: Message):
    processing_message = await message.reply_text("📂 **Analyzing file, please wait...**")

    try:
        file = message.document
        file_name = file.file_name
        file_type = file.mime_type
        
        # Check if there's a text prompt or use the default file content
        prompt = message.caption if message.caption else "Summarize the contents of this file."

        # Download file
        file_data = await client.download_media(file, in_memory=True)
        
        # Initialize extracted_text to an empty string
        extracted_text = ""

        # Extract text if it's a PDF
        if file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data.getbuffer()))
            extracted_text = " ".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

        elif file_type == "text/plain":  # TXT Files
            extracted_text = file_data.getvalue().decode("utf-8")

        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:  # DOCX Files
            doc = docx.Document(io.BytesIO(file_data.getbuffer()))
            extracted_text = "\n".join([para.text for para in doc.paragraphs])

        else:
            extracted_text = "⚠️ Unsupported file format. Only PDF, TXT, and DOCX are supported."

        # Ensure extracted_text is not empty
        if not extracted_text.strip():
            extracted_text = "⚠️ No readable text found in this file."

        response = model.generate_content(f"{prompt}\n\n{extracted_text[:4000]}")  # Use extracted_text
        response_text = response.text

        # Store metadata in MongoDB
        file_metadata_collection.insert_one({
            "chat_id": message.from_user.id,
            "file_name": file_name,
            "file_type": file_type,
            "description": response_text,
            "timestamp": datetime.utcnow()
        })

        await message.reply_text(f"📂 **File Analysis:**\n{response_text[:4000]}") 

    except Exception as e:
        await message.reply_text(f"❌ Error analyzing file: {str(e)}")
    finally:
        await processing_message.delete()
        
@app.on_message(filters.command("sentiment"))
@append_help
async def sentiment_handler(client: Client, message: Message):
    # Check if the user provided text after the command
    if len(message.text.split()) < 2:
        await message.reply_text("🔍 **Usage:** /sentiment <text>")
        return

    # Extract the text from the message
    text = message.text.split(maxsplit=1)[1]

    # Perform sentiment analysis using TextBlob
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity

    if sentiment > 0:
        sentiment_result = "😊 Positive"
    elif sentiment < 0:
        sentiment_result = "😞 Negative"
    else:
        sentiment_result = "😐 Neutral"
        
    # Store in MongoDB
    sentiment_history.insert_one({
        "chat_id": message.from_user.id,
        "user_query": text,
        "sentiment": sentiment_result,
        "timestamp": datetime.utcnow()
    })

    # Reply with sentiment result
    await message.reply_text(f"📊 **Sentiment Analysis:**\n{text}\n\nResult: {sentiment_result}")


@app.on_message(filters.command("websearch"))
@append_help
async def web_search(client: Client, message: Message):
    
    
    if len(message.text.split()) < 2:
        await message.reply_text("🔍 **Usage:** /websearch your_query")
        return

    query = message.text.split(maxsplit=1)[1]
    loading_msg = await message.reply_text("🔎 Searching the web...")
    
    # Perform sentiment analysis on query
    sentiment = get_sentiment(query)

    try:
        # Initialize the SERP API client
        search = GoogleSearch({"q": query, "api_key": SERP_API_KEY})
        
        # Perform the search
        results = search.get_dict().get("organic_results", [])[:3]  # Get top 3 results
        
        if not results:
            await message.reply_text("❌ No results found.")
            return
        
        # Construct the response text with titles and links
        response_text = "\n".join([f"🔹 [{r['title']}]({r['link']})\n{r['snippet']}" for r in results])

        # Generate the summary using Gemini AI
        summary_prompt = "Summarize the following web search results:\n" + response_text
        ai_summary = model.generate_content([summary_prompt])
        summary_text = ai_summary.text.strip()

        # Send the search results and AI-generated summary to the user
        response = f"🌍 **Top Search Results:**\n\n{response_text}\n\n**Gemini AI Summary:**\n{summary_text}"
        
        websearch_history_collection.insert_one({
            "chat_id": message.from_user.id,
            "user_query": query,
            "bot_response": response,
            "sentiment": sentiment,
            "timestamp": datetime.utcnow()
        })
        
        sentiment_responses = {
            "positive": "🌟 Great! Here are some useful links:",
            "negative": "😟 It seems like you have concerns. These results might help:",
            "neutral": "🔍 Here are the search results you requested:"
        }
        response = f"{sentiment_responses.get(sentiment, '')}\n\n{response_text}\n\n**Gemini AI Summary:**\n{summary_text}"
        
        await message.reply_text(response)

    except Exception as e:
        # Handle errors (e.g., API issues)
        await message.reply_text(f"⚠️ Error: {str(e)}")
    
    finally:
        # Delete the loading message after processing
        await loading_msg.delete()


# Run the bot
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5040))
    logger.info("Starting the bot...")
    app.run()
