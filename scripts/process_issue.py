import os
import json
import re
import requests
from openai import OpenAI
import time

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
    
    # 2. Поиск картинок в теле Issue
    # Markdown image syntax: ![alt](url)
    img_urls = re.findall(r'!\[.*?\]\((.*?)\)', body)
    
    # Очищаем текст от ссылок на картинки
    clean_body = re.sub(r'!\[.*?\]\(.*?\)', '', body).strip()
    
    # Настройка OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("No OPENAI_API_KEY found, exiting.")
        return
        
    client = OpenAI(api_key=api_key)
    
    # 3. Перевод текста на 3 языка
    translation_prompt = f"""
    Translate the following problem description into English (en), Montenegrin (me), and Ukrainian (ua).
    Output exactly in this JSON format:
    {{
        "en": "translated text",
        "me": "translated text",
        "ua": "translated text"
    }}
    
    Title: {title}
    Description: {clean_body}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": translation_prompt}],
        response_format={ "type": "json_object" }
    )
    
    translations = json.loads(response.choices[0].message.content)
    
    # 4. Генерация картинок (Акварель)
    downloaded_images = []
    
    for i, img_url in enumerate(img_urls):
        try:
            print(f"Processing image {i+1}...")
            # Шаг A: Изучаем исходное фото через GPT-4o Vision и пишем промпт для художника
            analysis_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Analyze this image of a household problem '{title}'. Write a highly detailed prompt for an AI image generator (like DALL-E 3) to recreate this exact scene as a 'vibrant watercolor painting'. Add exaggerated visual damage like sparks, smoke, or water leaks depending on the context. Only output the raw prompt string, nothing else."},
                            {"type": "image_url", "image_url": {"url": img_url}}
                        ]
                    }
                ]
            )
            dalle_prompt = analysis_response.choices[0].message.content.strip()
            print(f"DALL-E Prompt: {dalle_prompt}")
            
            # Шаг B: Рисуем новую акварельную картинку
            image_response = client.images.generate(
                model="dall-e-3",
                prompt=dalle_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            new_img_url = image_response.data[0].url
            
            # Шаг C: Скачиваем и сохраняем картинку
            img_data = requests.get(new_img_url).content
            safe_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
            if not safe_title: safe_title = "issue"
            filename = f"{safe_title}_{int(time.time())}_{i}.png"
            filepath = os.path.join("assets", filename)
            
            # Убедимся что папка assets существует
            os.makedirs("assets", exist_ok=True)
            
            with open(filepath, "wb") as f:
                f.write(img_data)
                
            downloaded_images.append(filepath)
        except Exception as e:
            print(f"Error processing image {i+1}: {e}")
            
    if not downloaded_images:
        print("No images processed. Falling back to default.")
        
    # 5. Обновляем data.js (Словарь переводов)
    issue_id = f"issue_{int(time.time())}"
    with open("data.js", "r") as f:
        data_js = f.read()
        
    for lang in ["en", "me", "ua"]:
        lang_marker = f"'{lang}': {{"
        replacement = f"'{lang}': {{\n        '{issue_id}': '{translations.get(lang, '')}',"
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
                <p data-i18n="{issue_id}">{translations.get('en', '')}</p>
            </div>
        </section>
    """
    
    insert_target = "<!-- Scene 5: Final Sad Scene -->"
    html = html.replace(insert_target, new_section + "\n        " + insert_target)
    
    with open("index.html", "w") as f:
        f.write(html)
        
    print("Issue processed successfully!")

if __name__ == "__main__":
    main()
