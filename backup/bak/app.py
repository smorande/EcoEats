import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from PIL import Image
import io
import base64

# Import custom modules
from database import setup_database, update_streak, get_achievement
from ai_utils import generate_ai_response, analyze_image, analyze_grocery_list
from viz_utils import create_waste_trend_chart, create_meals_trend_chart, create_goals_charts

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(page_title="EcoEats Tracker", page_icon="🌿", layout="wide")

# Initialize database
conn = setup_database()
cursor = conn.cursor()

def home():
    """Home page with overview and quick actions"""
    st.write("Welcome to EcoEats! Your personalized food waste reduction and healthy eating tracker.")
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("🗑️ Food Waste")
        cursor.execute("SELECT COUNT(*) FROM food_waste")
        waste_count = cursor.fetchone()[0]
        st.metric("Items Logged", waste_count)
    
    with col2:
        st.subheader("🥗 Healthy Meals")
        cursor.execute("SELECT COUNT(*) FROM meals")
        meal_count = cursor.fetchone()[0]
        st.metric("Meals Tracked", meal_count)
    
    with col3:
        st.subheader("🎯 Goals")
        cursor.execute("SELECT COUNT(*) FROM goals WHERE completed=1")
        goal_count = cursor.fetchone()[0]
        st.metric("Goals Completed", goal_count)
    
    # Grocery List Analysis
    st.subheader("🛒 Grocery List Analysis")
    uploaded_image = st.file_uploader("Upload an image of your grocery list", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Grocery List", use_column_width=True)
        
        if st.button("Analyze Grocery List"):
            analysis = analyze_grocery_list(uploaded_image)
            st.write("Sustainability Analysis:")
            st.info(analysis)
    
    # Quick Tips
    st.subheader("Quick Tips")
    tip = generate_ai_response("Provide a quick, engaging tip for reducing food waste and eating healthier.")
    st.info(tip)
    
    # Daily Quote
    quote = generate_ai_response("Generate a short, inspiring quote about sustainability or healthy eating.")
    st.markdown(f"### 💡 Thought of the Day\n\n{quote}")

def food_waste_tracker():
    """Food waste tracking page"""
    st.subheader("🗑️ Food Waste Tracker")
    
    # Notification
    notification = generate_ai_response("Generate a short, engaging notification about reducing food waste.")
    st.info(notification)
    
    # Input form
    waste_item = st.text_input("Log wasted food item:")
    quantity_type = st.selectbox("Quantity type:", ["Solid (grams)", "Liquid (ml)"])
    quantity = st.number_input(f"Quantity ({quantity_type.split()[1]}):", min_value=0, step=10)
    
    # Image upload and analysis
    uploaded_image = st.file_uploader("Upload an image of the food waste (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Analyze Image"):
            analysis = analyze_image(uploaded_image, "Identify the food item and estimate its quantity.")
            st.write("AI Analysis:", analysis)
    
    # Log waste button
    if st.button("Log Waste"):
        image_data = uploaded_image.getvalue() if uploaded_image else None
        cursor.execute("""
            INSERT INTO food_waste (item, quantity, quantity_type, date, image) 
            VALUES (?, ?, ?, ?, ?)
        """, (waste_item, quantity, quantity_type, datetime.now().isoformat(), image_data))
        conn.commit()
        st.success(f"Logged: {quantity} {quantity_type.split()[1]} of {waste_item}")
    
    # Display trend chart
    waste_chart = create_waste_trend_chart(cursor)
    if waste_chart:
        st.altair_chart(waste_chart, use_container_width=True)
    else:
        st.info("Start logging waste to see your trends!")

def meal_tracker():
    """Healthy meal tracking page"""
    st.subheader("🥗 Healthy Eating Tracker")
    
    # Meal input
    meal = st.text_input("Describe your meal:")
    
    # Image upload and analysis
    uploaded_image = st.file_uploader("Upload an image of your meal (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Meal", use_column_width=True)
        
        if st.button("Analyze Meal"):
            analysis = analyze_image(uploaded_image, "Analyze this meal and provide nutritional information.")
            st.write("AI Analysis:", analysis)
    
    # Log meal button
    if st.button("Log Meal"):
        nutrition_info = generate_ai_response(f"Provide a brief nutritional summary for this meal: {meal}")
        image_data = uploaded_image.getvalue() if uploaded_image else None
        cursor.execute("""
            INSERT INTO meals (meal, nutrition, date, image) 
            VALUES (?, ?, ?, ?)
        """, (meal, nutrition_info, datetime.now().isoformat(), image_data))
        conn.commit()
        st.success("Meal logged successfully!")
        st.write("Nutritional Information:", nutrition_info)
    
    # Display trend chart
    meals_chart = create_meals_trend_chart(cursor)
    if meals_chart:
        st.altair_chart(meals_chart, use_container_width=True)
    else:
        st.info("Start logging meals to see your trends!")

def goal_tracker():
    """Goal setting and tracking page"""
    st.subheader("🎯 Goal Setting")
    
    # Goal input
    goal_type = st.selectbox("Goal Type:", ["Food Waste Reduction", "Healthy Eating"])
    goal = st.text_input("Set your goal:")
    
    if st.button("Set Goal"):
        recommendations = generate_ai_response(
            f"Provide personalized recommendations for achieving this {goal_type} goal: {goal}"
        )
        potential_savings = generate_ai_response(
            f"Estimate the potential money saved by achieving this {goal_type} goal: {goal}"
        )
        
        cursor.execute("""
            INSERT INTO goals (type, goal, recommendations, date, completed, potential_savings)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_type, goal, recommendations, datetime.now().isoformat(), False, potential_savings))
        conn.commit()
        
        st.success("Goal set successfully!")
        st.write("Recommendations:", recommendations)
        st.write("Potential Savings:", potential_savings)
    
    # Display goals charts
    fig1, fig2 = create_goals_charts(cursor)
    if fig1 and fig2:
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(fig1)
        with col2:
            st.pyplot(fig2)
    else:
        st.info("Start setting goals to see your progress!")

def main():
    """Main application"""
    # Custom CSS
    st.markdown("""
        <style>
        .sidebar .sidebar-content {
            background-image: linear-gradient(#2193b0, #6dd5ed);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🌿 EcoEats Navigation")
    
    # Update and display streak
    streak = update_streak(conn)
    st.sidebar.info(f"Current Streak: {streak} days")
    st.sidebar.info(f"Achievement: {get_achievement(streak)}")
    
    # Navigation
    menu = ["Home", "Food Waste Tracker", "Meal Tracker", "Goal Tracker"]
    choice = st.sidebar.selectbox("Go to", menu)
    
    # Display selected page
    if choice == "Home":
        home()
    elif choice == "Food Waste Tracker":
        food_waste_tracker()
    elif choice == "Meal Tracker":
        meal_tracker()
    elif choice == "Goal Tracker":
        goal_tracker()
    
    # Footer
    st.markdown("---")
    st.markdown("Made with ❤️ by EcoEats Team")

if __name__ == "__main__":
    main()