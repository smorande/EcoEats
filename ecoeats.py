import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sqlite3
from openai import OpenAI
import matplotlib.pyplot as plt
import io
from io import BytesIO  # Add this import
import base64
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.platypus import PageBreak
import seaborn as sns

# Set page config at the very beginning of the script
st.set_page_config(page_title="EcoEats Tracker", page_icon="🌿", layout="wide")

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database setup
@st.cache_resource
def get_database_connection():
    return sqlite3.connect('ecoeats.db', check_same_thread=False)

conn = get_database_connection()
c = conn.cursor()

def setup_database():
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

# Call setup_database() at the beginning of your script
setup_database()

# AI Utility Functions
@st.cache_data(show_spinner=False)
def generate_ai_response(prompt, max_tokens=150):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
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

def analyze_image(image, task):
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": task},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64.b64encode(image.getvalue()).decode()}"
                            }
                        }
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error in image analysis: {str(e)}")
        return "I'm sorry, I couldn't analyze the image at this time."

def analyze_grocery_list(image):
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this grocery list image and provide sustainability recommendations. Consider packaging, local vs. imported items, and potential for food waste."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64.b64encode(image.getvalue()).decode()}"
                            }
                        }
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error in grocery list analysis: {str(e)}")
        return "I'm sorry, I couldn't analyze the grocery list at this time."

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

def home():
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
    
    st.subheader("🛒 Grocery List Analysis")
    uploaded_image = st.file_uploader("Upload an image of your grocery list", type=["jpg", "jpeg", "png"])
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Grocery List", use_column_width=True)
        
        if st.button("Analyze Grocery List"):
            analysis_result = analyze_grocery_list(uploaded_image)
            st.write("Sustainability Analysis:")
            st.info(analysis_result)
    
    st.subheader("Quick Tips")
    quick_tip = generate_ai_response("Provide a quick, engaging tip for reducing food waste and eating healthier.")
    st.info(quick_tip)
    
    quote = generate_ai_response("Generate a short, inspiring quote about sustainability or healthy eating.")
    st.markdown(f"### 💡 Thought of the Day\n\n{quote}")

def food_waste_notification():
    st.subheader("🗑️ Food Waste Notifications")
    
    notification = generate_ai_response("Generate a short, engaging notification about reducing food waste.")
    st.info(notification)
    
    waste_item = st.text_input("Log wasted food item:")
    quantity_type = st.selectbox("Quantity type:", ["Solid (grams)", "Liquid (ml)"])
    quantity = st.number_input(f"Quantity ({quantity_type.split()[1]}):", min_value=0, step=10)
    
    uploaded_image = st.file_uploader("Upload an image of the food waste (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Analyze Image"):
            analysis_result = analyze_image(uploaded_image, "Identify the food item and estimate its quantity in grams or ml.")
            st.write("AI Analysis:", analysis_result)
            try:
                ai_quantity = int(analysis_result.split(quantity_type.split()[1])[0].split()[-1])
                quantity = ai_quantity
                st.write(f"Estimated quantity: {quantity} {quantity_type.split()[1]}")
            except:
                st.write("Couldn't automatically extract quantity. Please input manually.")
    
    if st.button("Log Waste"):
        image_data = uploaded_image.getvalue() if uploaded_image else None
        c.execute("INSERT INTO food_waste (item, quantity, quantity_type, date, image) VALUES (?, ?, ?, ?, ?)", 
                  (waste_item, quantity, quantity_type, datetime.now().isoformat(), image_data))
        conn.commit()
        st.success(f"Logged: {quantity} {quantity_type.split()[1]} of {waste_item}")
    
def display_waste_chart():
    c.execute("SELECT * FROM food_waste ORDER BY date DESC LIMIT 5")
    waste_data = c.fetchall()
    if waste_data:
        st.subheader("Recent Food Waste")
        columns = [description[0] for description in c.description]
        waste_df = pd.DataFrame(waste_data, columns=columns)
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        
        # Handle NULL values in quantity_type
        waste_df['quantity_type'] = waste_df['quantity_type'].fillna('Unknown')
        
        chart = alt.Chart(waste_df).mark_bar().encode(
            x='date:T',
            y='quantity:Q',
            color='item:N',
            tooltip=['date:T', 'item:N', 'quantity:Q', 'quantity_type:N']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No food waste data available yet. Start logging to see your chart!")

def healthy_eating_tracker():
    st.subheader("🥗 Healthy Eating Tracker")
    
    meal = st.text_input("Describe your meal:")
    
    uploaded_image = st.file_uploader("Upload an image of your meal (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Meal", use_column_width=True)
        
        if st.button("Analyze Meal"):
            analysis_result = analyze_image(uploaded_image, "Identify the meal components and estimate their quantities.")
            st.write("AI Analysis:", analysis_result)
            
            # Get nutritional information using AI
            nutrition_info = generate_ai_response(
                f"Based on this meal analysis: {analysis_result}, provide detailed nutritional information including calories, protein, carbs, and fats."
            )
            st.write("Nutritional Information:", nutrition_info)
    
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
                nutrition_summary = meal[2][:100] + "..." if len(meal[2]) > 100 else meal[2]
                st.write(nutrition_summary)
                if meal[4]:  # If image data exists
                    try:
                        image_data = meal[4] if isinstance(meal[4], bytes) else meal[4].encode('utf-8')
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image, caption="Meal Image", use_column_width=True)
                    except Exception as e:
                        st.error(f"Error displaying image: {str(e)}")

def weekly_report():
    st.subheader("📊 Weekly Progress Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        display_waste_trend()
    
    with col2:
        display_meals_trend()
    
    # Generate weekly insights using AI
    c.execute("SELECT COUNT(*), SUM(quantity) FROM food_waste WHERE date >= date('now', '-7 days')")
    waste_stats = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM meals WHERE date >= date('now', '-7 days')")
    meal_stats = c.fetchone()
    
    stats_prompt = f"""Generate insights based on this week's data:
    - Food waste entries: {waste_stats[0]}
    - Total waste quantity: {waste_stats[1] if waste_stats[1] else 0}g/ml
    - Meals logged: {meal_stats[0]}
    Provide encouragement and specific suggestions for improvement."""
    
    insights = generate_ai_response(stats_prompt, max_tokens=300)
    st.info(insights)
    
    if st.button("Generate PDF Report"):
        pdf_buffer = generate_pdf_report()
        st.download_button(
            label="Download Your Weekly Sustainability Report",
            data=pdf_buffer,
            file_name=f"EcoEats_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
        st.success("Your report has been generated! Click above to download.")

def display_waste_trend():
    c.execute("""
        SELECT DATE(date) as date, SUM(quantity) as total
        FROM food_waste 
        WHERE date >= date('now', '-7 days')
        GROUP BY DATE(date)
        ORDER BY date
    """)
    waste_data = c.fetchall()
    
    if waste_data:
        waste_df = pd.DataFrame(waste_data, columns=['date', 'quantity'])
        waste_df['date'] = pd.to_datetime(waste_df['date'])
        
        chart = alt.Chart(waste_df).mark_area(
            color="lightblue",
            opacity=0.5
        ).encode(
            x='date:T',
            y='quantity:Q',
            tooltip=['date:T', 'quantity:Q']
        ).properties(
            title="Food Waste Trend (Last 7 Days)"
        )
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No food waste data available for the past week.")

def display_meals_trend():
    c.execute("""
        SELECT DATE(date) as date, COUNT(*) as count
        FROM meals 
        WHERE date >= date('now', '-7 days')
        GROUP BY DATE(date)
        ORDER BY date
    """)
    meals_data = c.fetchall()
    
    if meals_data:
        meals_df = pd.DataFrame(meals_data, columns=['date', 'count'])
        meals_df['date'] = pd.to_datetime(meals_df['date'])
        
        chart = alt.Chart(meals_df).mark_line(
            point=True,
            color="green"
        ).encode(
            x='date:T',
            y='count:Q',
            tooltip=['date:T', 'count:Q']
        ).properties(
            title="Meals Logged (Last 7 Days)"
        )
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No meals logged in the past week.")

def generate_pdf_report():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          leftMargin=0.5*inch, rightMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Fetch weekly statistics
    c.execute("""
        SELECT 
            COUNT(*) as entries,
            COALESCE(SUM(quantity), 0) as total_waste,
            COALESCE(AVG(quantity), 0) as avg_waste
        FROM food_waste 
        WHERE date >= date('now', '-7 days')
    """)
    waste_stats = c.fetchone()
    
    c.execute("""
        SELECT COUNT(*) 
        FROM meals 
        WHERE date >= date('now', '-7 days')
    """)
    meal_count = c.fetchone()[0]
    
    # Create the report content
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.green
    )
    story.append(Paragraph("EcoEats Weekly Sustainability Report", title_style))
    
    # Date range
    date_style = ParagraphStyle(
        'DateRange',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.gray
    )
    date_range = f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}"
    story.append(Paragraph(f"Report Period: {date_range}", date_style))
    story.append(Spacer(1, 20))
    
    # Summary Statistics
    stats_data = [
        ['Metric', 'Value'],
        ['Food Waste Entries', str(waste_stats[0])],
        ['Total Waste', f"{waste_stats[1]:.1f} g/ml"],
        ['Average Waste per Entry', f"{waste_stats[2]:.1f} g/ml"],
        ['Meals Logged', str(meal_count)]
    ]
    
    stats_table = Table(stats_data, colWidths=[2.5*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 20))
    
    # AI-generated insights
    insights_prompt = f"""Analyze these weekly statistics:
    - {waste_stats[0]} food waste entries
    - {waste_stats[1]:.1f} g/ml total waste
    - {meal_count} meals logged
    
    Provide detailed insights, trends, and actionable recommendations."""
    
    insights = generate_ai_response(insights_prompt, max_tokens=400)
    story.append(Paragraph("Weekly Insights", styles['Heading1']))
    story.append(Paragraph(insights, styles['Normal']))
    
    # Build the PDF
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def sustainability_tips():
    st.subheader("🌱 Sustainability Tips & Challenges")
    
    # Get current streak and achievement
    streak = update_streak()
    achievement = get_achievement(streak)
    
    # Display personalized tips based on user's progress
    tip_prompt = f"""Generate a personalized sustainability tip for a user who:
    - Has a {streak}-day streak
    - Current achievement level: {achievement}
    Make it specific and actionable."""
    
    tip = generate_ai_response(tip_prompt)
    st.info(tip)
    
    # Weekly Challenge Section
    st.subheader("🎯 Weekly Challenge")
    current_challenge = get_current_challenge()
    
    if current_challenge:
        display_challenge(current_challenge)
    else:
        create_new_challenge()

def get_current_challenge():
    c.execute("""
        SELECT * FROM challenges 
        WHERE end_date >= date('now')
        ORDER BY start_date DESC 
        LIMIT 1
    """)
    return c.fetchone()

def create_new_challenge():
    challenge_prompt = "Create an engaging weekly sustainability challenge focused on reducing food waste and promoting healthy eating. Include specific, measurable goals."
    new_challenge = generate_ai_response(challenge_prompt)
    
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=7)
    
    c.execute("""
        INSERT INTO challenges (challenge, start_date, end_date, completed) 
        VALUES (?, ?, ?, ?)
    """, (new_challenge, start_date.isoformat(), end_date.isoformat(), False))
    conn.commit()
    
    display_challenge((None, new_challenge, start_date.isoformat(), end_date.isoformat(), False))

def display_challenge(challenge):
    st.write(f"**Current Challenge:** {challenge[1]}")
    
    # Calculate days remaining
    end_date = datetime.strptime(challenge[3], "%Y-%m-%d").date()
    days_remaining = (end_date - datetime.now().date()).days
    
    st.write(f"**Days Remaining:** {days_remaining}")
    
    # Progress tracking
    progress = st.slider("Track your progress", 0, 100, 0)
    st.progress(progress / 100)
    
    if progress == 100 and not challenge[4]:
        if st.button("Complete Challenge"):
            c.execute("UPDATE challenges SET completed = TRUE WHERE id = ?", (challenge[0],))
            conn.commit()
            st.success("🎉 Congratulations on completing the challenge!")
            st.balloons()

def main():
    st.sidebar.title("🌿 EcoEats Navigation")
    
    # Update and display streak
    streak = update_streak()
    achievement = get_achievement(streak)
    
    st.sidebar.info(f"🔥 Current Streak: {streak} days")
    st.sidebar.info(f"🏆 Achievement: {achievement}")
    
    # Navigation
    pages = {
        "Home": home,
        "Food Waste Tracker": food_waste_notification,
        "Healthy Eating": healthy_eating_tracker,
        "Weekly Report": weekly_report,
        "Sustainability Tips": sustainability_tips
    }
    
    selection = st.sidebar.radio("Go to", list(pages.keys()))
    
    # Page title and content
    st.title("🌿 EcoEats: Your Sustainability Partner")
    pages[selection]()
    
    # Footer
    st.markdown("---")
    st.markdown("Made with ❤️ by EcoEats Team")

if __name__ == "__main__":
    main()