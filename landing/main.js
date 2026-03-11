/**
 * Revna — Awwwards-Level Interactions
 * GSAP + Lenis + Custom Animations
 */

// ═══════════════════════════════════════════════════
// Lenis Smooth Scroll
// ═══════════════════════════════════════════════════

const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  orientation: 'vertical',
  smoothWheel: true,
});

function raf(time) {
  lenis.raf(time);
  requestAnimationFrame(raf);
}
requestAnimationFrame(raf);

// Connect Lenis to GSAP ScrollTrigger
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => lenis.raf(time * 1000));
gsap.ticker.lagSmoothing(0);

// ═══════════════════════════════════════════════════
// Custom Cursor
// ═══════════════════════════════════════════════════

const cursor = document.querySelector('.cursor');
const cursorDot = document.querySelector('.cursor-dot');
const cursorRing = document.querySelector('.cursor-ring');

if (cursor && window.matchMedia('(pointer: fine)').matches) {
  let mouseX = 0, mouseY = 0;
  let ringX = 0, ringY = 0;

  document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
  });

  // Smooth cursor ring follow
  function animateCursor() {
    ringX += (mouseX - ringX) * 0.15;
    ringY += (mouseY - ringY) * 0.15;

    cursorDot.style.left = mouseX + 'px';
    cursorDot.style.top = mouseY + 'px';
    cursorRing.style.left = ringX + 'px';
    cursorRing.style.top = ringY + 'px';

    requestAnimationFrame(animateCursor);
  }
  animateCursor();

  // Hover states
  const hoverElements = document.querySelectorAll('a, button, .testimonial-card, .how-card, .quick-btn, .suggestion-card, input');
  hoverElements.forEach(el => {
    el.addEventListener('mouseenter', () => cursor.classList.add('hover'));
    el.addEventListener('mouseleave', () => cursor.classList.remove('hover'));
  });

  // Click state
  document.addEventListener('mousedown', () => cursor.classList.add('clicking'));
  document.addEventListener('mouseup', () => cursor.classList.remove('clicking'));
}

// ═══════════════════════════════════════════════════
// GSAP Animations
// ═══════════════════════════════════════════════════

gsap.registerPlugin(ScrollTrigger);

// Split text animation for hero title
const splitTextElements = document.querySelectorAll('[data-animate="split"]');
splitTextElements.forEach(el => {
  const lines = el.querySelectorAll('.line');
  lines.forEach(line => {
    const content = line.innerHTML;
    line.innerHTML = `<span class="line-inner">${content}</span>`;
  });

  gsap.to(el.querySelectorAll('.line-inner'), {
    y: 0,
    duration: 1,
    ease: 'power3.out',
    stagger: 0.15,
    delay: 0.3,
    onComplete: () => el.classList.add('animated')
  });
});

// Hero badge animation
gsap.from('.hero-badge', {
  y: 30,
  opacity: 0,
  duration: 0.8,
  ease: 'power3.out',
  delay: 0.1
});

// Hero subtitle
gsap.from('.hero-sub', {
  y: 40,
  opacity: 0,
  duration: 0.8,
  ease: 'power3.out',
  delay: 0.6
});

// Waitlist form
gsap.from('.hero .waitlist-form', {
  y: 40,
  opacity: 0,
  duration: 0.8,
  ease: 'power3.out',
  delay: 0.8
});

// Hero proof
gsap.from('.hero-proof', {
  y: 30,
  opacity: 0,
  duration: 0.8,
  ease: 'power3.out',
  delay: 1
});

// Phone entrance with 3D
gsap.from('.iphone-wrapper', {
  y: 100,
  opacity: 0,
  rotateY: -30,
  rotateX: 10,
  duration: 1.2,
  ease: 'power3.out',
  delay: 0.5
});

// ═══════════════════════════════════════════════════
// Scroll-triggered animations
// ═══════════════════════════════════════════════════

// Logos section
gsap.from('.logos-label', {
  scrollTrigger: {
    trigger: '.logos',
    start: 'top 80%',
  },
  y: 30,
  opacity: 0,
  duration: 0.6
});

gsap.from('.logo-item, .logo-more', {
  scrollTrigger: {
    trigger: '.logos',
    start: 'top 80%',
  },
  y: 30,
  opacity: 0,
  duration: 0.6,
  stagger: 0.1,
  delay: 0.2
});

// Stats counter animation
const statNums = document.querySelectorAll('.stat-num[data-count]');
statNums.forEach(stat => {
  const target = parseInt(stat.dataset.count, 10);

  ScrollTrigger.create({
    trigger: stat,
    start: 'top 80%',
    once: true,
    onEnter: () => {
      gsap.to(stat, {
        innerHTML: target,
        duration: 1.5,
        ease: 'power2.out',
        snap: { innerHTML: 1 },
        onUpdate: function() {
          stat.innerHTML = Math.round(this.targets()[0].innerHTML);
        }
      });
    }
  });
});

// Stats blocks
gsap.from('.stat-block', {
  scrollTrigger: {
    trigger: '.stats',
    start: 'top 70%',
  },
  y: 60,
  opacity: 0,
  duration: 0.8,
  stagger: 0.15,
  ease: 'power3.out'
});

// Section headers
document.querySelectorAll('.section-header').forEach(header => {
  gsap.from(header.querySelector('.section-tag'), {
    scrollTrigger: {
      trigger: header,
      start: 'top 80%',
    },
    y: 20,
    opacity: 0,
    duration: 0.6
  });

  gsap.from(header.querySelector('.section-title'), {
    scrollTrigger: {
      trigger: header,
      start: 'top 80%',
    },
    y: 40,
    opacity: 0,
    duration: 0.8,
    delay: 0.1
  });
});

// How cards with stagger
gsap.from('.how-card', {
  scrollTrigger: {
    trigger: '.how-grid',
    start: 'top 75%',
  },
  y: 80,
  opacity: 0,
  duration: 0.8,
  stagger: 0.2,
  ease: 'power3.out'
});

// Feature rows with alternating animation
document.querySelectorAll('.feature-row').forEach((row, i) => {
  const isReverse = row.classList.contains('reverse');

  gsap.from(row.querySelector('.feature-text'), {
    scrollTrigger: {
      trigger: row,
      start: 'top 75%',
    },
    x: isReverse ? 60 : -60,
    opacity: 0,
    duration: 0.8,
    ease: 'power3.out'
  });

  gsap.from(row.querySelector('.feature-visual'), {
    scrollTrigger: {
      trigger: row,
      start: 'top 75%',
    },
    x: isReverse ? -60 : 60,
    opacity: 0,
    duration: 0.8,
    delay: 0.2,
    ease: 'power3.out'
  });
});

// Testimonial cards
gsap.from('.testimonial-card', {
  scrollTrigger: {
    trigger: '.testimonials-grid',
    start: 'top 75%',
  },
  y: 80,
  opacity: 0,
  duration: 0.8,
  stagger: 0.15,
  ease: 'power3.out'
});

// CTA section
gsap.from('.cta-origin', {
  scrollTrigger: {
    trigger: '.cta',
    start: 'top 70%',
  },
  y: 40,
  opacity: 0,
  duration: 0.8
});

gsap.from('.cta-title', {
  scrollTrigger: {
    trigger: '.cta',
    start: 'top 70%',
  },
  y: 50,
  opacity: 0,
  duration: 0.8,
  delay: 0.2
});

gsap.from('.cta .waitlist-form', {
  scrollTrigger: {
    trigger: '.cta',
    start: 'top 70%',
  },
  y: 40,
  opacity: 0,
  duration: 0.8,
  delay: 0.4
});

// ═══════════════════════════════════════════════════
// Parallax Effects
// ═══════════════════════════════════════════════════

// Hero orbs parallax
gsap.to('.hero-orb-1', {
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: 1
  },
  y: -150,
  ease: 'none'
});

gsap.to('.hero-orb-2', {
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: 1
  },
  y: -100,
  ease: 'none'
});

gsap.to('.hero-orb-3', {
  scrollTrigger: {
    trigger: '.hero',
    start: 'top top',
    end: 'bottom top',
    scrub: 1
  },
  y: -200,
  ease: 'none'
});

// ═══════════════════════════════════════════════════
// Magnetic Buttons
// ═══════════════════════════════════════════════════

const magneticElements = document.querySelectorAll('.nav-cta, .waitlist-form button');
magneticElements.forEach(el => {
  el.classList.add('magnetic');

  el.addEventListener('mousemove', (e) => {
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;

    gsap.to(el, {
      x: x * 0.3,
      y: y * 0.3,
      duration: 0.3,
      ease: 'power2.out'
    });
  });

  el.addEventListener('mouseleave', () => {
    gsap.to(el, {
      x: 0,
      y: 0,
      duration: 0.5,
      ease: 'elastic.out(1, 0.5)'
    });
  });
});

// ═══════════════════════════════════════════════════
// Nav scroll effect
// ═══════════════════════════════════════════════════

const nav = document.querySelector('.nav');
ScrollTrigger.create({
  start: 50,
  onUpdate: (self) => {
    if (self.scroll() > 50) {
      nav.style.boxShadow = '0 1px 20px rgba(26, 29, 46, 0.08)';
      nav.style.background = 'rgba(251, 248, 244, 0.95)';
    } else {
      nav.style.boxShadow = 'none';
      nav.style.background = 'rgba(251, 248, 244, 0.85)';
    }
  }
});

// ═══════════════════════════════════════════════════
// 3D iPhone Mouse Tracking
// ═══════════════════════════════════════════════════

const iphoneWrapper = document.querySelector('.iphone-wrapper');
const heroPhone = document.querySelector('.hero-phone');
const iphoneScreen = document.querySelector('.iphone-screen');

if (iphoneWrapper && heroPhone) {
  let isHovering = false;
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
    targetRotateX = 2;
    targetRotateY = -8;
    gsap.to(iphoneWrapper, {
      rotateX: 2,
      rotateY: -8,
      duration: 0.8,
      ease: 'power3.out',
      onComplete: () => {
        iphoneWrapper.style.animation = 'float-phone 6s ease-in-out infinite';
      }
    });
  });

  heroPhone.addEventListener('mousemove', (e) => {
    if (!isHovering) return;

    const rect = heroPhone.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const mouseX = (e.clientX - centerX) / (rect.width / 2);
    const mouseY = (e.clientY - centerY) / (rect.height / 2);

    targetRotateY = mouseX * 20;
    targetRotateX = -mouseY * 15;

    if (iphoneScreen) {
      const glareX = 50 + mouseX * 30;
      const glareY = 50 + mouseY * 30;
      iphoneScreen.style.setProperty('--glare-x', `${glareX}%`);
      iphoneScreen.style.setProperty('--glare-y', `${glareY}%`);
    }
  });

  function animatePhone() {
    if (isHovering) {
      currentRotateX += (targetRotateX - currentRotateX) * 0.1;
      currentRotateY += (targetRotateY - currentRotateY) * 0.1;
      iphoneWrapper.style.transform = `rotateY(${currentRotateY}deg) rotateX(${currentRotateX}deg)`;
    }
    requestAnimationFrame(animatePhone);
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
      setTimeout(() => {
        messageIndex = 0;
        chat.innerHTML = '';
        showNextMessage();
      }, 4000);
      return;
    }

    const msg = chatMessages[messageIndex];

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
      setTimeout(() => {
        const bubble = createMessage(msg);
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;
        messageIndex++;
        setTimeout(showNextMessage, msg.delay);
      }, 300);
    }
  }

  setTimeout(showNextMessage, 1500);
}

runChatAnimation();

// ═══════════════════════════════════════════════════
// Form interactions
// ═══════════════════════════════════════════════════

document.querySelectorAll('.waitlist-form').forEach((form) => {
  const button = form.querySelector('button[type="submit"]');
  const input = form.querySelector('input[type="email"]');
  const originalButtonText = button ? button.textContent : '';

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!input.value || !input.validity.valid) {
      input.classList.add('error');
      gsap.to(input, {
        x: [-6, 6, -6, 6, 0],
        duration: 0.4,
        ease: 'power2.out'
      });
      input.focus();
      setTimeout(() => input.classList.remove('error'), 1000);
      return;
    }

    button.disabled = true;
    button.innerHTML = '<span class="btn-spinner"></span>';
    button.classList.add('loading');

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        button.classList.remove('loading');
        button.classList.add('success');
        button.innerHTML = '✓ Inscrit !';
        input.value = '';
        input.disabled = true;

        const successMsg = document.createElement('div');
        successMsg.className = 'form-success';
        successMsg.innerHTML = '🎉 Bienvenue dans la beta ! Check tes emails.';
        form.appendChild(successMsg);

        gsap.from(successMsg, {
          y: -10,
          opacity: 0,
          duration: 0.5,
          ease: 'power3.out',
          onComplete: () => successMsg.classList.add('visible')
        });
      } else {
        throw new Error('Erreur serveur');
      }
    } catch (error) {
      button.classList.remove('loading');
      button.classList.add('error');
      button.textContent = 'Erreur, réessaie';

      setTimeout(() => {
        button.classList.remove('error');
        button.disabled = false;
        button.textContent = originalButtonText;
      }, 3000);
    }
  });
});

// ═══════════════════════════════════════════════════
// Training Bars Animation
// ═══════════════════════════════════════════════════

const trainingBars = document.querySelector('.training-bars');
if (trainingBars) {
  ScrollTrigger.create({
    trigger: trainingBars,
    start: 'top 80%',
    once: true,
    onEnter: () => {
      const bars = trainingBars.querySelectorAll('.training-bar');
      bars.forEach((bar, i) => {
        const target = parseInt(bar.dataset.target, 10);
        gsap.to(bar, {
          height: target + '%',
          duration: 0.8,
          delay: i * 0.1,
          ease: 'power3.out'
        });
      });
    }
  });
}

// ═══════════════════════════════════════════════════
// Hover effects on cards
// ═══════════════════════════════════════════════════

document.querySelectorAll('.how-card, .testimonial-card').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = (y - centerY) / 20;
    const rotateY = (centerX - x) / 20;

    gsap.to(card, {
      rotateX: rotateX,
      rotateY: rotateY,
      transformPerspective: 1000,
      duration: 0.3,
      ease: 'power2.out'
    });
  });

  card.addEventListener('mouseleave', () => {
    gsap.to(card, {
      rotateX: 0,
      rotateY: 0,
      duration: 0.5,
      ease: 'power3.out'
    });
  });
});

// ═══════════════════════════════════════════════════
// Reduced Motion
// ═══════════════════════════════════════════════════

if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  lenis.destroy();
  gsap.globalTimeline.clear();
  ScrollTrigger.getAll().forEach(t => t.kill());
}
