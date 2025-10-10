# Meet my AI Twin
A digital avatar that looks and sounds just like me. Users can prompt this clone to say anything they desire (though inputs are later censored to ensure appropriate content outputs). Developed to help spread awareness on the complexity and nuance of deepfake technology that exists today. 

## Demo
Click on the video below to see my clone live in action. Specially recommended for Pink Floyd fans 🎸:

https://github.com/user-attachments/assets/1715745d-7579-4273-abde-3b62ca24a59f

If your GitHub page doesn't render `<video>` previews (some mobile or dark-mode clients),  
you can also [▶️ watch the same demo here](samples/Pink_Floyd.mp4).

## How It Works

1. **User Input** → A short message typed into the Streamlit app.  
2. **Prompt Censorship** → A GPT-4 safety filter reformats the text and blocks inappropriate content.  
3. **Voice Cloning** → ElevenLabs generates lifelike audio from the sanitized prompt.  
4. **Facial Animation** → D-ID animates a static reference image using the cloned audio.  
5. **Synthesis Output** → The generated video appears instantly on the web app — non-downloadable, short, and ethically constrained.


## Security
- User prompts are censored by AI before video synthesis to filter out inappropriate content
- Videos output on web app are non-downloadable
- Secret keys are obfuscated; samples are given in ```.env.example```

## Project Structure
```
ai-clone/
├── app.py                  # Main Streamlit application
├── .env.example            # Sample environment variables
├── requirements.txt
├── style.css               # Custom UI styles
├── samples/                # Short demo videos
│   ├── Hello_World.mp4
│   ├── Joke.mp4
│   ├── French.mp4
│   ├── Pink_Floyd.mp4
│   ├── Star_Wars.mp4       
│   └── reference_image.jpg
├─ .gitignore
├─ .streamlit/config.toml
└── README.md
```

## Installation and Usage

```bash
# 1. Clone this repo
git clone https://github.com/<your-username>/ai-clone.git
cd ai-clone

# 2. Create and fill a .env from the template
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
