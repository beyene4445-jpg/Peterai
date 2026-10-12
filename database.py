import sqlite3
import os

def init_db():
    conn = sqlite3.connect('peter_quiz_bot.db')
    cursor = conn.cursor()
    
    # የጥያቄዎች ማከማቻ ቴብል
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL
        )
    ''')
    
    # የተማሪዎች መረጃ ማከማቻ ቴብል
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            status TEXT DEFAULT 'FREE',
            score INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database Tables Created Successfully!")
    
    # ጥያቄዎችን ከ Text ፋይል ላይ ማንበቢያ ፈንክሽን
    seed_questions_from_txt()

def seed_questions_from_txt():
    if not os.path.exists('questions.txt'):
        print("questions.txt file not found. Skipping.")
        return
        
    conn = sqlite3.connect('peter_quiz_bot.db')
    cursor = conn.cursor()
    
    # ዳታቤዙ ውስጥ ጥያቄ አስቀድሞ መኖሩን ማረጋገጥ
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] > 0:
        print("Questions already exist. Skipping txt loading.")
        conn.close()
        return

    print("Loading questions from questions.txt...")
    with open('questions.txt', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # ጥያቄዎቹን በ '===' መለየት
    blocks = content.split('===')
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        q_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'subject': q_data['subject'] = value
                elif key == 'chapter': q_data['chapter'] = int(value)
                elif key == 'question': q_data['question'] = value
                elif key == 'a': q_data['a'] = value
                elif key == 'b': q_data['b'] = value
                elif key == 'c': q_data['c'] = value
                elif key == 'd': q_data['d'] = value
                elif key == 'answer': q_data['answer'] = value.upper()
        
        # ሁሉም 8ቱ መረጃዎች መሟላታቸውን ቼክ ማድረግ
        if len(q_data) == 8:
            cursor.execute('''
                INSERT INTO questions (subject, chapter, question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                q_data['subject'], 
                q_data['chapter'], 
                q_data['question'], 
                q_data['a'], 
                q_data['b'], 
                q_data['c'], 
                q_data['d'], 
                q_data['answer']
            ))
            
    conn.commit()
    conn.close()
    print("Successfully loaded all questions from TXT file!")

if __name__ == '__main__':
    init_db()
