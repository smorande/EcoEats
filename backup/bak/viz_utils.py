import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

def create_waste_trend_chart(cursor):
    """Create food waste trend chart"""
    cursor.execute(
        "SELECT date, SUM(quantity) FROM food_waste WHERE date > ? GROUP BY date", 
        ((datetime.now() - timedelta(days=7)).isoformat(),)
    )
    waste_data = cursor.fetchall()
    
    if not waste_data:
        return None
        
    waste_df = pd.DataFrame(waste_data, columns=['date', 'quantity'])
    waste_df['date'] = pd.to_datetime(waste_df['date'])
    
    chart = alt.Chart(waste_df).mark_line(point=True).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('quantity:Q', title='Quantity'),
        tooltip=['date:T', 'quantity:Q']
    ).properties(
        title='Food Waste Trend',
        width='container',
        height=300
    )
    
    return chart

def create_meals_trend_chart(cursor):
    """Create meals trend chart"""
    cursor.execute(
        "SELECT date, COUNT(*) FROM meals WHERE date > ? GROUP BY date", 
        ((datetime.now() - timedelta(days=7)).isoformat(),)
    )
    meals_data = cursor.fetchall()
    
    if not meals_data:
        return None
        
    meals_df = pd.DataFrame(meals_data, columns=['date', 'count'])
    meals_df['date'] = pd.to_datetime(meals_df['date'])
    
    chart = alt.Chart(meals_df).mark_line(point=True).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('count:Q', title='Number of Meals'),
        tooltip=['date:T', 'count:Q']
    ).properties(
        title='Meals Logged Trend',
        width='container',
        height=300
    )
    
    return chart

def create_goals_charts(cursor):
    """Create charts for goals visualization"""
    cursor.execute("SELECT * FROM goals")
    goals_data = cursor.fetchall()
    
    if not goals_data:
        return None, None
        
    completed_goals = sum(1 for goal in goals_data if goal[5])
    incomplete_goals = len(goals_data) - completed_goals
    
    # Create pie chart
    fig1, ax1 = plt.subplots(figsize=(6, 6))
    ax1.pie([completed_goals, incomplete_goals], 
            labels=['Completed', 'In Progress'], 
            autopct='%1.1f%%',
            colors=['#2ecc71', '#e74c3c'])
    ax1.set_title("Goals Progress")
    
    # Create bar chart for potential savings
    goal_names = [goal[2][:20] + "..." if len(goal[2]) > 20 else goal[2] for goal in goals_data]
    savings = [float(goal[6].replace('$', '').strip()) if isinstance(goal[6], str) else 0.0 for goal in goals_data]
    
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    sns.barplot(x=goal_names, y=savings, ax=ax2)
    ax2.set_title("Potential Savings per Goal")
    ax2.set_xlabel("Goals")
    ax2.set_ylabel("Potential Savings ($)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return fig1, fig2