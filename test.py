import google.generativeai as genai
import os
import base64
import cv2
import time
from dotenv import load_dotenv
import sys
import threading
from gtts import gTTS
import playsound
import queue
import tempfile

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def capture_frames(num_frames=5, interval=0.5):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        return None

    frame_paths = []
    print("Capturing frames...")
    narration_queue.put("Scanning surroundings to understand your environment.")

    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Could not capture frame {i+1}.")
            cap.release()
            return None

        frame_path = f"frame_{i+1}.jpg"
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)
        print(f"Captured frame {i+1}")
        time.sleep(interval)

    cap.release()
    return frame_paths

def get_ai_transcript(image_paths):
    if not image_paths:
        return "No images to analyze."

    contents = []
    for path in image_paths:
        encoded_image = encode_image(path)
        contents.append({"mime_type": "image/jpeg", "data": encoded_image})

    prompt_text = """
    You are an AI assistant guiding a blind person. Analyze the images to describe their surroundings for navigation.
    Identify objects and potential obstacles.
    For each significant object or obstacle, **estimate its distance relative to the user** and its approximate direction (left, right, ahead, etc.).
    Use qualitative distance descriptions like:
    - "Immediately in front of you"
    - "Very close by"
    - "Nearby on your left/right"
    - "A few steps ahead"
    - "In the distance"

    Focus on safety and clear navigation instructions. Provide concise guidance in 2-3 sentences, including distance estimations where relevant.

    Example Output:
    "The path ahead appears clear. There's a chair very close by on your right. A few steps ahead, you might encounter a small rug on the floor. Proceed cautiously."

    Another Example:
    "You are facing a doorway. Immediately in front, the floor seems level. To your left, nearby, there's a table. The doorway appears to lead to a hallway straight ahead."
    """
    contents.append({"text": prompt_text})

    try:
        response = model.generate_content(contents)
        response.resolve()
        ai_transcript = response.text if response.text else "I am unable to understand the surroundings clearly. Please try scanning again."

        ai_transcript = ai_transcript.strip()

        return ai_transcript
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return "Error getting AI guidance. Please try again."

narration_queue = queue.Queue()
is_narrating = False

def narrate_description(description):
    global is_narrating
    if not description or is_narrating:
        return

    is_narrating = True
    print(f"🗣️ Narrating: {description}")
    try:
        tts = gTTS(text=description, lang='en')
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            tts.save(tmp_file.name + ".mp3")
            playsound.playsound(tmp_file.name + ".mp3", block=True)
    except Exception as e:
        print(f"Error during narration: {e}")
    finally:
        is_narrating = False

def narration_worker():
    while True:
        description = narration_queue.get()
        if description is None:
            break
        narrate_description(description)
        narration_queue.task_done()

narration_thread = threading.Thread(target=narration_worker, daemon=True)
narration_thread.start()


def main_loop():
    while True:
        print("\n--- Navigation Assistant ---")
        narration_queue.put("Navigation Assistant Ready. Press Enter to scan surroundings.")

        input("Press Enter to scan your surroundings...")

        print("Starting scan: Understanding your surroundings...")
        frame_paths = capture_frames()

        if frame_paths:
            print("Analyzing images to provide navigation guidance...")
            narration_queue.put("Analyzing surroundings for navigation guidance.")
            ai_transcript = get_ai_transcript(frame_paths)
            print("\nAI Navigation Guidance:")
            print(ai_transcript)
            narration_queue.put(ai_transcript)

            while True:
                user_input = input("\nWhat would you like to do? (Options: 'rescan', 'thank you', 'q' to quit): ").lower()
                if user_input == "rescan":
                    narration_queue.put("Please rescan your surroundings when you are ready.")
                    break
                elif user_input == "thank you":
                    print("You've reached your destination or are done navigating. Closing Navigation Assistant. Thank you!")
                    narration_queue.put("Navigation complete. Closing Navigation Assistant. Thank you.")
                    return
                elif user_input == "q":
                    print("Exiting Navigation Assistant.")
                    narration_queue.put("Exiting Navigation Assistant.")
                    return
                else:
                    print("Invalid command. Please choose from 'rescan', 'thank you', or 'q'.")
                    narration_queue.put("Invalid command. Please choose 'rescan', 'thank you', or 'quit'.")
        else:
            print("Failed to capture frames. Please check your camera and try again.")
            narration_queue.put("Camera error. Failed to capture frames. Please check your camera and try again.")

if __name__ == "__main__":
    print("Starting Navigation Assistant...")
    narration_queue.put("Starting Navigation Assistant. System initializing.")
    main_loop()
    narration_queue.put(None)
    narration_thread.join()
    cv2.destroyAllWindows()
    sys.exit()