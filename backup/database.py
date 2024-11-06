import sqlite3
import streamlit as st
from datetime import datetime

def get_database_connection():
    """Create and return a database connection"""
    return sqlite3.connect('ecoeats.db', check_same_thread=False)

@st.cache_resource
def setup_database():
    """Initialize database tables"""
    conn = get_database_connection()
    c = conn.cursor()
    
    c.executescript('''
        CREATE TABLE IF NOT EXISTS food_waste
            (id INTEGER PRIMARY KEY, item TEXT, quantity INTEGER, quantity_type TEXT, date TEXT, image BLOB);
        CREATE TABLE IF NOT EXISTS meals
            (id INTEGER PRIMARY KEY, meal TEXT, nutrition TEXT, date TEXT, image BLOB, quantity INTEGER);
        CREATE TABLE IF NOT EXISTS goals
            (id INTEGER PRIMARY KEY, type TEXT, goal TEXT, recommendations TEXT, date TEXT, completed BOOLEAN, potential_savings TEXT);
        CREATE TABLE IF NOT EXISTS challenges
            (id INTEGER PRIMARY KEY, challenge TEXT, start_date TEXT, end_date TEXT, completed BOOLEAN);
        CREATE TABLE IF NOT EXISTS community_posts
            (id INTEGER PRIMARY KEY, post TEXT, likes INTEGER, date TEXT);
        CREATE TABLE IF NOT EXISTS user_stats
            (id INTEGER PRIMARY KEY, last_login TEXT, streak INTEGER);
    ''')
    conn.commit()
    return conn

def update_streak(conn):
    """Update user streak in database"""
    c = conn.cursor()
    today = datetime.now().date()
    
    c.execute("SELECT last_login, streak FROM user_stats WHERE id=1")
    result = c.fetchone()
    
    if result:
        last_login, streak = result
        last_login = datetime.strptime(last_login, "%Y-%m-%d").date()
        if (today - last_login).days == 1:
            streak += 1
        elif (today - last_login).days > 1:
            streak = 1
        else:
            return streak
    else:
        streak = 1
    
    c.execute("INSERT OR REPLACE INTO user_stats (id, last_login, streak) VALUES (1, ?, ?)", 
              (today.strftime("%Y-%m-%d"), streak))
    conn.commit()
    return streak

def get_achievement(streak):
    """Return achievement based on streak length"""
    achievements = [
        (30, "🏆 Eco Warrior"),
        (20, "🌟 Sustainability Star"),
        (10, "🌱 Green Enthusiast"),
        (5, "🍃 Eco Novice"),
        (0, "🌾 Beginner")
    ]
    for days, title in achievements:
        if streak >= days:
            return title
    return "🌾 Beginner"