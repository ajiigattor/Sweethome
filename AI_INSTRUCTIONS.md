# Sweet Home Project - AI Assistant Instructions

Hello, fellow AI Assistant! If the user asks you to add a new "problem" or "photo" to this project, you MUST follow these strict rules to maintain the site's unique aesthetic.

## 1. Image Generation (The "Sweet Home" Style)
- **Prompt Base:** ALWAYS use a prompt that starts with: `"Apply a vibrant watercolor filter to this exact image."`
- **Damage Exaggeration:** If the image shows a broken appliance or problem (e.g., a broken AC, a leak, a burnt wire), you MUST prompt the AI image generator to explicitly draw the damage (e.g., add water puddles, dark smoke, electrical sparks, cracked glass).
- **Save Location:** Save generated images to the `assets/` directory.

## 2. HTML Structure
Insert the new problem `section` BEFORE the Final Sad Scene (`#scene-final`).
Alternate the layout alignment using `.left-align` and `.right-align` classes on the `<section>` tag.

Use this EXACT HTML snippet for a new problem:

```html
<section class="scene scene-problem left-align"> <!-- or right-align -->
    <div class="torn-image-container mask-frame">
        <div class="ink-reveal carousel-container">
            <!-- Add images here. If there are multiple, the JS will automatically crossfade them! -->
            <img src="assets/your_new_image1.png" alt="Problem Description" class="carousel-img active">
            <!-- <img src="assets/your_new_image2.png" alt="Problem Description" class="carousel-img"> -->
        </div>
    </div>
    <div class="text-panel problem-text">
        <p>Your descriptive text about the problem goes here.</p>
    </div>
</section>
```

## 3. The Auto-Carousel Feature
If the user provides MULTIPLE photos of the *same* problem, generate them all in the watercolor style and put multiple `<img>` tags inside the `.carousel-container`. 
- Ensure the first `<img>` has the class `active`.
- Give the other `<img>` tags the class `carousel-img`.
- The JavaScript will automatically detect them and create a crossfade slideshow!

## 4. No SVG Masks
DO NOT use SVG `<clipPath>` or `<mask id="...">` inside the HTML for the torn edges. The torn edges are generated perfectly via a JavaScript `clip-path` math algorithm located in `app.js`.

Follow these rules, commit to `develop`, push, and the user will be happy!
