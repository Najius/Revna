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
    delay: 800
  },
  {
    type: 'bot',
    content: `
      <p class="section-label">📊 Ce qu'il faut retenir</p>
      <ul class="insight-list">
        <li><strong>Bonne allure</strong> — zone 3 bien tenue</li>
        <li><strong>Cadence stable</strong> — 174 spm</li>
        <li><strong>Charge +12%</strong> cette semaine</li>
      </ul>
    `,
    time: '19:32',
    delay: 1500
  },
  {
    type: 'user',
    content: `<p>Nickel ! Je fais quoi demain du coup ?</p>`,
    time: '19:34',
    delay: 2000
  },
  {
    type: 'bot',
    content: `
      <p>Ton <strong>Body Battery est à 35</strong> et ta VFC est basse. Je te conseille :</p>
      <div class="suggestion-cards">
        <div class="suggestion-card">
          <span class="suggestion-icon">🧘</span>
          <span>Yoga ou mobilité</span>
        </div>
        <div class="suggestion-card">
          <span class="suggestion-icon">🚶</span>
          <span>Marche active 30min</span>
        </div>
      </div>
    `,
    time: '19:34',
    delay: 1800
  },
  {
    type: 'user',
    content: `<p>Et si je veux quand même courir ?</p>`,
    time: '19:35',
    delay: 2200
  },
  {
    type: 'bot',
    content: `
      <p>OK, mais reste en <strong>zone 2 max</strong> — 30 min, pas plus.</p>
      <p class="tip">Je surveillerai ta FC en temps réel et t'alerterai si tu dépasses.</p>
      <div class="quick-actions">
        <span class="quick-btn active">✓ Compris</span>
        <span class="quick-btn">📅 Reporter à jeudi</span>
      </div>
    `,
    time: '19:35',
    delay: 1600
  },
  {
    type: 'user',
    content: `<p>Parfait, merci Revna 🙏</p>`,
    time: '19:36',
    delay: 1500
  },
  {
    type: 'bot',
    content: `
      <p>De rien ! Bonne récup ce soir. 😊</p>
      <p class="tip">Je t'envoie ton bilan sommeil demain matin.</p>
    `,
    time: '19:36',
    delay: 1200
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
