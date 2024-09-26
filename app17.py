import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sqlite3
import openai
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
import requests
from fpdf import FPDF
import tweepy
import facebook
import tempfile
import seaborn as sns

# Set page config at the very beginning of the script
st.set_page_config(page_title="EcoEats Tracker", page_icon="🌿", layout="wide")

# Load environment variables
load_dotenv()

# Make sure you've set your API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database setup
@st.cache_resource
def get_database_connection():
    return sqlite3.connect('ecoeats.db', check_same_thread=False)

conn = get_database_connection()
c = conn.cursor()

# Create tables if they don't exist and add new columns
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
    
    # Add 'image' column to food_waste table if it doesn't exist
    c.execute("PRAGMA table_info(food_waste)")
    columns = [column[1] for column in c.fetchall()]
    if 'image' not in columns:
        c.execute("ALTER TABLE food_waste ADD COLUMN image BLOB")
    
    # Add 'image' and 'quantity' columns to meals table if they don't exist
    c.execute("PRAGMA table_info(meals)")
    columns = [column[1] for column in c.fetchall()]
    if 'image' not in columns:
        c.execute("ALTER TABLE meals ADD COLUMN image BLOB")
    if 'quantity' not in columns:
        c.execute("ALTER TABLE meals ADD COLUMN quantity INTEGER")
    
    conn.commit()

setup_database()

# AI Utility Function
@st.cache_data(show_spinner=False)
def generate_ai_response(prompt, max_tokens=150):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",  # Using gpt-4-vision-preview as a stand-in for "get-4o-mini"
            messages=[
                {"role": "system", "content": "You are a helpful assistant for an eco-friendly food tracking app."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error in AI response generation: {str(e)}")
        return "I'm sorry, I couldn't generate a response at this time."

# New function for image analysis
def analyze_image(image, task):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": task},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image.getvalue()).decode()}"}}
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error in image analysis: {str(e)}")
        return "I'm sorry, I couldn't analyze the image at this time."

# Login function
def login():
    st.title("🌿 EcoEats Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "kanwal" and password == "swapnil":
            st.session_state.logged_in = True
            st.success("Logged in successfully!")
        else:
            st.error("Incorrect username or password")

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
    
    # New: Image upload for food waste
    uploaded_image = st.file_uploader("Upload an image of the food waste (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Analyze Image"):
            analysis_result = analyze_image(uploaded_image, "Identify the food item and estimate its quantity in grams.")
            st.write("AI Analysis:", analysis_result)
            # Extract quantity from AI analysis (assuming it's provided in a structured format)
            # This is a simplified extraction, you might need more robust parsing depending on the AI output
            try:
                ai_quantity = int(analysis_result.split("grams")[0].split()[-1])
                quantity = ai_quantity
                st.write(f"Estimated quantity: {quantity} grams")
            except:
                st.write("Couldn't automatically extract quantity. Please input manually.")
    
    if st.button("Log Waste"):
        image_data = uploaded_image.getvalue() if uploaded_image else None
        c.execute("INSERT INTO food_waste (item, quantity, date, image) VALUES (?, ?, ?, ?)", 
                  (waste_item, quantity, datetime.now().isoformat(), image_data))
        conn.commit()
        st.success(f"Logged: {quantity}g of {waste_item}")
    
    display_waste_chart()

def display_waste_chart():
    c.execute("SELECT * FROM food_waste ORDER BY date DESC LIMIT 5")
    waste_data = c.fetchall()
    if waste_data:
        st.subheader("Recent Food Waste")
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
    
    # New: Image upload for meal logging
    uploaded_image = st.file_uploader("Upload an image of your meal (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Meal", use_column_width=True)
        
        if st.button("Analyze Meal"):
            analysis_result = analyze_image(uploaded_image, "Identify the meal components and estimate their quantities.")
            st.write("AI Analysis:", analysis_result)
            # Extract quantity from AI analysis (this is a simplified approach)
            try:
                # Assuming the AI provides a total calorie estimate
                ai_quantity = int(analysis_result.split("calories")[0].split()[-1])
                st.write(f"Estimated calories: {ai_quantity}")
            except:
                st.write("Couldn't automatically extract calorie information. Please input manually if needed.")
    
    if st.button("Log Meal"):
        nutrition_info = generate_ai_response(f"Provide a brief, engaging nutritional summary for this meal: {meal}")
        image_data = uploaded_image.getvalue() if uploaded_image else None
        c.execute("INSERT INTO meals (meal, nutrition, date, image) VALUES (?, ?, ?, ?)", 
                  (meal, nutrition_info, datetime.now().isoformat(), image_data))
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
                if meal[4]:  # If image data exists
                    try:
                        # Check if the image data is already bytes, if not, encode it
                        image_data = meal[4] if isinstance(meal[4], bytes) else meal[4].encode('utf-8')
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image, caption="Meal Image", use_column_width=True)
                    except Exception as e:
                        st.error(f"Error displaying image: {str(e)}")

def weekly_report():
    st.subheader("📊 Weekly Progress Report")
    
    display_waste_trend()
    display_meals_trend()
    
    summary = generate_ai_response("Generate a brief, encouraging summary of progress in reducing food waste and eating healthy based on the charts.")
    st.info(summary)
    
    # New: PDF Download option
    if st.button("Generate PDF Report"):
        pdf_buffer = generate_pdf_report()
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name="weekly_report.pdf",
            mime="application/pdf"
        )

def generate_pdf_report():
    pdf = FPDF()
    pdf.add_page()
    
    # Set font and colors
    pdf.set_font("Arial", "B", 16)
    pdf.set_fill_color(200, 220, 255)
    
    # Title
    pdf.cell(0, 10, "EcoEats Weekly Report", 0, 1, "C", 1)
    pdf.ln(10)
    
    # Summary
    pdf.set_font("Arial", "", 12)
    summary = generate_ai_response("Generate a comprehensive summary of the user's progress in reducing food waste and eating healthy this week. Include specific metrics and encouragement.")
    pdf.multi_cell(0, 10, summary)
    pdf.ln(10)
    
    # Food Waste Chart
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Food Waste Trend", 0, 1, "C")
    waste_chart = create_waste_trend_chart()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name)
        pdf.image(tmpfile.name, x=10, y=pdf.get_y(), w=190)
    pdf.ln(100)  # Adjust spacing
    
    # Meals Chart
    pdf.cell(0, 10, "Meals Logged Trend", 0, 1, "C")
    meals_chart = create_meals_trend_chart()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name)
        pdf.image(tmpfile.name, x=10, y=pdf.get_y(), w=190)
    pdf.ln(100)  # Adjust spacing
    
    # Sustainability Tips
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Sustainability Tips", 0, 1, "L")
    pdf.set_font("Arial", "", 12)
    tips = generate_ai_response("Provide 3 actionable tips for reducing food waste and eating more sustainably.")
    pdf.multi_cell(0, 10, tips)
    
    return pdf.output(dest='S').encode('latin-1')

def create_waste_trend_chart():
    c.execute("SELECT date, SUM(quantity) FROM food_waste WHERE date > ? GROUP BY date", 
              ((datetime.now() - timedelta(days=7)).isoformat(),))
    waste_data = c.fetchall()
    waste_df = pd.DataFrame(waste_data, columns=['date', 'quantity'])
    waste_df['date'] = pd.to_datetime(waste_df['date'])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(data=waste_df, x='date', y='quantity', marker='o', ax=ax)
    ax.set_title("Food Waste Trend")
    ax.set_xlabel("Date")
    ax.set_ylabel("Quantity (g)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def create_meals_trend_chart():
    c.execute("SELECT date, COUNT(*) FROM meals WHERE date > ? GROUP BY date", 
              ((datetime.now() - timedelta(days=7)).isoformat(),))
    meals_data = c.fetchall()
    meals_df = pd.DataFrame(meals_data, columns=['date', 'count'])
    meals_df['date'] = pd.to_datetime(meals_df['date'])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(data=meals_df, x='date', y='count', marker='o', ax=ax)
    ax.set_title("Meals Logged Trend")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Meals")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

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
        
        # Create a pie chart of completed vs. incomplete goals
        completed_goals = sum(1 for goal in goals_data if goal[5])
        incomplete_goals = len(goals_data) - completed_goals
        
        fig, ax = plt.subplots()
        ax.pie([completed_goals, incomplete_goals], labels=['Completed', 'In Progress'], autopct='%1.1f%%')
        ax.set_title("Goals Progress")
        st.pyplot(fig)
        
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
    
    # Social Media Integration
    st.subheader("Share on Social Media")
    platform = st.selectbox("Choose a platform", ["Twitter", "Facebook", "Instagram"])
    
    if platform == "Twitter":
        twitter_post = st.text_area("Compose your tweet:", max_chars=280)
        if st.button("Post to Twitter"):
            post_to_twitter(twitter_post)
    elif platform == "Facebook":
        facebook_post = st.text_area("Compose your Facebook post:")
        if st.button("Post to Facebook"):
            post_to_facebook(facebook_post)
    elif platform == "Instagram":
        instagram_caption = st.text_area("Compose your Instagram caption:")
        instagram_image = st.file_uploader("Upload an image for Instagram", type=["jpg", "jpeg", "png"])
        if st.button("Prepare Instagram Post"):
            prepare_instagram_post(instagram_caption, instagram_image)

def post_to_twitter(tweet):
    # Twitter API credentials (you'll need to set these up)
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    # Authenticate with Twitter
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    
    try:
        api.update_status(tweet)
        st.success("Tweet posted successfully!")
    except Exception as e:
        st.error(f"Error posting to Twitter: {str(e)}")

def post_to_facebook(post):
    # Facebook API credentials (you'll need to set these up)
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    
    try:
        graph = facebook.GraphAPI(access_token)
        graph.put_object(parent_object='me', connection_name='feed', message=post)
        st.success("Posted to Facebook successfully!")
    except facebook.GraphAPIError as e:
        st.error(f"Error posting to Facebook: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error posting to Facebook: {str(e)}")

def prepare_instagram_post(caption, image):
    if image is not None:
        # Convert the image to base64 for display
        image_base64 = base64.b64encode(image.getvalue()).decode()
        st.image(image, caption="Your Instagram Image", use_column_width=True)
    else:
        st.warning("No image uploaded. Instagram posts require an image.")
        return

    st.subheader("Instagram Post Preview")
    st.write("Caption:")
    st.write(caption)

    st.subheader("Instructions for Posting to Instagram")
    st.markdown("""
    1. Save the image displayed above to your device.
    2. Open the Instagram app on your mobile device.
    3. Tap the '+' button to create a new post.
    4. Select the image you just saved.
    5. Tap 'Next' and apply any filters if desired.
    6. Tap 'Next' again and paste the following caption:
    """)
    st.code(caption)
    st.markdown("""
    7. Add any location or tags as desired.
    8. Tap 'Share' to post to Instagram.
    """)

    st.success("Your Instagram post is ready! Follow the instructions above to post it manually.")

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
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
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