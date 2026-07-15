document.addEventListener("DOMContentLoaded", () => {
    
    // Torn Edges Generation (non-distorting clip-path)
    const applyTornEdges = () => {
        const containers = document.querySelectorAll('.torn-image-container');
        containers.forEach(container => {
            const points = [];
            const segments = 20;
            // Top edge
            for (let i = 0; i <= segments; i++) {
                points.push(`${(i / segments) * 100}% ${Math.random() * 2.5}%`);
            }
            // Right edge
            for (let i = 1; i <= segments; i++) {
                points.push(`${100 - Math.random() * 2.5}% ${(i / segments) * 100}%`);
            }
            // Bottom edge
            for (let i = segments - 1; i >= 0; i--) {
                points.push(`${(i / segments) * 100}% ${100 - Math.random() * 2.5}%`);
            }
            // Left edge
            for (let i = segments - 1; i > 0; i--) {
                points.push(`${Math.random() * 2.5}% ${(i / segments) * 100}%`);
            }
            container.style.clipPath = `polygon(${points.join(', ')})`;
        });
    };
    applyTornEdges();

    // Universal Auto-Carousel Logic
    const carousels = document.querySelectorAll('.carousel-container');
    carousels.forEach(container => {
        const images = container.querySelectorAll('.carousel-img');
        if (images.length > 0) {
            // First image must hold the container height
            images[0].classList.add('relative-anchor');
            
            if (images.length > 1) {
                let currentIndex = 0;
                setInterval(() => {
                    images[currentIndex].classList.remove('active');
                    currentIndex = (currentIndex + 1) % images.length;
                    images[currentIndex].classList.add('active');
                }, 3500); // 3.5 seconds crossfade
            }
        }
    });

    // Splash Screen & Audio & i18n
    const montenegro = document.getElementById("montenegro-tag");
    const sweetHome = document.getElementById("sweet-home-logo");
    const overlay = document.getElementById("splash-overlay");
    const startBtn = document.getElementById("start-button");
    const bgMusic = document.getElementById("bg-music");
    const muteBtn = document.getElementById("mute-btn");
    const langBtn = document.getElementById("lang-btn");
    const houseToggleBtn = document.getElementById("house-toggle-btn");
    const house1 = document.getElementById("house-1");
    const house2 = document.getElementById("house-2");

    // Toggle Logic
    let currentHouse = 1;
    houseToggleBtn.addEventListener("click", () => {
        if (currentHouse === 1) {
            currentHouse = 2;
            houseToggleBtn.innerText = "🏠 II";
            house1.classList.add("hidden-house");
            house1.classList.remove("active-house");
            house2.classList.remove("hidden-house");
            house2.classList.add("active-house");
        } else {
            currentHouse = 1;
            houseToggleBtn.innerText = "🏠 I";
            house2.classList.add("hidden-house");
            house2.classList.remove("active-house");
            house1.classList.remove("hidden-house");
            house1.classList.add("active-house");
        }
    });

    // Language switcher
    const langs = ['en', 'me', 'ua'];
    let currentLang = 'en';

    function updateLanguage(lang) {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (translations[lang] && translations[lang][key]) {
                el.innerText = translations[lang][key];
            }
        });
    }

    langBtn.addEventListener("click", () => {
        let currentIndex = langs.indexOf(currentLang);
        currentLang = langs[(currentIndex + 1) % langs.length];
        updateLanguage(currentLang);
    });

    muteBtn.addEventListener("click", () => {
        if (bgMusic.muted) {
            bgMusic.muted = false;
            muteBtn.innerText = "🔊";
        } else {
            bgMusic.muted = true;
            muteBtn.innerText = "🔇";
        }
    });

    overlay.addEventListener("click", () => {
        // Start music
        bgMusic.volume = 0.3; // nice background volume
        bgMusic.play();

        // Hide button immediately
        startBtn.style.animation = 'none';
        startBtn.style.display = 'none';
        muteBtn.classList.add("show");
        langBtn.classList.add("show");
        if(houseToggleBtn) houseToggleBtn.classList.add("show");

        // Start Splash Sequence
        setTimeout(() => { montenegro.classList.add("splash-center"); }, 100);
        setTimeout(() => { montenegro.classList.remove("splash-center"); montenegro.classList.add("header-pos"); }, 1000);
        setTimeout(() => { sweetHome.classList.add("splash-center"); }, 1500);
        setTimeout(() => { sweetHome.classList.remove("splash-center"); sweetHome.classList.add("header-pos"); }, 2500);
        setTimeout(() => { overlay.classList.add("hidden"); }, 3000);
    }, { once: true });

    // Scroll Logic (Dual Observers for both houses)
    let hallTimers = [];
    const observerCallback = (entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                // Hall Sequence
                if ((entry.target.id === 'scene-hall' || entry.target.id === 'scene-hall-2') && !entry.target.classList.contains('scene-hall-step-1')) {
                    hallTimers.push(setTimeout(() => { entry.target.classList.add('scene-hall-step-1'); }, 1000));
                    hallTimers.push(setTimeout(() => { entry.target.classList.add('scene-hall-step-2'); }, 2000));
                    hallTimers.push(setTimeout(() => { entry.target.classList.add('scene-hall-step-3'); }, 3000));
                }
            } else {
                entry.target.classList.remove('active');
                if (entry.target.id === 'scene-hall' || entry.target.id === 'scene-hall-2') {
                    hallTimers.forEach(t => clearTimeout(t));
                    hallTimers = [];
                }
            }
        });
    };

    const obs1 = new IntersectionObserver(observerCallback, { root: house1, threshold: 0.5 });
    const obs2 = new IntersectionObserver(observerCallback, { root: house2, threshold: 0.5 });

    house1.querySelectorAll('.scene').forEach(scene => obs1.observe(scene));
    house2.querySelectorAll('.scene').forEach(scene => obs2.observe(scene));
    
    // Auto-pause music when tab is hidden (e.g. minimizing app or locking phone)
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            bgMusic.pause();
        } else {
            // Resume only if splash screen was already clicked and user didn't mute it
            if (overlay.classList.contains("hidden") && !bgMusic.muted) {
                bgMusic.play().catch(e => console.log("Autoplay blocked:", e));
            }
        }
    });
});
