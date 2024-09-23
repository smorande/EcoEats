import streamlit as st
import openai
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sqlite3

# Load environment variables
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database setup
conn = sqlite3.connect('ecoeats.db')
c = conn.cursor()

# Create tables if they don't exist
def setup_database():
    c.executescript('''
        CREATE TABLE IF NOT EXISTS food_waste
            (id INTEGER PRIMARY KEY, item TEXT, quantity INTEGER, date TEXT);
        CREATE TABLE IF NOT EXISTS meals
            (id INTEGER PRIMARY KEY, meal TEXT, nutrition TEXT, date TEXT);
        CREATE TABLE IF NOT EXISTS goals
            (id INTEGER PRIMARY KEY, type TEXT, goal TEXT, recommendations TEXT, date TEXT, completed BOOLEAN);
        CREATE TABLE IF NOT EXISTS challenges
            (id INTEGER PRIMARY KEY, challenge TEXT, start_date TEXT, end_date TEXT, completed BOOLEAN);
        CREATE TABLE IF NOT EXISTS community_posts
            (id INTEGER PRIMARY KEY, post TEXT, likes INTEGER, date TEXT);
        CREATE TABLE IF NOT EXISTS user_stats
            (id INTEGER PRIMARY KEY, last_login TEXT, streak INTEGER);
    ''')
    conn.commit()

setup_database()

# AI Utility Functions
@st.cache_data(show_spinner=False)
def generate_ai_response(prompt, max_tokens=150):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
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
def update_streak():
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

# App Components
def food_waste_notification():
    st.subheader("🗑️ Food Waste Notifications")
    
    notification = generate_ai_response("Generate a short, engaging notification about reducing food waste.")
    st.info(notification)
    
    waste_item = st.text_input("Log wasted food item:")
    quantity = st.number_input("Quantity (in grams):", min_value=0, step=10)
    
    if st.button("Log Waste"):
        c.execute("INSERT INTO food_waste (item, quantity, date) VALUES (?, ?, ?)", 
                  (waste_item, quantity, datetime.now().isoformat()))
        conn.commit()
        st.success(f"Logged: {quantity}g of {waste_item}")
    
    display_waste_chart()

def display_waste_chart():
    c.execute("SELECT * FROM food_waste ORDER BY date DESC LIMIT 5")
    waste_data = c.fetchall()
    if waste_data:
        st.subheader("Recent Food Waste")
        # Get the column names from the cursor description
        columns = [description[0] for description in c.description]
        waste_df = pd.DataFrame(waste_data, columns=columns)
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        
        chart = alt.Chart(waste_df).mark_bar().encode(
            x='date:T',
            y='quantity:Q',
            color='item:N',
            tooltip=['date', 'item', 'quantity']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No food waste data available yet. Start logging to see your chart!")

def healthy_eating_tracker():
    st.subheader("🥗 Healthy Eating Tracker")
    
    meal = st.text_input("Describe your meal:")
    
    if st.button("Log Meal"):
        nutrition_info = generate_ai_response(f"Provide a brief, engaging nutritional summary for this meal: {meal}")
        c.execute("INSERT INTO meals (meal, nutrition, date) VALUES (?, ?, ?)", 
                  (meal, nutrition_info, datetime.now().isoformat()))
        conn.commit()
        st.success("Meal logged successfully!")
        st.write(nutrition_info)
    
    display_recent_meals()

def display_recent_meals():
    c.execute("SELECT * FROM meals ORDER BY date DESC LIMIT 5")
    meals_data = c.fetchall()
    if meals_data:
        st.subheader("Recent Meals")
        for meal in meals_data:
            with st.expander(f"{meal[3]} - {meal[1]}"):
                st.write(meal[2])

def weekly_report():
    st.subheader("📊 Weekly Progress Report")
    
    display_waste_trend()
    display_meals_trend()
    
    summary = generate_ai_response("Generate a brief, encouraging summary of progress in reducing food waste and eating healthy based on the charts.")
    st.info(summary)

def display_waste_trend():
    c.execute("SELECT date, SUM(quantity) FROM food_waste WHERE date > ? GROUP BY date", 
              ((datetime.now() - timedelta(days=7)).isoformat(),))
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

def display_meals_trend():
    c.execute("SELECT date, COUNT(*) FROM meals WHERE date > ? GROUP BY date", 
              ((datetime.now() - timedelta(days=7)).isoformat(),))
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

def sustainability_tips():
    st.subheader("🌱 Sustainability Tips & Challenges")
    
    tip = generate_ai_response("Provide an engaging tip for reducing food waste and eating more sustainably.")
    st.info(tip)
    
    display_weekly_challenge()

def display_weekly_challenge():
    st.subheader("Weekly Challenge")
    c.execute("SELECT * FROM challenges ORDER BY end_date DESC LIMIT 1")
    current_challenge = c.fetchone()
    
    if not current_challenge or datetime.strptime(current_challenge[3], "%Y-%m-%d").date() < datetime.now().date():
        new_challenge = generate_ai_response("Create a week-long challenge related to reducing food waste or eating more sustainably.")
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=7)
        c.execute("INSERT INTO challenges (challenge, start_date, end_date, completed) VALUES (?, ?, ?, ?)", 
                  (new_challenge, start_date.isoformat(), end_date.isoformat(), False))
        conn.commit()
        current_challenge = (None, new_challenge, start_date.isoformat(), end_date.isoformat(), False)
    
    st.write(f"**Challenge:** {current_challenge[1]}")
    st.write(f"**Start Date:** {current_challenge[2]}")
    st.write(f"**End Date:** {current_challenge[3]}")
    
    if not current_challenge[4]:
        if st.button("Mark as Completed"):
            c.execute("UPDATE challenges SET completed = ? WHERE id = ?", (True, current_challenge[0]))
            conn.commit()
            st.success("Congratulations on completing the challenge!")
            st.balloons()
    else:
        st.success("Challenge completed! Great job!")

def goal_setting():
    st.subheader("🎯 Custom Goals")
    
    goal_type = st.selectbox("Goal Type", ["Food Waste Reduction", "Healthy Eating"])
    goal = st.text_input("Set your goal:")
    
    if st.button("Set Goal"):
        recommendations = generate_ai_response(f"Provide personalized recommendations for achieving this {goal_type} goal: {goal}")
        c.execute("INSERT INTO goals (type, goal, recommendations, date, completed) VALUES (?, ?, ?, ?, ?)", 
                  (goal_type, goal, recommendations, datetime.now().isoformat(), False))
        conn.commit()
        st.success("Goal set successfully!")
        st.write("Personalized Recommendations:")
        st.info(recommendations)
    
    display_user_goals()

def display_user_goals():
    c.execute("SELECT * FROM goals ORDER BY date DESC")
    goals_data = c.fetchall()
    if goals_data:
        st.subheader("Your Goals")
        for goal in goals_data:
            with st.expander(f"{goal[1]}: {goal[2]}"):
                st.write(f"Set on: {goal[4]}")
                st.write(f"Recommendations: {goal[3]}")
                if not goal[5]:
                    if st.button(f"Mark as Completed", key=f"complete_goal_{goal[0]}"):
                        c.execute("UPDATE goals SET completed = ? WHERE id = ?", (True, goal[0]))
                        conn.commit()
                        st.success("Goal marked as completed!")
                        st.balloons()
                else:
                    st.success("Goal completed!")

def community_section():
    st.subheader("🌍 Community Hub")
    
    post = st.text_area("Share your thoughts, tips, or achievements:")
    if st.button("Submit Post"):
        c.execute("INSERT INTO community_posts (post, likes, date) VALUES (?, ?, ?)", 
                  (post, 0, datetime.now().isoformat()))
        conn.commit()
        st.success("Post shared with the community!")
    
    display_community_feed()
    
    community_summary = generate_ai_response("Summarize recent community activity and provide an encouraging message for community engagement.")
    st.info(community_summary)

def display_community_feed():
    c.execute("SELECT * FROM community_posts ORDER BY date DESC LIMIT 10")
    posts_data = c.fetchall()
    if posts_data:
        st.subheader("Community Feed")
        for post in posts_data:
            with st.expander(f"Post from {post[3]}"):
                st.write(post[1])
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(f"👍 {post[2]}", key=f"like_post_{post[0]}"):
                        c.execute("UPDATE community_posts SET likes = likes + 1 WHERE id = ?", (post[0],))
                        conn.commit()
                with col2:
                    st.write(f"Likes: {post[2]}")

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
    
    # Sidebar
    st.sidebar.title("🌿 EcoEats Navigation")
    st.sidebar.markdown("---")
    
    menu = ["Home", "Food Waste", "Healthy Eating", "Weekly Report", "Sustainability", "Goals", "Community"]
    
    # Create dropdown for navigation
    choice = st.sidebar.selectbox("Go to", menu)
    
    streak = update_streak()
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"Current Streak: {streak} days")
    st.sidebar.info(f"Achievement: {get_achievement(streak)}")
    
    # Main content
    st.title("🌿 EcoEats: Food Waste Reduction & Healthy Eating Tracker")
    
    if choice == "Home":
        st.write("Welcome to EcoEats! Your personalized food waste reduction and healthy eating tracker.")
        st.write("Use the sidebar to navigate through different features of the app.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🗑️ Food Waste")
            c.execute("SELECT COUNT(*) FROM food_waste")
            waste_count = c.fetchone()[0]
            st.metric("Items Logged", waste_count)
        with col2:
            st.subheader("🥗 Healthy Meals")
            c.execute("SELECT COUNT(*) FROM meals")
            meal_count = c.fetchone()[0]
            st.metric("Meals Tracked", meal_count)
        with col3:
            st.subheader("🎯 Goals")
            c.execute("SELECT COUNT(*) FROM goals WHERE completed=1")
            goal_count = c.fetchone()[0]
            st.metric("Goals Completed", goal_count)
        
        st.subheader("Quick Tips")
        quick_tip = generate_ai_response("Provide a quick, engaging tip for reducing food waste and eating healthier.")
        st.info(quick_tip)
        
        # Add a motivational quote
        quote = generate_ai_response("Generate a short, inspiring quote about sustainability or healthy eating.")
        st.markdown(f"### 💡 Thought of the Day\n\n{quote}")
        
    elif choice == "Food Waste":
        food_waste_notification()
    elif choice == "Healthy Eating":
        healthy_eating_tracker()
    elif choice == "Weekly Report":
        weekly_report()
    elif choice == "Sustainability":
        sustainability_tips()
    elif choice == "Goals":
        goal_setting()
    elif choice == "Community":
        community_section()

    # Add a footer
    st.markdown("---")
    st.markdown("Made with ❤️ by EcoEats Team")
    st.markdown("For support, contact us at support@ecoeats.com")

if __name__ == "__main__":
    main()