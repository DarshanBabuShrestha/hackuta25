import google.generativeai as genai
import os
import base64
import cv2
import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini AI Model
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize Text-to-Speech
engine = pyttsx3.init()
engine.setProperty("rate", 150)  

# Initialize Speech Recognition
recognizer = sr.Recognizer()
mic = sr.Microphone()

# Open webcam for live video
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print(" Error: Could not open video stream.")
    exit()

print(" Live GeminEye Running...")


# Announce welcome message
welcome_message = "Welcome to GeminEye. I will assist you with navigation. Please keep the camera still.Say stop to exit"
exit_message="Thank you for using GeminEye"
print(f"🗣️ {welcome_message}")
engine.say(welcome_message)
engine.runAndWait()

def get_speech_input():
    """Captures speech input from the user."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for a command...")
        try:
            audio = recognizer.listen(source, timeout=15)
            text = recognizer.recognize_google(audio)
            print(f"🎙️ You said: {text}")
            # ✅ Exit if "stop" is detected
            if "stop" in text:
                print("Exiting GeminEye.")
                engine.say("Thankyou for using GeminEye. Goodbye.")
                engine.runAndWait()
                
                cap.release()
                cv2.destroyAllWindows()
                exit()

            return text

        except sr.UnknownValueError:
            print(" Could not understand speech.")
            return None
        except sr.RequestError:
            print("Speech recognition service unavailable.")
            return None

while True:
    ret, frame = cap.read()
    if not ret:
        print(" Error: Could not capture frame.")
        break
   # frame = cv2.flip(frame, 1) 
    # Convert frame to Base64
    _, buffer = cv2.imencode('.jpg', frame)
    img_base64 = base64.b64encode(buffer).decode("utf-8")

    # Get speech input
    speech_text = get_speech_input()
    if speech_text:
        # Send frame & speech input to Gemini
        response = model.generate_content([
            {"mime_type": "image/jpeg", "data": img_base64},
            {"text": f"""
You are an AI assistant helping a blind person navigate their surroundings.
    Analyze the following images of their environment.
    Describe the scene from the perspective of a blind person.
    Focus on providing information that is crucial for safe navigation.
    Specifically identify:
    - Potential obstacles in their path (e.g., chairs, steps, uneven ground, objects on the floor).
    - Clear pathways or directions they can take.
    - Any hazards they should be aware of (e.g., traffic sounds, drop-offs, overhanging objects).
    - Describe the general layout of the immediate surroundings in a way that is easy to understand through audio.

    Provide concise, actionable instructions in 2-3 short sentences.
    Start with an overview of the immediate environment and then give a direction or warning.
    For example: "In front of you, the path seems clear. You can walk straight ahead. Be aware of a slight step down in about 5 feet."
    Or: "It appears you are facing a wall. To your left, there is an open doorway. To your right, there might be chairs. Turn left to proceed through the doorway."
    Imagine you are their eyes and your description is their primary source of visual information.

User's question: '{speech_text}' 
Based on the latest live image, provide the best possible guidance to help the user move safely and locate what they need.The objects in the image are mirrored so keep that in mind.
"""}
        ])

        # Extract AI-generated response
        ai_description = response.text if response.text else "No description available."
        print(f"AI Guidance: {ai_description}")

        # Convert AI response to speech
        engine.say(ai_description)
        engine.runAndWait()

        # Display AI response on video feed
        display_text = ai_description.split(".")[0]  
        cv2.putText(frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Show live video with AI guidance overlay
    cv2.imshow("Gemini 1.5 flash Live Navigation", frame)

  

cap.release()
cv2.destroyAllWindows()
print("AI navigation ended.")
