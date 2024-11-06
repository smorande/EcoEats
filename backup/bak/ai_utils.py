import openai
import streamlit as st
import base64
from PIL import Image
import io

@st.cache_data(show_spinner=False)
def generate_ai_response(prompt, max_tokens=150):
    """Generate AI response using OpenAI API"""
    try:
        response = openai.ChatCompletion.create(
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
    """Analyze image using OpenAI API"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": task},
                        {"type": "image_url", 
                         "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image.getvalue()).decode()}"}}
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
    """Analyze grocery list image and provide sustainability recommendations"""
    return analyze_image(image, 
                        "Analyze this grocery list image and provide sustainability recommendations. "
                        "Consider packaging, local vs. imported items, and potential for food waste.")