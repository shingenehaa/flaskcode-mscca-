from gtts import gTTS
import os

def main():
    text = "   not granted  park your vehicle outside "
    
    try:
        tts = gTTS(text=text, lang="en")
        tts.save("output.mp3")
        os.system("start output.mp3")
    except Exception as e:
        print("Text-to-speech error:", e)

if __name__ == "__main__":
 main()