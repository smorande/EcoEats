import streamlit as st
import openai
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sqlite3
import bcrypt

# Load environment variables
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database setup
conn = sqlite3.connect('ecoeats.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS food_waste
             (id INTEGER PRIMARY KEY, user_id INTEGER, item TEXT, quantity INTEGER, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS meals
             (id INTEGER PRIMARY KEY, user_id INTEGER, meal TEXT, nutrition TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS goals
             (id INTEGER PRIMARY KEY, user_id INTEGER, type TEXT, goal TEXT, recommendations TEXT, date TEXT, completed BOOLEAN)''')
c.execute('''CREATE TABLE IF NOT EXISTS challenges
             (id INTEGER PRIMARY KEY, user_id INTEGER, challenge TEXT, start_date TEXT, end_date TEXT, completed BOOLEAN)''')
c.execute('''CREATE TABLE IF NOT EXISTS community_posts
             (id INTEGER PRIMARY KEY, user_id INTEGER, post TEXT, likes INTEGER, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_stats
             (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, last_login TEXT, streak INTEGER)''')
conn.commit()

# Helper functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def create_user(username, password):
    hashed_password = hash_password(password)
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()

def get_user(username):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    return c.fetchone()

# AI Utility Functions
def generate_ai_response(prompt, max_tokens=150):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for an eco-friendly food tracking app."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        st.error(f"Error in AI response generation: {str(e)}")
        return "I'm sorry, I couldn't generate a response at this time."

# Gamification Functions
def update_streak(user_id):
    today = datetime.now().date()
    c.execute("SELECT last_login, streak FROM user_stats WHERE user_id=?", (user_id,))
    result = c.fetchone()
    if result:
        last_login, streak = result
        last_login = datetime.strptime(last_login, "%Y-%m-%d").date()
        if (today - last_login).days == 1:
            streak += 1
        elif (today - last_login).days > 1:
            streak = 1
        else:
            # User has already logged in today, don't update the streak
            return streak
    else:
        # First time user, initialize streak
        streak = 1
    
    c.execute("INSERT OR REPLACE INTO user_stats (user_id, last_login, streak) VALUES (?, ?, ?)", 
              (user_id, today.strftime("%Y-%m-%d"), streak))
    conn.commit()
    return streak

def get_achievement(streak):
    if streak >= 30:
        return "🏆 Eco Warrior"
    elif streak >= 20:
        return "🌟 Sustainability Star"
    elif streak >= 10:
        return "🌱 Green Enthusiast"
    elif streak >= 5:
        return "🍃 Eco Novice"
    else:
        return "🌾 Beginner"

# App Components
def food_waste_notification(user_id):
    st.subheader("🗑️ Food Waste Notifications")
    
    notification = generate_ai_response("Generate a short, engaging notification about reducing food waste.")
    st.info(notification)
    
    waste_item = st.text_input("Log wasted food item:")
    quantity = st.number_input("Quantity (in grams):", min_value=0, step=10)
    
    if st.button("Log Waste"):
        c.execute("INSERT INTO food_waste (user_id, item, quantity, date) VALUES (?, ?, ?, ?)", 
                  (user_id, waste_item, quantity, datetime.now().isoformat()))
        conn.commit()
        st.success(f"Logged: {quantity}g of {waste_item}")
    
    c.execute("SELECT * FROM food_waste WHERE user_id=? ORDER BY date DESC LIMIT 5", (user_id,))
    waste_data = c.fetchall()
    if waste_data:
        st.subheader("Recent Food Waste")
        waste_df = pd.DataFrame(waste_data, columns=['id', 'user_id', 'item', 'quantity', 'date'])
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        
        chart = alt.Chart(waste_df).mark_bar().encode(
            x='date:T',
            y='quantity:Q',
            color='item:N',
            tooltip=['date', 'item', 'quantity']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

def healthy_eating_tracker(user_id):
    st.subheader("🥗 Healthy Eating Tracker")
    
    meal = st.text_input("Describe your meal:")
    
    if st.button("Log Meal"):
        nutrition_info = generate_ai_response(f"Provide a brief, engaging nutritional summary for this meal: {meal}")
        c.execute("INSERT INTO meals (user_id, meal, nutrition, date) VALUES (?, ?, ?, ?)", 
                  (user_id, meal, nutrition_info, datetime.now().isoformat()))
        conn.commit()
        st.success("Meal logged successfully!")
        st.write(nutrition_info)
    
    c.execute("SELECT * FROM meals WHERE user_id=? ORDER BY date DESC LIMIT 5", (user_id,))
    meals_data = c.fetchall()
    if meals_data:
        st.subheader("Recent Meals")
        for meal in meals_data:
            with st.expander(f"{meal[4]} - {meal[2]}"):
                st.write(meal[3])

def weekly_report(user_id):
    st.subheader("📊 Weekly Progress Report")
    
    # Food Waste Chart
    c.execute("SELECT date, SUM(quantity) FROM food_waste WHERE user_id=? AND date > ? GROUP BY date", 
              (user_id, (datetime.now() - timedelta(days=7)).isoformat()))
    waste_data = c.fetchall()
    if waste_data:
        waste_df = pd.DataFrame(waste_data, columns=['date', 'quantity'])
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        
        waste_chart = alt.Chart(waste_df).mark_area().encode(
            x='date:T',
            y='quantity:Q',
            tooltip=['date', 'quantity']
        ).properties(title="Food Waste This Week")
        st.altair_chart(waste_chart, use_container_width=True)
    
    # Meals Chart
    c.execute("SELECT date, COUNT(*) FROM meals WHERE user_id=? AND date > ? GROUP BY date", 
              (user_id, (datetime.now() - timedelta(days=7)).isoformat()))
    meals_data = c.fetchall()
    if meals_data:
        meals_df = pd.DataFrame(meals_data, columns=['date', 'count'])
        meals_df['date'] = pd.to_datetime(meals_df['date'])
        
        meals_chart = alt.Chart(meals_df).mark_line().encode(
            x='date:T',
            y='count:Q',
            tooltip=['date', 'count']
        ).properties(title="Meals Logged This Week")
        st.altair_chart(meals_chart, use_container_width=True)
    
    summary = generate_ai_response("Generate a brief, encouraging summary of progress in reducing food waste and eating healthy based on the charts.")
    st.info(summary)

def sustainability_tips(user_id):
    st.subheader("🌱 Sustainability Tips & Challenges")
    
    tip = generate_ai_response("Provide an engaging tip for reducing food waste and eating more sustainably.")
    st.info(tip)
    
    st.subheader("Weekly Challenge")
    c.execute("SELECT * FROM challenges WHERE user_id=? ORDER BY end_date DESC LIMIT 1", (user_id,))
    current_challenge = c.fetchone()
    
    if not current_challenge or datetime.strptime(current_challenge[4], "%Y-%m-%d").date() < datetime.now().date():
        new_challenge = generate_ai_response("Create a week-long challenge related to reducing food waste or eating more sustainably.")
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=7)
        c.execute("INSERT INTO challenges (user_id, challenge, start_date, end_date, completed) VALUES (?, ?, ?, ?, ?)", 
                  (user_id, new_challenge, start_date.isoformat(), end_date.isoformat(), False))
        conn.commit()
        current_challenge = (None, user_id, new_challenge, start_date.isoformat(), end_date.isoformat(), False)
    
    st.write(f"**Challenge:** {current_challenge[2]}")
    st.write(f"**Start Date:** {current_challenge[3]}")
    st.write(f"**End Date:** {current_challenge[4]}")
    
    if not current_challenge[5]:
        if st.button("Mark as Completed"):
            c.execute("UPDATE challenges SET completed = ? WHERE id = ?", (True, current_challenge[0]))
            conn.commit()
            st.success("Congratulations on completing the challenge!")
            st.balloons()
    else:
        st.success("Challenge completed! Great job!")

def goal_setting(user_id):
    st.subheader("🎯 Custom Goals")
    
    goal_type = st.selectbox("Goal Type", ["Food Waste Reduction", "Healthy Eating"])
    goal = st.text_input("Set your goal:")
    
    if st.button("Set Goal"):
        recommendations = generate_ai_response(f"Provide personalized recommendations for achieving this {goal_type} goal: {goal}")
        c.execute("INSERT INTO goals (user_id, type, goal, recommendations, date, completed) VALUES (?, ?, ?, ?, ?, ?)", 
                  (user_id, goal_type, goal, recommendations, datetime.now().isoformat(), False))
        conn.commit()
        st.success("Goal set successfully!")
        st.write("Personalized Recommendations:")
        st.info(recommendations)
    
    c.execute("SELECT * FROM goals WHERE user_id=? ORDER BY date DESC", (user_id,))
    goals_data = c.fetchall()
    if goals_data:
        st.subheader("Your Goals")
        for goal in goals_data:
            with st.expander(f"{goal[2]}: {goal[3]}"):
                st.write(f"Set on: {goal[5]}")
                st.write(f"Recommendations: {goal[4]}")
                if not goal[6]:
                    if st.button(f"Mark as Completed", key=f"complete_goal_{goal[0]}"):
                        c.execute("UPDATE goals SET completed = ? WHERE id = ?", (True, goal[0]))
                        conn.commit()
                        st.success("Goal marked as completed!")
                        st.balloons()
                else:
                    st.success("Goal completed!")

def community_section(user_id):
    st.subheader("🌍 Community Hub")
    
    post = st.text_area("Share your thoughts, tips, or achievements:")
    if st.button("Submit Post"):
        c.execute("INSERT INTO community_posts (user_id, post, likes, date) VALUES (?, ?, ?, ?)", 
                  (user_id, post, 0, datetime.now().isoformat()))
        conn.commit()
        st.success("Post shared with the community!")
    
    c.execute("SELECT * FROM community_posts ORDER BY date DESC LIMIT 10")
    posts_data = c.fetchall()
    if posts_data:
        st.subheader("Community Feed")
        for post in posts_data:
            with st.expander(f"Post from {post[4]}"):
                st.write(post[2])
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(f"👍 {post[3]}", key=f"like_post_{post[0]}"):
                        c.execute("UPDATE community_posts SET likes = likes + 1 WHERE id = ?", (post[0],))
                        conn.commit()
                with col2:
                    st.write(f"Likes: {post[3]}")
    
    community_summary = generate_ai_response("Summarize recent community activity and provide an encouraging message for community engagement.")
    st.info(community_summary)

def login_page():
    st.title("🌿 EcoEats Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == "kanwal" and password == "swapnil87":
            # For demonstration purposes, we're using a hardcoded user ID.
            # In a real application, you'd retrieve this from the database.
            st.session_state.user_id = 1
            st.session_state.username = username
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.markdown("---")
    st.info("For demo purposes, use the following credentials:")
    st.info("Username: kanwal")
    st.info("Password: swapnil87")

def main():
    st.set_page_config(page_title="EcoEats Tracker", page_icon="🌿", layout="wide")
    
    # Custom CSS for a blue-colored dropdown in the sidebar
    st.markdown("""
        <style>
        .sidebar .sidebar-content {
            background-image: linear-gradient(#2193b0, #6dd5ed);
        }
        .sidebar .sidebar-content .block-container {
            padding-top: 0;
        }
        .stSelectbox > div > div {
            background-color: #2193b0;
            color: white;
        }
        .stSelectbox > div > div:hover {
            background-color: #1c7a94;
        }
        .stSelectbox [data-baseweb="select"] {
            border-color: #2193b0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if 'user_id' not in st.session_state:
        login_page()
    else:
        # Sidebar
        st.sidebar.title("🌿 EcoEats Navigation")
        st.sidebar.markdown("---")
        
        menu = ["Home", "Food Waste", "Healthy Eating", "Weekly Report", "Sustainability", "Goals", "Community"]
        
        # Create dropdown for navigation
        choice = st.sidebar.selectbox("Go to", menu)
        
        streak = update_streak(st.session_state.user_id)
        
        st.sidebar.markdown("---")
        st.sidebar.info(f"Current Streak: {streak} days")
        st.sidebar.info(f"Achievement: {get_achievement(streak)}")
        st.sidebar.info(f"Logged in as: {st.session_state.username}")
        if st.sidebar.button("Logout"):
            del st.session_state.user_id
            del st.session_state.username
            st.experimental_rerun()
        
        # Main content
        st.title("🌿 EcoEats: Food Waste Reduction & Healthy Eating Tracker")
        
        if choice == "Home":
            st.write(f"Welcome to EcoEats, {st.session_state.username}! Your personalized food waste reduction and healthy eating tracker.")
            st.write("Use the sidebar to navigate through different features of the app.")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("🗑️ Food Waste")
                c.execute("SELECT COUNT(*) FROM food_waste WHERE user_id=?", (st.session_state.user_id,))
                waste_count = c.fetchone()[0]
                st.metric("Items Logged", waste_count)
            with col2:
                st.subheader("🥗 Healthy Meals")
                c.execute("SELECT COUNT(*) FROM meals WHERE user_id=?", (st.session_state.user_id,))
                meal_count = c.fetchone()[0]
                st.metric("Meals Tracked", meal_count)
            with col3:
                st.subheader("🎯 Goals")
                c.execute("SELECT COUNT(*) FROM goals WHERE user_id=? AND completed=1", (st.session_state.user_id,))
                goal_count = c.fetchone()[0]
                st.metric("Goals Completed", goal_count)
            
            st.subheader("Quick Tips")
            quick_tip = generate_ai_response("Provide a quick, engaging tip for reducing food waste and eating healthier.")
            st.info(quick_tip)
            
            # Add a motivational quote
            quote = generate_ai_response("Generate a short, inspiring quote about sustainability or healthy eating.")
            st.markdown(f"### 💡 Thought of the Day\n\n{quote}")
            
        elif choice == "Food Waste":
            food_waste_notification(st.session_state.user_id)
        elif choice == "Healthy Eating":
            healthy_eating_tracker(st.session_state.user_id)
        elif choice == "Weekly Report":
            weekly_report(st.session_state.user_id)
        elif choice == "Sustainability":
            sustainability_tips(st.session_state.user_id)
        elif choice == "Goals":
            goal_setting(st.session_state.user_id)
        elif choice == "Community":
            community_section(st.session_state.user_id)

        # Add a footer
        st.markdown("---")
        st.markdown("Made with ❤️ by EcoEats Team")
        st.markdown("For support, contact us at support@ecoeats.com")

if __name__ == "__main__":
    main()