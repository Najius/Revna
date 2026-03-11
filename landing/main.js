/**
 * Revna v8 — Landing Page Interactions
 * Scroll reveals, animated counters, training bars
 */

// ═══════════════════════════════════════════════════
// Intersection Observer — Scroll-Triggered Reveals
// ═══════════════════════════════════════════════════

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, {
  threshold: 0.1,
  rootMargin: '0px 0px -40px 0px'
});

document.querySelectorAll('.reveal').forEach((el) => {
  revealObserver.observe(el);
});

// ═══════════════════════════════════════════════════
// Animated Counters
// ═══════════════════════════════════════════════════

function easeOutExpo(t) {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

function animateCounter(element, target) {
  const duration = 1600;
  const startTime = performance.now();

  function frame(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeOutExpo(progress);
    const current = Math.round(target * eased);

    element.textContent = current;

    if (progress < 1) {
      requestAnimationFrame(frame);
    } else {
      element.textContent = target;
    }
  }

  requestAnimationFrame(frame);
}

const countObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting && !entry.target.dataset.counted) {
      entry.target.dataset.counted = 'true';
      const target = parseInt(entry.target.dataset.count, 10);
      animateCounter(entry.target, target);
    }
  });
}, { threshold: 0.3 });

document.querySelectorAll('[data-count]').forEach((el) => {
  countObserver.observe(el);
});

// ═══════════════════════════════════════════════════
// Training Bars Height Animation
// ═══════════════════════════════════════════════════

function animateTrainingBars() {
  const trainingBars = document.querySelector('.training-bars');
  if (!trainingBars || trainingBars.dataset.animated) return;
  trainingBars.dataset.animated = 'true';

  const bars = trainingBars.querySelectorAll('.training-bar');
  bars.forEach((bar, i) => {
    const target = parseInt(bar.dataset.target, 10);
    setTimeout(() => {
      bar.style.height = target + '%';
    }, i * 120);
  });
}

const trainingObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      setTimeout(animateTrainingBars, 300);
    }
  });
}, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

const trainingSection = document.querySelector('.training-bars');
if (trainingSection) {
  trainingObserver.observe(trainingSection);
}

// ═══════════════════════════════════════════════════
// Nav background on scroll
// ═══════════════════════════════════════════════════

const nav = document.querySelector('.nav');
let lastScroll = 0;

window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;
  if (scrollY > 50) {
    nav.style.boxShadow = '0 1px 12px rgba(26, 29, 46, 0.06)';
  } else {
    nav.style.boxShadow = 'none';
  }
  lastScroll = scrollY;
}, { passive: true });

// ═══════════════════════════════════════════════════
// Form interactions
// ═══════════════════════════════════════════════════

document.querySelectorAll('.waitlist-form').forEach((form) => {
  const button = form.querySelector('button[type="submit"]');
  if (button) {
    button.addEventListener('click', () => {
      button.style.pointerEvents = 'none';
      setTimeout(() => {
        button.style.pointerEvents = 'auto';
      }, 2000);
    });
  }
});

// ═══════════════════════════════════════════════════
// Initialize — handle elements already in viewport
// ═══════════════════════════════════════════════════

function initializeAnimations() {
  document.querySelectorAll('.reveal:not(.visible)').forEach((el) => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.9) {
      el.classList.add('visible');
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeAnimations);
} else {
  initializeAnimations();
}

// ═══════════════════════════════════════════════════
// Reduced Motion
// ═══════════════════════════════════════════════════

if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.querySelectorAll('.reveal').forEach((el) => {
    el.classList.add('visible');
  });
}

// ═══════════════════════════════════════════════════
// 3D iPhone Mouse Tracking
// ═══════════════════════════════════════════════════

const iphoneWrapper = document.querySelector('.iphone-wrapper');
const heroPhone = document.querySelector('.hero-phone');
const iphoneScreen = document.querySelector('.iphone-screen');

if (iphoneWrapper && heroPhone) {
  let isHovering = false;
  let animationFrame;
  let currentRotateX = 2;
  let currentRotateY = -8;
  let targetRotateX = 2;
  let targetRotateY = -8;

  heroPhone.addEventListener('mouseenter', () => {
    isHovering = true;
    iphoneWrapper.style.animation = 'none';
  });

  heroPhone.addEventListener('mouseleave', () => {
    isHovering = false;
    // Smoothly return to default position
    targetRotateX = 2;
    targetRotateY = -8;
    iphoneWrapper.style.animation = 'float-phone 6s ease-in-out infinite';
  });

  heroPhone.addEventListener('mousemove', (e) => {
    if (!isHovering) return;

    const rect = heroPhone.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Calculate mouse position relative to center (-1 to 1)
    const mouseX = (e.clientX - centerX) / (rect.width / 2);
    const mouseY = (e.clientY - centerY) / (rect.height / 2);

    // Set target rotation (max ±20 degrees)
    targetRotateY = mouseX * 20;
    targetRotateX = -mouseY * 15;

    // Update glare position
    if (iphoneScreen) {
      const glareX = 50 + mouseX * 30;
      const glareY = 50 + mouseY * 30;
      iphoneScreen.style.setProperty('--glare-x', `${glareX}%`);
      iphoneScreen.style.setProperty('--glare-y', `${glareY}%`);
    }
  });

  // Smooth animation loop
  function animatePhone() {
    // Lerp towards target
    currentRotateX += (targetRotateX - currentRotateX) * 0.1;
    currentRotateY += (targetRotateY - currentRotateY) * 0.1;

    if (isHovering) {
      iphoneWrapper.style.transform = `rotateY(${currentRotateY}deg) rotateX(${currentRotateX}deg)`;
    }

    animationFrame = requestAnimationFrame(animatePhone);
  }

  animatePhone();
}

// ═══════════════════════════════════════════════════
// Interactive Chat Simulation
// ═══════════════════════════════════════════════════

const chatMessages = [
  {
    type: 'bot',
    class: 'activity-alert',
    content: `
      <div class="activity-header">
        <span class="activity-icon">🏃</span>
        <span class="activity-badge">Nouvelle activité</span>
      </div>
      <p class="activity-title">Course — 8,4 km</p>
      <div class="activity-metrics">
        <div class="metric"><span class="metric-val">42:18</span><span class="metric-label">Durée</span></div>
        <div class="metric"><span class="metric-val">152</span><span class="metric-label">FC moy</span></div>
        <div class="metric"><span class="metric-val">5:02</span><span class="metric-label">/km</span></div>
      </div>
    `,
    time: '19:32',
    delay: 600
  },
  {
    type: 'bot',
    content: `
      <p class="section-label">📊 Ce qu'il faut retenir</p>
      <ul class="insight-list">
        <li><strong>Bonne allure</strong> — zone 3 maîtrisée</li>
        <li><strong>Cadence stable</strong> — 174 spm</li>
        <li><strong>Charge +12%</strong> cette semaine</li>
      </ul>
    `,
    time: '19:32',
    delay: 1200
  },
  {
    type: 'bot',
    content: `
      <p class="section-label">💡 Point d'amélioration</p>
      <p>Ta FC monte vite dans les côtes. Travaille des intervalles en dénivelé pour progresser.</p>
    `,
    time: '19:32',
    delay: 1000
  },
  {
    type: 'user',
    content: `<p>Nickel ! Je fais quoi demain ?</p>`,
    time: '19:34',
    delay: 1800
  },
  {
    type: 'bot',
    content: `
      <p>Ton <strong>Body Battery est à 35</strong> et ta VFC est 15% sous ta baseline. Je te conseille :</p>
      <div class="suggestion-cards">
        <div class="suggestion-card">
          <span class="suggestion-icon">🧘</span>
          <span>Yoga 20min</span>
        </div>
        <div class="suggestion-card">
          <span class="suggestion-icon">🚶</span>
          <span>Marche 30min</span>
        </div>
      </div>
    `,
    time: '19:34',
    delay: 1400
  },
  {
    type: 'user',
    content: `<p>Et si je veux courir quand même ?</p>`,
    time: '19:35',
    delay: 1600
  },
  {
    type: 'bot',
    content: `
      <p>OK, mais <strong>zone 2 max</strong> — 30 min pas plus.</p>
      <p class="tip">Je surveillerai ta FC et t'alerterai si tu dépasses.</p>
    `,
    time: '19:35',
    delay: 1200
  },
  {
    type: 'user',
    content: `<p>D'accord ! Et pour mon sommeil cette nuit ?</p>`,
    time: '19:36',
    delay: 1800
  },
  {
    type: 'bot',
    class: 'sleep-insight',
    content: `
      <p class="section-label">😴 Analyse sommeil (nuit dernière)</p>
      <div class="sleep-bars">
        <div class="sleep-stage"><span class="sleep-label">Profond</span><div class="sleep-bar-track"><div class="sleep-bar" style="width: 22%"></div></div><span class="sleep-val">1h28</span></div>
        <div class="sleep-stage"><span class="sleep-label">Léger</span><div class="sleep-bar-track"><div class="sleep-bar light" style="width: 55%"></div></div><span class="sleep-val">3h42</span></div>
        <div class="sleep-stage"><span class="sleep-label">REM</span><div class="sleep-bar-track"><div class="sleep-bar rem" style="width: 23%"></div></div><span class="sleep-val">1h32</span></div>
      </div>
      <p class="tip">Ton sommeil profond est un peu court. Évite les écrans 1h avant de dormir.</p>
    `,
    time: '19:36',
    delay: 1600
  },
  {
    type: 'user',
    content: `<p>Comment améliorer mon sommeil profond ?</p>`,
    time: '19:38',
    delay: 2000
  },
  {
    type: 'bot',
    content: `
      <p>Quelques conseils basés sur tes données :</p>
      <ul class="insight-list">
        <li><strong>Température</strong> — chambre à 18°C max</li>
        <li><strong>Régularité</strong> — couche-toi à heure fixe</li>
        <li><strong>Pas de sport</strong> après 20h</li>
        <li><strong>Caféine</strong> — stop après 14h</li>
      </ul>
    `,
    time: '19:38',
    delay: 1400
  },
  {
    type: 'user',
    content: `<p>Top, je teste ce soir !</p>`,
    time: '19:39',
    delay: 1400
  },
  {
    type: 'bot',
    content: `
      <p>Parfait ! Je comparerai ta nuit avec tes précédentes. 📊</p>
      <div class="quick-actions">
        <span class="quick-btn active">🔔 Rappel 22h</span>
        <span class="quick-btn">📖 En savoir plus</span>
      </div>
    `,
    time: '19:39',
    delay: 1200
  },
  {
    type: 'user',
    content: `<p>Merci Revna, t'es au top 🙌</p>`,
    time: '19:40',
    delay: 1600
  },
  {
    type: 'bot',
    content: `
      <p>Toujours là pour toi ! 💪</p>
      <p class="tip">Bilan matinal demain à 7h30. Bonne soirée !</p>
    `,
    time: '19:40',
    delay: 1000
  }
];

function createTypingIndicator() {
  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.innerHTML = '<span></span><span></span><span></span>';
  return typing;
}

function createMessage(msg) {
  const bubble = document.createElement('div');
  bubble.className = `bubble ${msg.type === 'bot' ? 'bot' : 'user'} ${msg.class || ''} chat-animate`;
  bubble.innerHTML = `${msg.content}<span class="time">${msg.time}</span>`;
  return bubble;
}

function runChatAnimation() {
  const chat = document.getElementById('hero-chat');
  if (!chat) return;

  let messageIndex = 0;
  chat.innerHTML = '';

  function showNextMessage() {
    if (messageIndex >= chatMessages.length) {
      // Reset and loop after a pause
      setTimeout(() => {
        messageIndex = 0;
        chat.innerHTML = '';
        showNextMessage();
      }, 4000);
      return;
    }

    const msg = chatMessages[messageIndex];

    // Show typing indicator for bot messages
    if (msg.type === 'bot') {
      const typing = createTypingIndicator();
      chat.appendChild(typing);
      chat.scrollTop = chat.scrollHeight;

      setTimeout(() => {
        typing.remove();
        const bubble = createMessage(msg);
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;
        messageIndex++;
        setTimeout(showNextMessage, msg.delay);
      }, 800 + Math.random() * 400);
    } else {
      // User messages appear faster
      setTimeout(() => {
        const bubble = createMessage(msg);
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;
        messageIndex++;
        setTimeout(showNextMessage, msg.delay);
      }, 300);
    }
  }

  // Start the animation
  setTimeout(showNextMessage, 1000);
}

// Initialize chat animation when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', runChatAnimation);
} else {
  runChatAnimation();
}
