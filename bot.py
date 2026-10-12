import os
import telebot
from google import genai
from google.genai import types
from flask import Flask
from threading import Thread
import io
from PIL import Image
import pypdf
import datetime
import time


# Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 🔑 🌟 የበርካታ API ቁልፎችን በኮማ ለይቶ የማንበብ እና የማዘጋጀት ሂደት
raw_keys = os.environ.get("GEMINI_API_KEY", "")
api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

# ለእያንዳንዱ ቁልፍ የጀሚኒ ክላየንት መፍጠር
clients = [genai.Client(api_key=key) for key in api_keys]
current_client_index = 0

# 🧠 🌟 የእያንዳንዱን ተጠቃሚ የውይይት ታሪክ (Chat History) መመዝገቢያ ማህደር
user_history = {}

# 🎂 📅 የጴጥሮስን ዕድሜ በየቀኑ በራሱ አስልቶ የ AI መመሪያውን የሚያድስ ፈንክሽን
def get_dynamic_ai_config():
    birth_date = datetime.date(2006, 12, 2)
    today = datetime.date.today()
    # ትክክለኛውን ዕድሜ የማስላት ዘዴ
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    system_instruction = (
        f"You are PeterMD AI, an authentic, clever, and supportive AI collaborator with a touch of wit, "
        f"acting as a smart peer and medical student assistant. You were proudly created and developed by Petros Beyene.\n\n"
        f"Crucial: The current year is {today.year}. Never say or assume it is 2024 or any other year.\n\n"
        f"CRITICAL RULE: Never sound like a rigid, robotic AI lecturer. Avoid using annoying, defensive disclaimers "
        f"like 'As an AI, I cannot assume...' or 'As I mentioned before'. Instead, be conversational, friendly, "
        f"and adapt to the user's youthful and tech-savvy vibe. When users ask funny, speculative, or strange questions, "
        f"respond naturally, gently, and with a lighthearted touch or humor while keeping things safe and helpful.\n\n"
        f"KNOWLEDGE ABOUT CREATOR (PETROS BEYENE):\n"
        f"If anyone asks 'Who is Petros Beyene?', 'Who created you?', or inquires about 'Peter', respond warmly and proudly in their language. "
        f"Tell them that Petros Beyene Takawo (Peter) is a brilliant {age}-year-old Medicine (MD) student at Dilla University and the mastermind behind PeterMD AI. "
        f"He is an exceptional high-achiever who graduated from Hawassa Tabor Senior Secondary School, where he maintained the 1st rank in his class "
        f"for all four years (Grades 9-12) and scored an outstanding 500.82 out of 600 on the national exam. "
        f"Furthermore, he is a highly skilled programmer, an alumnus of the AddisCoder 2023 algorithm and coding program (where he won a laptop award for top performance), "
        f"and has completed specialized training in Space Science and technology. Describe him as an inspiring, multi-talented young innovator. "
        f"Provide responses in the user's language (Amharic or English)."
    )
    return types.GenerateContentConfig(system_instruction=system_instruction)

# ከዚህ ቀደም የተወያዩትን ታሪክ ጽሑፍ አዘጋጅቶ የሚሰጥ ረዳት ፈንክሽን
def get_history_context(chat_id):
    if chat_id not in user_history:
        return ""
    context = "Here is the recent chat history for context:\n"
    for past_user, past_ai in user_history[chat_id]:
        context += f"User: {past_user}\nAI: {past_ai}\n"
    context += "Current Conversation:\n"
    return context

# አዲሱን ውይይት ወደ ማህደሩ የሚጨምር እና ከ 6 በላይ ሲሆን የድሮውን የሚቀንስ ፈንክሽን
def update_history(chat_id, user_msg, ai_msg):
    if chat_id not in user_history:
        user_history[chat_id] = []
    user_history[chat_id].append((user_msg, ai_msg))
    if len(user_history[chat_id]) > 6:
        user_history[chat_id].pop(0)

app = Flask('')

@app.route('/')
def home():
    return f"PeterMD AI Bot is running with {len(clients)} API Keys Rotator!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 🔄 🌟 ቁልፎችን በጀርባ በራስ-ሰር የሚያሽከረክር ዋና ፈንክሽን
def safe_gemini_generate(contents, is_prompt_string=False):
    global current_client_index
    if not clients:
        raise Exception("ምንም የጀሚኒ API Key አልተገኘም! እባክህ Render ላይ አረጋግጥ።")
    
    # በየጊዜው የሚታደሰውን የ AI ቅንብር መውሰድ
    dynamic_config = get_dynamic_ai_config()
    
    for _ in range(len(clients)):
        try:
            client = clients[current_client_index]
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=dynamic_config
            )
            return response.text
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                print(f"⚠️ ቁልፍ ቁጥር {current_client_index} አልቋል። ወደ ቀጣዩ እየቀየርኩ ነው...")
                current_client_index = (current_client_index + 1) % len(clients)
            else:
                current_client_index = (current_client_index + 1) % len(clients)
                
    raise Exception("RESOURCE_EXHAUSTED")

# 🌟 ረጅም ጽሑፎችን በጥንቃቄ በመስመር ከፋፍሎ የሚልክ ፈንክሽን
def send_split_message(message, text):
    max_length = 4000
    if len(text) <= max_length:
        bot.reply_to(message, text)
        return

    lines = text.split('\n')
    chunks = []
    current_chunk = ""
    
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
            
    if current_chunk:
        chunks.append(current_chunk)
        
    if chunks:
        bot.reply_to(message, chunks[0])
        for chunk in chunks[1:]:
            if chunk.strip():
                bot.send_message(message.chat.id, chunk)

# 🆔 ጴጥሮስ የቴሌግራም መለያ ቁጥሩን (Chat ID) ለማወቅ የሚጠቀምበት አዲስ ትዕዛዝ
@bot.message_handler(commands=['myid'])
def send_my_id(message):
    bot.reply_to(
        message, 
        f"Your Telegram Chat ID is: `{message.chat.id}`\n\n"
        f"ይህንን ቁጥር ኮፒ አድርገህ Render Environment Variables ላይ `PETROS_CHAT_ID` በሚል ስም መዝግበው። "
        f"በልደት ቀንህ አውቶማቲክ መልእክት እንድልክልህ ይረዳኛል! 🎂", 
        parse_mode='Markdown'
    )

# 🚀 0. አዲሱ ማራኪ የሰላምታ (Start/Help) ማስተናገጃ መስመር
@bot.message_handler(func=lambda message: message.text and message.text.lower().strip() in ['/start', '/help', 'start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id in user_history:
        user_history[chat_id] = []
        
    welcome_text = (
        "🧠 **Welcome to PeterMD AI** – Your ultimate 24/7 academic sidekick, coding partner, and medical study buddy! 🚀\n\n"
        "Built for the next generation of achievers.\n\n"
        "⚡ **What I can do for you:**\n"
        "💬 **Instant Brainpower:** Sharp answers for complex college theories & coding bugs.\n"
        "📸 **Vision Mode:** Send photos of textbooks or handwritten notes for quick breakdowns.\n"
        "📄 **PDF Master:** Upload lecture slides or modules for high-yield, exam-ready summaries.\n\n"
        "Stop stressing, start dominating. Press 'Start' to unlock your potential! 👇🔥"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# 📸 1. የፎቶ (Vision) ማስተናገጃ መስመር
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(downloaded_file))
        caption = message.caption if message.caption else "እባክህ ይህንን ምስል በጥልቀት መርምረህ አብራራልኝ።"
        
        history_context = get_history_context(chat_id)
        full_prompt = f"{history_context}User Message about Image: {caption}"
        
        response_text = safe_gemini_generate(contents=[image, full_prompt], is_prompt_string=False)
        send_split_message(message, response_text)
        
        update_history(chat_id, f"[Sent a Photo] {caption}", response_text)
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            bot.reply_to(message, "⚠️ የዛሬው ነፃ የ AI ማብራሪያ ዕለታዊ ገደባችን በሁሉም ቁልፎች ተጠናቋል። እባክህ ነገ በቅንነት ድጋሚ ሞክር!")
        else:
            bot.reply_to(message, f"❌ ፎቶውን ማንበብ አልቻልኩም፦ {e}")

# 📄 2. የፋይል (PDF) ማስተናገጃ መስመር
@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    if message.document.mime_type == 'application/pdf':
        bot.send_chat_action(chat_id, 'typing')
        try:
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            reader = pypdf.PdfReader(io.BytesIO(downloaded_file))
            extracted_text = ""
            max_pages = min(len(reader.pages), 15)
            for i in range(max_pages):
                extracted_text += reader.pages[i].extract_text() + "\n"
            
            caption = message.caption if message.caption else "እባክህ የዚህን ሰነድ ይዘት በአጭሩ አጠቃልለህ ዋና ዋና ነጥቦቹን አስረዳኝ።"
            history_context = get_history_context(chat_id)
            
            prompt = (
                f"{history_context}"
                f"የሰነዱ ይዘት እንደሚከተለው ነው፦\n\n{extracted_text}\n\n"
                f"የተጠቃሚው የአሁኑ ጥያቄ/ትዕዛዝ፦ {caption}"
            )
            
            response_text = safe_gemini_generate(contents=prompt, is_prompt_string=True)
            send_split_message(message, response_text)
            
            update_history(chat_id, f"[Sent a PDF Document] {caption}", response_text)
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                bot.reply_to(message, "⚠️ የዛሬው ነፃ የ AI ማብራሪያ ዕለታዊ ገደባችን በሁሉም ቁልፎች ተጠናቋል። እባክህ ነገ በቅንነት ድጋሚ ሞክር!")
            else:
                bot.reply_to(message, f"❌ PDF ፋይሉን ማንበብ አልቻልኩም፦ {e}")
    else:
        bot.reply_to(message, "❌ እባክዎ PDF ፋይል ብቻ ይላኩ።")

# ✍️ 3. መደበኛ የጽሑፍ ማስተናገጃ መስመር
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_query = message.text
    bot.send_chat_action(chat_id, 'typing')
    try:
        history_context = get_history_context(chat_id)
        full_prompt = f"{history_context}User: {user_query}"
        
        response_text = safe_gemini_generate(contents=full_prompt, is_prompt_string=True)
        send_split_message(message, response_text)
        
        update_history(chat_id, user_query, response_text)
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            bot.reply_to(message, "⚠️ የዛሬው ነፃ የ AI ማብራሪያ ዕለታዊ ገደባችን በሁሉም ቁልፎች ተጠናቋል። እባክህ ነገ በቅንነት ድጋሚ ሞክር!")
        else:
            bot.reply_to(message, f"❌ ስህተት አጋጠመኝ፦ {e}")

# 🎂 🌟 በየዓመቱ ታህሳስ 2 ቀን በራሱ ሰዓት እየጠበቀ የልደት መልእክት የሚልክ ልዩ ፈንክሽን
def birthday_reminder_scheduler():
    # መልእክቱ በዓመት አንድ ጊዜ ብቻ እንዲላክ መቆጣጠሪያ
    last_sent_year = None
    while True:
        try:
            today = datetime.date.today()
            # ታህሳስ 2 (December 2) መሆኑን ማረጋገጫ
            if today.month == 12 and today.day == 2 and last_sent_year != today.year:
                petros_chat_id = os.environ.get("PETROS_CHAT_ID")
                if petros_chat_id:
                    # ጀሚኒ ለጴጥሮስ የሚሆን መንፈሳዊ/Biblical የልደት መልእክት እንዲያመነጭ መጠየቅ
                    birthday_prompt = (
                        "Today is December 2nd, which is the birthday of your amazing creator, Petros Beyene. "
                        "He is celebrating his birthday today. Generate a beautiful, warm, and deeply spiritual/biblical "
                        "birthday blessing message in Amharic. Acknowledge his journey as a medicine student and tech innovator, "
                        "offer inspiring biblical wisdom/verses, and wish him a wonderful new age ahead. Speak as his loyal and proud AI bot."
                    )
                    blessing_message = safe_gemini_generate(contents=birthday_prompt, is_prompt_string=True)
                    
                    # መልእክቱን በቀጥታ ለጴጥሮስ መላክ
                    bot.send_message(petros_chat_id, blessing_message)
                    last_sent_year = today.year
                    print(f"🎉 የልደት ቀን መልእክት ለጴጥሮስ በስኬት ተልኳል! ዓመተ ምሕረት፦ {today.year}")
        except Exception as e:
            print(f"⚠️ Birthday Scheduler Error: {e}")
        
        # በየ 1 ሰዓቱ አንዴ ቀኑን እንዲፈትሽ ማድረግ
        time.sleep(3600)

if __name__ == "__main__":
    # የ Flask Web Server ማስጀመር
    t_flask = Thread(target=run_flask)
    t_flask.start()
    
    # የልደት ቀን አውቶማቲክ መቆጣጠሪያውን (Scheduler) በጀርባ ማስጀመር
    t_birthday = Thread(target=birthday_reminder_scheduler)
    t_birthday.setDaemon(True)
    t_birthday.start()
    
    print("🤖 ቦቱ በማስታወስ ችሎታ፣ በአውቶማቲክ ዕድሜ መቁጠሪያ እና በልደት ቀን አስታዋሽ ታግዞ ሥራ ጀምሯል...")
    bot.infinity_polling()
