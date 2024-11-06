import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import random
import base64
from io import BytesIO
import os
from dotenv import load_dotenv
from gtts import gTTS
import altair as alt

# Load environment variables
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize session state
if 'food_waste' not in st.session_state:
    st.session_state.food_waste = []
if 'meals' not in st.session_state:
    st.session_state.meals = []
if 'goals' not in st.session_state:
    st.session_state.goals = []
if 'challenges' not in st.session_state:
    st.session_state.challenges = []
if 'community_posts' not in st.session_state:
    st.session_state.community_posts = []
if 'user_streak' not in st.session_state:
    st.session_state.user_streak = 0
if 'last_login' not in st.session_state:
    st.session_state.last_login = None

# AI Utility Functions
def generate_ai_response(prompt, max_tokens=150):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
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

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='en')
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
    except Exception as e:
        st.error(f"Error in text-to-speech conversion: {str(e)}")
        return None

# UI Helper Functions
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def remote_css(url):
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)

def icon(icon_name):
    st.markdown(f'<i class="material-icons">{icon_name}</i>', unsafe_allow_html=True)

# Gamification Functions
def update_streak():
    today = datetime.now().date()
    if 'last_login' not in st.session_state:
        st.session_state.last_login = today
    if 'user_streak' not in st.session_state:
        st.session_state.user_streak = 0

    if st.session_state.last_login:
        if (today - st.session_state.last_login).days == 1:
            st.session_state.user_streak += 1
        elif (today - st.session_state.last_login).days > 1:
            st.session_state.user_streak = 0
    st.session_state.last_login = today

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
def food_waste_notification():
    st.subheader("🗑️ Food Waste Notifications")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        notification = generate_ai_response("Generate a short, engaging notification about reducing food waste.")
        st.info(notification)
    
    with col2:
        if st.button("🔊 Speak"):
            audio = text_to_speech(notification)
            if audio:
                st.audio(audio, format='audio/mp3', start_time=0)
    
    waste_item = st.text_input("Log wasted food item:")
    quantity = st.number_input("Quantity (in grams):", min_value=0, step=10)
    
    if st.button("Log Waste"):
        st.session_state.food_waste.append({
            "item": waste_item,
            "quantity": quantity,
            "date": datetime.now().isoformat()
        })
        st.success(f"Logged: {quantity}g of {waste_item}")
    
    if st.session_state.food_waste:
        st.subheader("Recent Food Waste")
        waste_df = pd.DataFrame(st.session_state.food_waste)
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        waste_df = waste_df.sort_values('date', ascending=False).head(5)
        
        chart = alt.Chart(waste_df).mark_bar().encode(
            x='date:T',
            y='quantity:Q',
            color='item:N',
            tooltip=['date', 'item', 'quantity']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

def healthy_eating_tracker():
    st.subheader("🥗 Healthy Eating Tracker")
    
    meal = st.text_input("Describe your meal:")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("Log Meal"):
            nutrition_info = generate_ai_response(f"Provide a brief, engaging nutritional summary for this meal: {meal}")
            st.session_state.meals.append({
                "meal": meal,
                "nutrition": nutrition_info,
                "date": datetime.now().isoformat()
            })
            st.success("Meal logged successfully!")
            st.write(nutrition_info)
    
    with col2:
        if st.button("🔊 Speak Nutrition Info"):
            audio = text_to_speech(nutrition_info)
            if audio:
                st.audio(audio, format='audio/mp3', start_time=0)
    
    if st.session_state.meals:
        st.subheader("Recent Meals")
        meals_df = pd.DataFrame(st.session_state.meals)
        meals_df['date'] = pd.to_datetime(meals_df['date'])
        meals_df = meals_df.sort_values('date', ascending=False).head(5)
        
        for _, row in meals_df.iterrows():
            with st.expander(f"{row['date'].date()} - {row['meal']}"):
                st.write(row['nutrition'])

def weekly_report():
    st.subheader("📊 Weekly Progress Report")
    
    # Food Waste Chart
    waste_df = pd.DataFrame(st.session_state.food_waste)
    if not waste_df.empty:
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        waste_df = waste_df[waste_df['date'] > datetime.now() - timedelta(days=7)]
        waste_df = waste_df.groupby('date').sum().reset_index()
        
        waste_chart = alt.Chart(waste_df).mark_area().encode(
            x='date:T',
            y='quantity:Q',
            tooltip=['date', 'quantity']
        ).properties(title="Food Waste This Week")
        st.altair_chart(waste_chart, use_container_width=True)
    
    # Meals Chart
    meals_df = pd.DataFrame(st.session_state.meals)
    if not meals_df.empty:
        meals_df['date'] = pd.to_datetime(meals_df['date'])
        meals_df = meals_df[meals_df['date'] > datetime.now() - timedelta(days=7)]
        meals_df['count'] = 1
        meals_df = meals_df.groupby('date').count().reset_index()
        
        meals_chart = alt.Chart(meals_df).mark_line().encode(
            x='date:T',
            y='count:Q',
            tooltip=['date', 'count']
        ).properties(title="Meals Logged This Week")
        st.altair_chart(meals_chart, use_container_width=True)
    
    summary = generate_ai_response("Generate a brief, encouraging summary of progress in reducing food waste and eating healthy based on the charts.")
    st.info(summary)
    
    if st.button("🔊 Speak Summary"):
        audio = text_to_speech(summary)
        if audio:
            st.audio(audio, format='audio/mp3', start_time=0)

def sustainability_tips():
    st.subheader("🌱 Sustainability Tips & Challenges")
    
    tip = generate_ai_response("Provide an engaging tip for reducing food waste and eating more sustainably.")
    st.info(tip)
    
    if st.button("🔊 Speak Tip"):
        audio = text_to_speech(tip)
        if audio:
            st.audio(audio, format='audio/mp3', start_time=0)
    
    st.subheader("Weekly Challenge")
    if not st.session_state.challenges or st.session_state.challenges[-1]['end_date'] < datetime.now().date():
        new_challenge = generate_ai_response("Create a week-long challenge related to reducing food waste or eating more sustainably.")
        st.session_state.challenges.append({
            'challenge': new_challenge,
            'start_date': datetime.now().date(),
            'end_date': datetime.now().date() + timedelta(days=7),
            'completed': False
        })
    
    current_challenge = st.session_state.challenges[-1]
    st.write(f"**Challenge:** {current_challenge['challenge']}")
    st.write(f"**Start Date:** {current_challenge['start_date']}")
    st.write(f"**End Date:** {current_challenge['end_date']}")
    
    if not current_challenge['completed']:
        if st.button("Mark as Completed"):
            current_challenge['completed'] = True
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
        st.session_state.goals.append({
            'type': goal_type,
            'goal': goal,
            'recommendations': recommendations,
            'date': datetime.now().isoformat(),
            'completed': False
        })
        st.success("Goal set successfully!")
        st.write("Personalized Recommendations:")
        st.info(recommendations)
        
        audio = text_to_speech(f"Goal set. Here are some recommendations: {recommendations}")
        if audio:
            st.audio(audio, format='audio/mp3', start_time=0)
    
    if st.session_state.goals:
        st.subheader("Your Goals")
        for i, goal in enumerate(st.session_state.goals):
            with st.expander(f"{goal['type']}: {goal['goal']}"):
                st.write(f"Set on: {goal['date']}")
                st.write(f"Recommendations: {goal['recommendations']}")
                if not goal['completed']:
                    if st.button(f"Mark as Completed", key=f"complete_goal_{i}"):
                        goal['completed'] = True
                        st.success("Goal marked as completed!")
                        st.balloons()
                else:
                    st.success("Goal completed!")

def community_section():
    st.subheader("🌍 Community Hub")
    
    post = st.text_area("Share your thoughts, tips, or achievements:")
    if st.button("Submit Post"):
        st.session_state.community_posts.append({
            'post': post,
            'likes': 0,
            'date': datetime.now().isoformat()
        })
        st.success("Post shared with the community!")
    
    if st.session_state.community_posts:
        st.subheader("Community Feed")
        for i, post in enumerate(reversed(st.session_state.community_posts)):
            with st.expander(f"Post from {post['date']}"):
                st.write(post['post'])
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(f"👍 {post['likes']}", key=f"like_post_{i}"):
                        post['likes'] += 1
                with col2:
                    st.write(f"Likes: {post['likes']}")
    
    community_summary = generate_ai_response("Summarize recent community activity and provide an encouraging message for community engagement.")
    st.info(community_summary)
    
    if st.button("🔊 Hear Community Updates"):
        audio = text_to_speech(community_summary)
        if audio:
            st.audio(audio, format='audio/mp3', start_time=0)

def main():
    st.set_page_config(page_title="EcoEats Tracker", page_icon="🌿", layout="wide")
    
    # local_css("style.css")  # Uncomment if you have a local CSS file
    remote_css('https://fonts.googleapis.com/icon?family=Material+Icons')
    
    # Update user streak
    update_streak()
    
    # Sidebar
    st.sidebar.title("🌿 EcoEats Navigation")
    st.sidebar.markdown("---")
    
    menu = ["Home", "Food Waste", "Healthy Eating", "Weekly Report", "Sustainability", "Goals", "Community"]
    
    # Create radio buttons for navigation
    choice = st.sidebar.radio("Go to", menu)
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"Current Streak: {st.session_state.user_streak} days")
    st.sidebar.info(f"Achievement: {get_achievement(st.session_state.user_streak)}")
    st.sidebar.info("EcoEats: Your personal food waste reduction and healthy eating companion.")
    
    # Main content
    st.title("🌿 EcoEats: Food Waste Reduction & Healthy Eating Tracker")
    
    if choice == "Home":
        st.write("Welcome to EcoEats, your personalized food waste reduction and healthy eating tracker!")
        st.write("Use the sidebar to navigate through different features of the app.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🗑️ Food Waste")
            waste_count = len(st.session_state.food_waste)
            st.metric("Items Logged", waste_count)
        with col2:
            st.subheader("🥗 Healthy Meals")
            meal_count = len(st.session_state.meals)
            st.metric("Meals Tracked", meal_count)
        with col3:
            st.subheader("🎯 Goals")
            goal_count = len([g for g in st.session_state.goals if g['completed']])
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