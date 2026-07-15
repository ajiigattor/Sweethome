import os
import json
import re
import requests
import time
from google import genai
from google.genai import types
from io import BytesIO
from PIL import Image

def main():
    # 1. Загрузка данных из GitHub Issue
    event_path = os.getenv("ISSUE_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        print("No event path found. Running locally?")
        return
        
    with open(event_path, "r") as f:
        event = json.load(f)
        
    issue = event.get("issue", {})
    body = issue.get("body", "")
    title = issue.get("title", "")
    
    # 2. Поиск картинок (поддержка Markdown, HTML и сырых ссылок GitHub)
    img_urls = []
    # Markdown
    img_urls.extend(re.findall(r'!\[.*?\]\((.*?)\)', body))
    # HTML
    img_urls.extend(re.findall(r'<img[^>]+src=["\'](.*?)["\']', body))
    # Raw GitHub Asset URLs (just in case they are naked)
    img_urls.extend(re.findall(r'(https://github\.com/[^/\s]+/[^/\s]+/assets/\d+/[a-zA-Z0-9-]+)', body))
    
    # Remove duplicates
    img_urls = list(set(img_urls))
    
    # Очищаем текст от ссылок
    clean_body = re.sub(r'!\[.*?\]\(.*?\)', '', body)
    clean_body = re.sub(r'<img.*?>', '', clean_body)
    clean_body = re.sub(r'https://github\.com[^\s]+', '', clean_body).strip()
    
    # Настройка Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found, exiting.")
        return
        
    client = genai.Client(api_key=api_key)
    
    # 3. Перевод текста на 3 языка
    translation_prompt = f"""
    You are a professional translator. Translate the following household problem into English (en), Montenegrin (me), and Ukrainian (ua).
    Combine the Title and Description into a single, natural, story-telling paragraph.
    DO NOT include the words "Title:" or "Description:" in your output. Just the natural text.
    
    Title: {title}
    Description: {clean_body}
    
    Output exactly in this JSON format:
    {{
        "en": "translated natural text",
        "me": "translated natural text",
        "ua": "translated natural text"
    }}
    """
    
    response = client.models.generate_content(
        model='gemini-flash-lite-latest',
        contents=translation_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    
    translations = json.loads(response.text)
    
    # 4. Генерация картинок (Акварель с помощью Imagen)
    downloaded_images = []
    os.makedirs("assets", exist_ok=True)
    
    for i, img_url in enumerate(img_urls):
        try:
            print(f"Processing image {i+1}...")
            
            img_data = requests.get(img_url).content
            pil_image = Image.open(BytesIO(img_data))
            
            analysis_prompt = f"Analyze this image of a household problem '{title}'. Write a highly detailed prompt for an AI image generator (like Imagen 3) to recreate this exact scene as a 'vibrant watercolor painting'. Add exaggerated visual damage like sparks, smoke, or water leaks depending on the context, or emphasize the problem (e.g. huge ants). Only output the raw prompt string, nothing else."
            
            analysis_response = client.models.generate_content(
                model='gemini-flash-lite-latest',
                contents=[pil_image, analysis_prompt]
            )
            
            imagen_prompt = analysis_response.text.strip()
            print(f"Imagen Prompt: {imagen_prompt}")
            
            # Список моделей для попытки генерации
            image_models_to_try = [
                'imagen-4.0-generate-001',
                'imagen-4.0-fast-generate-001',
                'gemini-3.1-flash-image',
                'gemini-2.5-flash-image'
            ]
            
            result = None
            for attempt in range(2): # 2 глобальные попытки (с паузой)
                for img_model in image_models_to_try:
                    try:
                        print(f"Trying image model: {img_model} (Attempt {attempt+1})")
                        result = client.models.generate_images(
                            model=img_model,
                            prompt=imagen_prompt,
                            config=types.GenerateImagesConfig(
                                number_of_images=1,
                                output_mime_type="image/png",
                                aspect_ratio="1:1"
                            )
                        )
                        break # Успех! Выходим из цикла моделей
                    except Exception as e:
                        print(f"Failed with {img_model}: {e}")
                        
                if result:
                    break # Успех! Выходим из глобального цикла попыток
                else:
                    print("All models failed in this attempt. Sleeping for 15 seconds before retry...")
                    time.sleep(15)
                    
            if not result:
                raise Exception("All models and retries failed to generate an image.")
            
            safe_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
            if not safe_title: safe_title = "issue"
            filename = f"{safe_title}_{int(time.time())}_{i}.png"
            filepath = os.path.join("assets", filename)
            
            generated_image = result.generated_images[0]
            with open(filepath, "wb") as f:
                f.write(generated_image.image.image_bytes)
                
            downloaded_images.append(filepath)
        except Exception as e:
            print(f"Error processing image {i+1} with AI: {e}")
            print("Falling back to original image...")
            # Save original image instead
            safe_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
            if not safe_title: safe_title = "issue"
            filename = f"{safe_title}_{int(time.time())}_{i}_original.png"
            filepath = os.path.join("assets", filename)
            with open(filepath, "wb") as f:
                f.write(img_data)
            downloaded_images.append(filepath)
            
    if not downloaded_images:
        print("No images processed. Falling back to default.")
        
    # 5. Обновляем data.js (Словарь переводов)
    issue_id = f"issue_{int(time.time())}"
    with open("data.js", "r") as f:
        data_js = f.read()
        
    for lang in ["en", "me", "ua"]:
        lang_marker = f"'{lang}': {{"
        # Escape single quotes and newlines for JS string
        safe_text = translations.get(lang, '').replace("'", "\\'").replace("\n", " ")
        replacement = f"'{lang}': {{\n        '{issue_id}': '{safe_text}',"
        data_js = data_js.replace(lang_marker, replacement)
        
    with open("data.js", "w") as f:
        f.write(data_js)
        
    # 6. Обновляем index.html
    with open("index.html", "r") as f:
        html = f.read()
        
    img_tags = ""
    if downloaded_images:
        img_tags = "\n                    ".join([f'<img src="{img}" alt="{title}" class="carousel-img {"active" if idx==0 else ""}">' for idx, img in enumerate(downloaded_images)])
    else:
        img_tags = f'<img src="assets/hall_empty.png" alt="Fallback" class="carousel-img active">'
    
    new_section = f"""
        <!-- Scene: {title} -->
        <section class="scene scene-problem left-align" id="scene-{issue_id}">
            <div class="torn-image-container mask-frame">
                <div class="ink-reveal carousel-container">
                    {img_tags}
                </div>
            </div>
            <div class="text-panel problem-text">
                <p data-i18n="{issue_id}">{translations.get('en', '').replace("'", "&apos;")}</p>
            </div>
        </section>
    """
    
    insert_target = "<!-- Scene 5: Final Sad Scene -->"
    html = html.replace(insert_target, new_section + "\n        " + insert_target)
    
    with open("index.html", "w") as f:
        f.write(html)
        
    print("Issue processed successfully with Gemini API!")

if __name__ == "__main__":
    main()
