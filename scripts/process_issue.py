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
    body = issue.get("body") or ""
    title = issue.get("title") or ""
    
    # Очищаем текст от ссылок
    clean_body = re.sub(r'!\[.*?\]\(.*?\)', '', body)
    clean_body = re.sub(r'<img.*?>', '', clean_body)
    clean_body = re.sub(r'https://github\.com[^\s]+', '', clean_body).strip()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found, exiting.")
        return
        
    client = genai.Client(api_key=api_key)
    
    # 2. SMART INTENT ROUTER (ADD vs REMOVE)
    try:
        with open("data.js", "r") as f:
            data_js_content = f.read()
    except Exception as e:
        data_js_content = "No data.js found"
        
    intent_prompt = f"""
    You are an intelligent router for a website's issue tracker. A user has submitted a GitHub issue.
    Read the issue title and body to determine the intent. There are 3 possible actions: ADD, REMOVE, FIX.
    
    Issue Title: {title}
    Issue Body: {clean_body}
    
    Current problems on the website (from data.js):
    {data_js_content}
    
    - If the user is reporting a NEW problem, return exactly this JSON:
      {{"action": "ADD"}}
      
    - If the user is saying a problem was RESOLVED, FIXED, or "починили" (and they want to leave a nice "fixed" mark on it), figure out WHICH issue ID they mean from data.js.
      Return exactly this JSON:
      {{"action": "FIX", "issue_id": "the_found_id"}}
      
    - If the user is explicitly asking to DELETE or REMOVE a problem completely (e.g. "удали", "ошибка", "убери совсем"), figure out WHICH issue ID they mean.
      Return exactly this JSON:
      {{"action": "REMOVE", "issue_id": "the_found_id"}}
    """
    
    print("Checking intent (ADD/REMOVE)...")
    try:
        intent_response = client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=intent_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        intent_data = json.loads(intent_response.text)
        action = intent_data.get("action", "ADD")
    except Exception as e:
        print(f"Failed to parse intent: {e}. Defaulting to ADD.")
        action = "ADD"
        
    if action == "REMOVE":
        issue_id_to_remove = intent_data.get("issue_id")
        if not issue_id_to_remove:
            print("Action was REMOVE but no issue_id was provided. Defaulting to ADD.")
        else:
            print(f"Intent classified as REMOVE for issue ID: {issue_id_to_remove}")
            # Remove from index.html
            with open("index.html", "r") as f:
                html = f.read()
            html = re.sub(rf'\s*<!-- Scene:[^>]*?-->\s*<section class="scene[^>]*id="scene-{issue_id_to_remove}".*?</section>', '', html, flags=re.DOTALL)
            with open("index.html", "w") as f:
                f.write(html)
                
            # Remove from data.js
            with open("data.js", "r") as f:
                djs = f.read()
            djs = re.sub(rf"\s*'{issue_id_to_remove}':\s*'.*?',", "", djs)
            with open("data.js", "w") as f:
                f.write(djs)
                
            # Cache busting
            with open("index.html", "r") as f:
                html = f.read()
            html = re.sub(r'data\.js\?v=\d+', f'data.js?v={int(time.time())}', html)
            with open("index.html", "w") as f:
                f.write(html)
                
            print("Successfully removed the issue from index.html and data.js!")
            return # Мы завершаем работу, картинки генерировать не нужно

    elif action == "FIX":
        issue_id_to_fix = intent_data.get("issue_id")
        if not issue_id_to_fix:
            print("Action was FIX but no issue_id was provided. Defaulting to ADD.")
            action = "ADD"
        else:
            print(f"Intent classified as FIX for issue ID: {issue_id_to_fix}")
            with open("index.html", "r") as f:
                html = f.read()
                
            # Добавляем класс resolved
            section_pattern = rf'(<section class="scene scene-problem[^"]*)" id="scene-{issue_id_to_fix}">'
            html = re.sub(section_pattern, r'\1 resolved" id="scene-' + issue_id_to_fix + '">', html)
            
            # Вставляем HTML ленточки
            ribbon_html = '\n                <div class="fixed-ribbon-container"><div class="fixed-ribbon" data-i18n="fixed_label">FIXED</div></div>'
            ribbon_pattern = rf'(id="scene-{issue_id_to_fix}">\s*<div class="torn-image-container mask-frame">)'
            html = re.sub(ribbon_pattern, r'\1' + ribbon_html, html)
            
            # Cache busting
            html = re.sub(r'data\.js\?v=\d+', f'data.js?v={int(time.time())}', html)
            
            with open("index.html", "w") as f:
                f.write(html)
            
            print("Successfully marked the issue as FIXED!")
            return

    print("Intent classified as ADD. Proceeding with generation...")
    
    # 3. Поиск картинок (поддержка Markdown, HTML и сырых ссылок GitHub)
    img_urls = []
    img_urls.extend(re.findall(r'!\[.*?\]\((.*?)\)', body))
    img_urls.extend(re.findall(r'<img[^>]+src=["\'](.*?)["\']', body))
    img_urls.extend(re.findall(r'(https://github\.com/[^/\s]+/[^/\s]+/assets/\d+/[a-zA-Z0-9-]+)', body))
    img_urls = list(set(img_urls))
    
    # 4. Перевод текста на 3 языка
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
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    translations = json.loads(response.text)
    
    # 5. Генерация картинок (Акварель с помощью Gemini Image)
    downloaded_images = []
    os.makedirs("assets", exist_ok=True)
    
    for i, img_url in enumerate(img_urls):
        try:
            print(f"Processing image {i+1}...")
            
            img_data = requests.get(img_url).content
            pil_image = Image.open(BytesIO(img_data))
            
            analysis_prompt = f"Analyze this image of a household problem '{title}'. Write a highly detailed prompt for an AI image generator to recreate this exact scene as a 'vibrant watercolor painting'. Make sure the layout and the main objects closely resemble the original image. Add exaggerated visual damage like sparks, smoke, or cracks depending on the context to emphasize the problem. Only output the raw prompt string, nothing else."
            
            analysis_response = client.models.generate_content(
                model='gemini-flash-lite-latest',
                contents=[pil_image, analysis_prompt]
            )
            
            imagen_prompt = analysis_response.text.strip()
            print(f"Imagen Prompt: {imagen_prompt}")
            
            image_models_to_try = [
                'gemini-2.5-flash-image',
                'gemini-3.1-flash-image',
                'gemini-3-pro-image'
            ]
            
            result = None
            image_bytes = None
            
            for attempt in range(2): 
                for img_model in image_models_to_try:
                    try:
                        print(f"Trying image model: {img_model} (Attempt {attempt+1})")
                        result = client.models.generate_content(
                            model=img_model,
                            contents=imagen_prompt,
                        )
                        has_image = False
                        if result.candidates and result.candidates[0].content.parts:
                            for part in result.candidates[0].content.parts:
                                if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                                    has_image = True
                                    image_bytes = part.inline_data.data
                                    break
                        if has_image:
                            break 
                        else:
                            result = None
                            print(f"Failed with {img_model}: No image in response")
                    except Exception as e:
                        print(f"Failed with {img_model}: {e}")
                        result = None
                        
                if result:
                    break
                else:
                    print("All models failed. Sleeping for 15s...")
                    time.sleep(15)
                    
            if not result or not image_bytes:
                raise Exception("All image generation models failed.")
            
            safe_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
            if not safe_title: safe_title = "issue"
            filename = f"{safe_title}_{int(time.time())}_{i}.png"
            filepath = os.path.join("assets", filename)
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
                
            downloaded_images.append(filepath)
        except Exception as e:
            print(f"Error processing image {i+1} with AI: {e}")
            print("Falling back to original image...")
            safe_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
            if not safe_title: safe_title = "issue"
            filename = f"{safe_title}_{int(time.time())}_{i}_original.png"
            filepath = os.path.join("assets", filename)
            with open(filepath, "wb") as f:
                f.write(img_data)
            downloaded_images.append(filepath)
            
    if not downloaded_images:
        print("No images processed. Falling back to default.")
        
    # 6. Обновляем data.js
    issue_id = f"issue_{int(time.time())}"
    with open("data.js", "r") as f:
        data_js = f.read()
        
    for lang in ["en", "me", "ua"]:
        lang_marker = f"'{lang}': {{"
        safe_text = translations.get(lang, '').replace("'", "\\'").replace("\n", " ")
        replacement = f"'{lang}': {{\n        '{issue_id}': '{safe_text}',"
        data_js = data_js.replace(lang_marker, replacement)
        
    with open("data.js", "w") as f:
        f.write(data_js)
        
    # 7. Обновляем index.html
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
    
    # 8. Cache busting для data.js
    html = re.sub(r'data\.js\?v=\d+', f'data.js?v={int(time.time())}', html)
    
    with open("index.html", "w") as f:
        f.write(html)
        
    print("Issue processed successfully with Gemini API!")

if __name__ == "__main__":
    main()
