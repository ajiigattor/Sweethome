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

    // Splash Screen & Audio
    const montenegro = document.getElementById("montenegro-tag");
    const sweetHome = document.getElementById("sweet-home-logo");
    const overlay = document.getElementById("splash-overlay");
    const startBtn = document.getElementById("start-button");
    const bgMusic = document.getElementById("bg-music");
    const muteBtn = document.getElementById("mute-btn");

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

        // Start Splash Sequence
        setTimeout(() => { montenegro.classList.add("splash-center"); }, 100);
        setTimeout(() => { montenegro.classList.remove("splash-center"); montenegro.classList.add("header-pos"); }, 1000);
        setTimeout(() => { sweetHome.classList.add("splash-center"); }, 1500);
        setTimeout(() => { sweetHome.classList.remove("splash-center"); sweetHome.classList.add("header-pos"); }, 2500);
        setTimeout(() => { overlay.classList.add("hidden"); }, 3000);
    }, { once: true });

    // Scroll Logic
    const scrollContainer = document.getElementById("scroll-container");
    const scenes = document.querySelectorAll('.scene');
    const observerOptions = { root: scrollContainer, threshold: 0.5 };
    let hallTimers = [];

    const sceneObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                
                // Hall Sequence
                if (entry.target.id === 'scene-hall' && !entry.target.classList.contains('scene-hall-step-1')) {
                    // Start Hall Sequence precisely as requested
                    hallTimers.push(setTimeout(() => { entry.target.classList.add('scene-hall-step-1'); }, 1000)); // "This is our little family."
                    hallTimers.push(setTimeout(() => { entry.target.classList.add('scene-hall-step-2'); }, 2000)); // People fade in!
                    hallTimers.push(setTimeout(() => { entry.target.classList.add('scene-hall-step-3'); }, 3000)); // "We are happy to live here..."
                }
            } else {
                entry.target.classList.remove('active');
                if (entry.target.id === 'scene-hall') {
                    hallTimers.forEach(t => clearTimeout(t));
                    hallTimers = [];
                }
            }
        });
    }, observerOptions);

    scenes.forEach(scene => sceneObserver.observe(scene));
});
