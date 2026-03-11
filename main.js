/**
 * Revna — Landing Page Interactions
 * GSAP + ScrollTrigger (native scroll)
 */

document.addEventListener('DOMContentLoaded', () => {

  // ═══════════════════════════════════════════════════
  // GSAP + ScrollTrigger Setup
  // ═══════════════════════════════════════════════════

  gsap.registerPlugin(ScrollTrigger);

  // ═══════════════════════════════════════════════════
  // Hero Title Word-by-Word Animation (keeps words intact)
  // ═══════════════════════════════════════════════════

  const heroTitle = document.querySelector('.hero-title');
  if (heroTitle) {
    const lines = heroTitle.querySelectorAll('.line');
    let wordIndex = 0;

    lines.forEach(line => {
      // Process each text node and element
      const processNode = (node) => {
        if (node.nodeType === Node.TEXT_NODE) {
          const text = node.textContent;
          // Split by spaces but keep spaces
          const parts = text.split(/(\s+)/);
          const fragment = document.createDocumentFragment();

          parts.forEach(part => {
            if (/^\s+$/.test(part)) {
              // It's whitespace, keep as is
              fragment.appendChild(document.createTextNode(part));
            } else if (part.length > 0) {
              // It's a word, wrap it
              const wordSpan = document.createElement('span');
              wordSpan.className = 'word';
              wordSpan.style.animationDelay = `${wordIndex * 0.1}s`;
              wordSpan.textContent = part;
              fragment.appendChild(wordSpan);
              wordIndex++;
            }
          });

          node.parentNode.replaceChild(fragment, node);
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          // For elements like <span class="accent">, wrap the whole element
          if (node.classList.contains('accent')) {
            node.classList.add('word');
            node.style.animationDelay = `${wordIndex * 0.1}s`;
            wordIndex++;
          } else {
            Array.from(node.childNodes).forEach(child => processNode(child));
          }
        }
      };

      // Clone children to avoid live collection issues
      Array.from(line.childNodes).forEach(child => processNode(child));
    });
  }

  // ═══════════════════════════════════════════════════
  // Badge Countdown (Places Left)
  // ═══════════════════════════════════════════════════

  const spotsElement = document.getElementById('spots-left');
  if (spotsElement) {
    let spots = 47;

    // Randomly decrease spots occasionally
    setInterval(() => {
      if (Math.random() > 0.7 && spots > 12) {
        spots--;
        gsap.to(spotsElement, {
          scale: 1.3,
          color: '#EF4444',
          duration: 0.15,
          yoyo: true,
          repeat: 1,
          ease: 'power2.out',
          onStart: () => {
            spotsElement.textContent = spots;
          }
        });
      }
    }, 8000);
  }

  // ═══════════════════════════════════════════════════
  // Testers Count Animation
  // ═══════════════════════════════════════════════════

  const testersElement = document.getElementById('testers-count');
  if (testersElement) {
    let testers = 42;

    // Occasionally increase testers count
    setInterval(() => {
      if (Math.random() > 0.6 && testers < 99) {
        testers++;
        gsap.to(testersElement, {
          scale: 1.2,
          duration: 0.15,
          yoyo: true,
          repeat: 1,
          ease: 'power2.out',
          onStart: () => {
            testersElement.textContent = testers;
          }
        });
      }
    }, 12000);
  }

  // ═══════════════════════════════════════════════════
  // Split Text for H2 Titles
  // ═══════════════════════════════════════════════════

  function splitTextIntoWords(element) {
    const text = element.innerHTML;
    // Handle HTML tags like <span class="accent">
    const words = text.split(/(\s+)/).filter(word => word.trim() !== '');

    element.innerHTML = words.map(word => {
      if (word.startsWith('<') && word.endsWith('>')) {
        return word; // Keep HTML tags as-is
      }
      // Check if word contains HTML
      if (word.includes('<')) {
        return word;
      }
      return `<span class="word" style="display: inline-block; opacity: 0; transform: translateY(20px);">${word}</span>`;
    }).join(' ');

    return element.querySelectorAll('.word');
  }

  // ═══════════════════════════════════════════════════
  // Section Animations with ScrollTrigger
  // ═══════════════════════════════════════════════════

  const sections = [
    { selector: '.hero', children: '.hero-badge, .hero-title, .hero-sub, .waitlist-form, .hero-proof, .hero-phone' },
    { selector: '.logos', children: '.logos-label, .logo-item, .logo-more' },
    { selector: '.stats', children: '.stat-block' },
    { selector: '.how', children: '.section-header, .how-card' },
    { selector: '.features', children: '.section-header, .feature-row' },
    { selector: '.testimonials', children: '.section-header, .testimonial-card' },
    { selector: '.cta', children: '.cta-origin, .cta-title, .waitlist-form' }
  ];

  sections.forEach(({ selector, children }) => {
    const section = document.querySelector(selector);
    if (!section) return;

    const elements = section.querySelectorAll(children);
    if (elements.length === 0) return;

    // Set initial state
    gsap.set(elements, {
      opacity: 0,
      y: 60
    });

    // Animate on scroll
    ScrollTrigger.create({
      trigger: section,
      start: 'top 85%',
      once: true,
      onEnter: () => {
        gsap.to(elements, {
          opacity: 1,
          y: 0,
          duration: 0.8,
          stagger: 0.15,
          ease: 'power3.out'
        });
      }
    });
  });

  // ═══════════════════════════════════════════════════
  // H2 Split Text Animation
  // ═══════════════════════════════════════════════════

  document.querySelectorAll('.section-title, .cta-title').forEach(title => {
    // Get the raw text content while preserving structure
    const originalHTML = title.innerHTML;

    // Create wrapper spans for each word
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = originalHTML;

    function wrapWords(node) {
      if (node.nodeType === Node.TEXT_NODE) {
        const words = node.textContent.split(/(\s+)/);
        const fragment = document.createDocumentFragment();

        words.forEach(word => {
          if (word.trim() === '') {
            fragment.appendChild(document.createTextNode(word));
          } else {
            const span = document.createElement('span');
            span.className = 'word';
            span.style.display = 'inline-block';
            span.textContent = word;
            fragment.appendChild(span);
          }
        });

        node.parentNode.replaceChild(fragment, node);
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        Array.from(node.childNodes).forEach(child => wrapWords(child));
      }
    }

    wrapWords(tempDiv);
    title.innerHTML = tempDiv.innerHTML;

    const words = title.querySelectorAll('.word');

    // Set initial state
    gsap.set(words, {
      opacity: 0,
      y: 30
    });

    // Animate
    ScrollTrigger.create({
      trigger: title,
      start: 'top 85%',
      once: true,
      onEnter: () => {
        gsap.to(words, {
          opacity: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.08,
          ease: 'power3.out'
        });
      }
    });
  });

  // ═══════════════════════════════════════════════════
  // Parallax for brand pattern (if exists)
  // ═══════════════════════════════════════════════════

  const brandPattern = document.querySelector('.brand-pattern');
  if (brandPattern) {
    gsap.to(brandPattern, {
      scrollTrigger: {
        trigger: brandPattern.parentElement || document.body,
        start: 'top bottom',
        end: 'bottom top',
        scrub: true
      },
      y: (i, el) => -ScrollTrigger.maxScroll(window) * 0.3,
      ease: 'none'
    });
  }

  // ═══════════════════════════════════════════════════
  // Nav scroll effect
  // ═══════════════════════════════════════════════════

  const nav = document.querySelector('.nav');

  ScrollTrigger.create({
    start: 50,
    onUpdate: (self) => {
      if (self.scroll() > 50) {
        nav.style.boxShadow = '0 1px 30px rgba(0, 0, 0, 0.3)';
        nav.style.background = 'rgba(10, 10, 15, 0.95)';
      } else {
        nav.style.boxShadow = 'none';
        nav.style.background = 'rgba(10, 10, 15, 0.8)';
      }
    }
  });

  // ═══════════════════════════════════════════════════
  // Stats counter animation
  // ═══════════════════════════════════════════════════

  const statNums = document.querySelectorAll('.stat-num[data-count]');

  statNums.forEach(stat => {
    const target = parseInt(stat.dataset.count, 10);

    ScrollTrigger.create({
      trigger: stat,
      start: 'top 85%',
      once: true,
      onEnter: () => {
        gsap.to(stat, {
          innerHTML: target,
          duration: 1.5,
          ease: 'power2.out',
          snap: { innerHTML: 1 },
          onUpdate: function() {
            stat.textContent = Math.floor(stat.innerHTML);
          }
        });
      }
    });
  });

  // ═══════════════════════════════════════════════════
  // Training bars animation
  // ═══════════════════════════════════════════════════

  const trainingBars = document.querySelector('.training-bars');

  if (trainingBars) {
    const bars = trainingBars.querySelectorAll('.training-bar');

    ScrollTrigger.create({
      trigger: trainingBars,
      start: 'top 80%',
      once: true,
      onEnter: () => {
        bars.forEach((bar, i) => {
          const target = bar.dataset.target;
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
  // 3D iPhone Mouse Tracking (Enhanced)
  // ═══════════════════════════════════════════════════

  const iphoneWrapper = document.querySelector('.iphone-wrapper');
  const heroPhone = document.querySelector('.hero-phone');
  const iphoneScreen = document.querySelector('.iphone-screen');
  const iphoneShadow = document.querySelector('.iphone-shadow');

  if (iphoneWrapper && heroPhone) {
    let isHovering = false;
    let animationFrame;

    // Smooth mouse tracking with lerp
    let currentRotateX = 4;
    let currentRotateY = -12;
    let targetRotateX = 4;
    let targetRotateY = -12;

    function updatePhonePosition() {
      // Lerp towards target
      currentRotateX += (targetRotateX - currentRotateX) * 0.08;
      currentRotateY += (targetRotateY - currentRotateY) * 0.08;

      if (isHovering) {
        iphoneWrapper.style.transform = `
          rotateY(${currentRotateY}deg)
          rotateX(${currentRotateX}deg)
          translateZ(30px)
        `;

        // Move shadow based on rotation
        if (iphoneShadow) {
          const shadowX = -currentRotateY * 2;
          const shadowScale = 1 + Math.abs(currentRotateY) * 0.01;
          iphoneShadow.style.transform = `translateX(calc(-50% + ${shadowX}px)) rotateX(80deg) scale(${shadowScale})`;
        }
      }

      animationFrame = requestAnimationFrame(updatePhonePosition);
    }

    heroPhone.addEventListener('mouseenter', () => {
      isHovering = true;
      iphoneWrapper.style.animation = 'none';
      updatePhonePosition();
    });

    heroPhone.addEventListener('mouseleave', () => {
      isHovering = false;
      cancelAnimationFrame(animationFrame);

      gsap.to(iphoneWrapper, {
        rotateY: -12,
        rotateX: 4,
        translateZ: 0,
        duration: 0.8,
        ease: 'elastic.out(1, 0.5)',
        onComplete: () => {
          iphoneWrapper.style.animation = 'float-phone 8s ease-in-out infinite';
        }
      });

      // Reset shadow
      if (iphoneShadow) {
        gsap.to(iphoneShadow, {
          x: 0,
          scale: 1,
          duration: 0.8,
          ease: 'elastic.out(1, 0.5)'
        });
        iphoneShadow.style.transform = '';
        iphoneShadow.style.animation = 'shadow-pulse 8s ease-in-out infinite';
      }

      // Reset glare
      if (iphoneScreen) {
        gsap.to({}, {
          duration: 0.5,
          onUpdate: function() {
            const progress = this.progress();
            const glareX = (50 + targetRotateY * 2) + (50 - (50 + targetRotateY * 2)) * progress;
            const glareY = (50 - targetRotateX * 2) + (30 - (50 - targetRotateX * 2)) * progress;
            iphoneScreen.style.setProperty('--glare-x', `${glareX}%`);
            iphoneScreen.style.setProperty('--glare-y', `${glareY}%`);
          }
        });
      }

      // Reset tracking
      targetRotateX = 4;
      targetRotateY = -12;
    });

    heroPhone.addEventListener('mousemove', (e) => {
      if (!isHovering) return;

      const rect = heroPhone.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const mouseX = (e.clientX - centerX) / (rect.width / 2);
      const mouseY = (e.clientY - centerY) / (rect.height / 2);

      // Set target rotation (more dramatic)
      targetRotateY = mouseX * 25;
      targetRotateX = -mouseY * 15;

      // Update glare position
      if (iphoneScreen) {
        const glareX = 50 + mouseX * 40;
        const glareY = 50 + mouseY * 40;
        iphoneScreen.style.setProperty('--glare-x', `${glareX}%`);
        iphoneScreen.style.setProperty('--glare-y', `${glareY}%`);
      }
    });

    // Add gyroscope support for mobile
    if (window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', (e) => {
        if (!e.gamma || !e.beta) return;

        const tiltX = Math.max(-30, Math.min(30, e.gamma)) / 30;
        const tiltY = Math.max(-30, Math.min(30, e.beta - 45)) / 30;

        gsap.to(iphoneWrapper, {
          rotateY: tiltX * 15,
          rotateX: tiltY * 10,
          duration: 0.5,
          ease: 'power2.out'
        });
      });
    }
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
      content: `<p>Merci Revna 🙌</p>`,
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
  // Confetti Animation
  // ═══════════════════════════════════════════════════

  function createConfetti() {
    const container = document.createElement('div');
    container.className = 'confetti-container';
    document.body.appendChild(container);

    const colors = ['#FF6B35', '#06B6D4', '#A855F7', '#10B981', '#FFD93D', '#EF4444'];
    const shapes = ['circle', 'square', 'triangle'];

    for (let i = 0; i < 80; i++) {
      const confetti = document.createElement('div');
      const shape = shapes[Math.floor(Math.random() * shapes.length)];
      confetti.className = `confetti ${shape}`;
      confetti.style.left = Math.random() * 100 + 'vw';
      confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
      confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
      confetti.style.animationDelay = Math.random() * 0.5 + 's';
      container.appendChild(confetti);
    }

    setTimeout(() => container.remove(), 4000);
  }

  // ═══════════════════════════════════════════════════
  // Form interactions
  // ═══════════════════════════════════════════════════

  document.querySelectorAll('.waitlist-form').forEach((form) => {
    const button = form.querySelector('button[type="submit"]');
    const input = form.querySelector('input[type="email"]');
    const originalButtonText = button ? button.textContent : '';

    // Input focus glow effect
    if (input) {
      input.addEventListener('focus', () => {
        gsap.to(input, { scale: 1.02, duration: 0.2, ease: 'power2.out' });
      });
      input.addEventListener('blur', () => {
        gsap.to(input, { scale: 1, duration: 0.2, ease: 'power2.out' });
      });
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!input || !input.value || !input.validity.valid) {
        if (input) {
          input.classList.add('error');
          gsap.to(input, {
            x: [-8, 8, -8, 8, 0],
            duration: 0.4,
            ease: 'power2.out'
          });
          input.focus();
          setTimeout(() => input.classList.remove('error'), 1000);
        }
        return;
      }

      button.disabled = true;
      button.innerHTML = '<span class="btn-spinner"></span>';
      button.classList.add('loading');

      try {
        const response = await fetch('/.netlify/functions/subscribe', {
          method: 'POST',
          body: JSON.stringify({ email: input.value }),
          headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
          // Success!
          createConfetti();

          button.classList.remove('loading');
          button.classList.add('success');
          button.innerHTML = '✓ Inscrit !';
          input.value = '';
          input.disabled = true;

          // Update spots count
          const spotsElement = document.getElementById('spots-left');
          if (spotsElement) {
            const currentSpots = parseInt(spotsElement.textContent);
            spotsElement.textContent = currentSpots - 1;
            gsap.to(spotsElement, {
              scale: 1.5,
              color: '#EF4444',
              duration: 0.2,
              yoyo: true,
              repeat: 1
            });
          }

          const successMsg = document.createElement('div');
          successMsg.className = 'form-success';
          successMsg.innerHTML = '🎉 Bienvenue dans la beta ! Check tes emails.';
          form.appendChild(successMsg);

          gsap.fromTo(successMsg,
            { opacity: 0, y: -10 },
            { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }
          );
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
  // Cards hover effect with GSAP
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
  // Hero orbs parallax
  // ═══════════════════════════════════════════════════

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
  // How-it-works Icon Animations
  // ═══════════════════════════════════════════════════

  document.querySelectorAll('.how-card').forEach((card, index) => {
    const icon = card.querySelector('.how-icon-wrap');
    const svg = icon?.querySelector('svg');

    if (icon && svg) {
      // Floating animation for icons
      gsap.to(icon, {
        y: -5,
        duration: 2 + index * 0.3,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
        delay: index * 0.5
      });

      // Glow pulse effect
      gsap.to(icon, {
        boxShadow: '0 0 30px rgba(255, 107, 53, 0.4)',
        duration: 1.5,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
        delay: index * 0.3
      });

      // SVG path drawing on scroll
      const paths = svg.querySelectorAll('path, rect, circle');
      paths.forEach(path => {
        if (path.getTotalLength) {
          const length = path.getTotalLength();
          gsap.set(path, {
            strokeDasharray: length,
            strokeDashoffset: length
          });

          ScrollTrigger.create({
            trigger: card,
            start: 'top 80%',
            once: true,
            onEnter: () => {
              gsap.to(path, {
                strokeDashoffset: 0,
                duration: 1.5,
                ease: 'power2.out',
                delay: index * 0.2
              });
            }
          });
        }
      });
    }
  });

  // ═══════════════════════════════════════════════════
  // Bento Cards Enhanced Animations
  // ═══════════════════════════════════════════════════

  // Notification cards staggered animation
  document.querySelectorAll('.notif-card').forEach((notif, index) => {
    gsap.set(notif, { x: 50, opacity: 0 });

    ScrollTrigger.create({
      trigger: notif,
      start: 'top 85%',
      once: true,
      onEnter: () => {
        gsap.to(notif, {
          x: 0,
          opacity: 1,
          duration: 0.6,
          delay: index * 0.15,
          ease: 'power3.out'
        });
      }
    });
  });

  // Readiness ring animation
  const readinessRing = document.querySelector('.readiness-ring circle:last-child');
  if (readinessRing) {
    gsap.set(readinessRing, { strokeDashoffset: 314 });

    ScrollTrigger.create({
      trigger: '.readiness-display',
      start: 'top 80%',
      once: true,
      onEnter: () => {
        gsap.to(readinessRing, {
          strokeDashoffset: 69,
          duration: 1.5,
          ease: 'power2.out'
        });
        // Animate the number
        const readinessNum = document.querySelector('.readiness-num');
        if (readinessNum) {
          gsap.fromTo(readinessNum,
            { textContent: 0 },
            { textContent: 78, duration: 1.5, ease: 'power2.out', snap: { textContent: 1 } }
          );
        }
      }
    });
  }

  // HRV sparkline animation
  const sparkline = document.querySelector('.hrv-sparkline polyline');
  if (sparkline) {
    const length = sparkline.getTotalLength();
    gsap.set(sparkline, { strokeDasharray: length, strokeDashoffset: length });

    ScrollTrigger.create({
      trigger: '.hrv-sparkline',
      start: 'top 85%',
      once: true,
      onEnter: () => {
        gsap.to(sparkline, {
          strokeDashoffset: 0,
          duration: 2,
          ease: 'power2.out'
        });
      }
    });
  }

  // Training bars animation
  document.querySelectorAll('.tmb').forEach((bar, index) => {
    const targetHeight = bar.style.getPropertyValue('--h');
    gsap.set(bar, { '--h': '0%' });

    ScrollTrigger.create({
      trigger: bar,
      start: 'top 90%',
      once: true,
      onEnter: () => {
        gsap.to(bar, {
          '--h': targetHeight,
          duration: 0.8,
          delay: index * 0.1,
          ease: 'power3.out'
        });
      }
    });
  });

  // Sleep bars animation
  document.querySelectorAll('.sbm').forEach((bar, index) => {
    const targetWidth = bar.style.getPropertyValue('--w');
    gsap.set(bar, { '--w': '0%' });

    ScrollTrigger.create({
      trigger: bar,
      start: 'top 90%',
      once: true,
      onEnter: () => {
        gsap.to(bar, {
          '--w': targetWidth,
          duration: 1,
          delay: index * 0.2,
          ease: 'power2.out'
        });
      }
    });
  });

  // Empathy card animation
  const empathyQ = document.querySelector('.empathy-q');
  const empathyA = document.querySelector('.empathy-a');

  if (empathyQ && empathyA) {
    gsap.set(empathyA, { opacity: 0, y: 20 });

    ScrollTrigger.create({
      trigger: empathyQ,
      start: 'top 80%',
      once: true,
      onEnter: () => {
        gsap.to(empathyA, {
          opacity: 1,
          y: 0,
          duration: 0.6,
          delay: 0.4,
          ease: 'power3.out'
        });
      }
    });
  }

  // ═══════════════════════════════════════════════════
  // Smartwatch Animation Enhancements
  // ═══════════════════════════════════════════════════

  const smartwatch = document.querySelector('.smartwatch');
  if (smartwatch) {
    // Data update simulation
    const swValue = smartwatch.querySelector('.sw-value');
    if (swValue) {
      setInterval(() => {
        const newValue = 75 + Math.floor(Math.random() * 8);
        gsap.to(swValue, {
          textContent: newValue,
          duration: 0.3,
          snap: { textContent: 1 }
        });
      }, 5000);
    }
  }

  // ═══════════════════════════════════════════════════
  // Testimonials Cards Parallax
  // ═══════════════════════════════════════════════════

  document.querySelectorAll('.testimonial-card').forEach((card, index) => {
    gsap.to(card, {
      scrollTrigger: {
        trigger: card,
        start: 'top bottom',
        end: 'bottom top',
        scrub: 1
      },
      y: index % 2 === 0 ? -30 : 30,
      ease: 'none'
    });
  });

  // ═══════════════════════════════════════════════════
  // Floating Widgets Animations (in Hero)
  // ═══════════════════════════════════════════════════

  document.querySelectorAll('.floating-widget').forEach((widget, index) => {
    gsap.set(widget, { opacity: 0, scale: 0.8, y: 20 });

    // Animate widgets appearing with stagger after page load
    gsap.to(widget, {
      opacity: 1,
      scale: 1,
      y: 0,
      duration: 0.8,
      delay: 1.5 + index * 0.2,
      ease: 'back.out(1.7)'
    });
  });

  // ═══════════════════════════════════════════════════
  // Data Flow Lines (Widget to Phone connections)
  // ═══════════════════════════════════════════════════

  const heroPhoneEl = document.querySelector('.hero-phone');
  const iphoneEl = document.querySelector('.iphone-frame');

  if (heroPhoneEl && iphoneEl) {
    // Create SVG container for data flow lines
    const svgContainer = document.createElement('div');
    svgContainer.className = 'data-flow-container';
    svgContainer.innerHTML = `
      <svg class="data-flow-svg">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <g class="data-flow-paths"></g>
        <g class="data-dots"></g>
      </svg>
    `;
    heroPhoneEl.style.position = 'relative';
    heroPhoneEl.insertBefore(svgContainer, heroPhoneEl.firstChild);

    const svg = svgContainer.querySelector('.data-flow-svg');
    const pathsGroup = svg.querySelector('.data-flow-paths');
    const dotsGroup = svg.querySelector('.data-dots');

    // Create flowing dot animation
    function createFlowingDot(pathElement, colorClass) {
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('r', '4');
      dot.setAttribute('class', `data-dot ${colorClass}`);
      dot.setAttribute('filter', 'url(#glow)');
      dotsGroup.appendChild(dot);

      const pathLength = pathElement.getTotalLength();
      const duration = 2.5 + Math.random() * 1.5;
      const delay = Math.random() * 2;

      function animateDot() {
        gsap.fromTo({ progress: 0 },
          { progress: 0 },
          {
            progress: 1,
            duration: duration,
            delay: delay,
            ease: 'none',
            repeat: -1,
            onUpdate: function() {
              const point = pathElement.getPointAtLength(this.targets()[0].progress * pathLength);
              dot.setAttribute('cx', point.x);
              dot.setAttribute('cy', point.y);
              // Fade in and out at ends
              const progress = this.targets()[0].progress;
              const opacity = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
              dot.setAttribute('opacity', opacity * 0.9);
            }
          }
        );
      }

      animateDot();
    }

    // Calculate path from widget to phone edge
    function createPath(widgetEl, colorClass, phoneRect, containerRect) {
      const widgetRect = widgetEl.getBoundingClientRect();

      // Widget center
      const wx = widgetRect.left - containerRect.left + widgetRect.width / 2;
      const wy = widgetRect.top - containerRect.top + widgetRect.height / 2;

      // Phone bounds relative to container
      const phoneLeft = phoneRect.left - containerRect.left;
      const phoneRight = phoneLeft + phoneRect.width;
      const phoneTop = phoneRect.top - containerRect.top;
      const phoneBottom = phoneTop + phoneRect.height;
      const phoneCenterY = phoneTop + phoneRect.height / 2;

      // Determine which edge of the phone to connect to
      let targetX, targetY, controlX, controlY;

      if (wx < phoneLeft) {
        // Widget is on the left - connect to left edge
        targetX = phoneLeft - 10;
        targetY = Math.max(phoneTop + 50, Math.min(phoneBottom - 50, wy));
        controlX = (wx + targetX) / 2;
        controlY = wy + (targetY - wy) * 0.3;
      } else if (wx > phoneRight) {
        // Widget is on the right - connect to right edge
        targetX = phoneRight + 10;
        targetY = Math.max(phoneTop + 50, Math.min(phoneBottom - 50, wy));
        controlX = (wx + targetX) / 2;
        controlY = wy + (targetY - wy) * 0.3;
      } else if (wy < phoneTop) {
        // Widget is above - connect to top edge
        targetX = Math.max(phoneLeft + 50, Math.min(phoneRight - 50, wx));
        targetY = phoneTop - 10;
        controlX = wx + (targetX - wx) * 0.3;
        controlY = (wy + targetY) / 2;
      } else {
        // Widget is below - connect to bottom edge
        targetX = Math.max(phoneLeft + 50, Math.min(phoneRight - 50, wx));
        targetY = phoneBottom + 10;
        controlX = wx + (targetX - wx) * 0.3;
        controlY = (wy + targetY) / 2;
      }

      // Create smooth bezier curve
      const pathD = `M ${wx} ${wy} Q ${controlX} ${controlY} ${targetX} ${targetY}`;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', pathD);
      path.setAttribute('class', `data-flow-path ${colorClass}`);

      return path;
    }

    // Create all paths after widgets are positioned
    setTimeout(() => {
      const containerRect = heroPhoneEl.getBoundingClientRect();
      const phoneRect = iphoneEl.getBoundingClientRect();

      // Update SVG size
      svg.style.width = containerRect.width + 'px';
      svg.style.height = containerRect.height + 'px';

      // Widget configurations: element selector, color class
      const widgetConfigs = [
        { selector: '.floating-hrv', color: 'turquoise' },
        { selector: '.floating-hr', color: 'orange' },
        { selector: '.floating-sleep', color: 'purple' },
        { selector: '.floating-steps', color: 'turquoise' },
        { selector: '.floating-calories', color: 'orange' },
        { selector: '.floating-stress', color: 'turquoise' },
        { selector: '.smartwatch-float', color: 'turquoise' }
      ];

      widgetConfigs.forEach((config, index) => {
        const widget = heroPhoneEl.querySelector(config.selector);
        if (!widget) return;

        const path = createPath(widget, config.color, phoneRect, containerRect);
        path.style.animationDelay = `${index * 0.2}s`;
        pathsGroup.appendChild(path);

        // Fade in path
        setTimeout(() => {
          path.classList.add('visible');

          // Add flowing dots (2 per path for more visual interest)
          createFlowingDot(path, config.color);
          setTimeout(() => createFlowingDot(path, config.color), 1200);
        }, 300 + index * 150);
      });
    }, 2500);
  }

  // Animate mini chart bars in HRV widget (after widget appears)
  const hrvChart = document.querySelector('.floating-hrv .mini-chart');
  if (hrvChart) {
    const bars = hrvChart.querySelectorAll('span');
    bars.forEach((bar, i) => {
      const originalHeight = bar.style.height;
      gsap.set(bar, { height: '0%' });
      gsap.to(bar, {
        height: originalHeight,
        duration: 0.5,
        delay: 2.5 + i * 0.08,
        ease: 'power2.out'
      });
    });
  }

  // Animate stress meter
  const stressMeter = document.querySelector('.floating-stress .stress-meter');
  if (stressMeter) {
    const bars = stressMeter.querySelectorAll('span');
    bars.forEach((bar, i) => {
      gsap.set(bar, { scaleY: 0 });
      gsap.to(bar, {
        scaleY: 1,
        duration: 0.3,
        delay: 2.8 + i * 0.1,
        ease: 'power2.out'
      });
    });
  }

  // Steps progress bar animation
  const stepsProgress = document.querySelector('.floating-steps .steps-progress-bar');
  if (stepsProgress) {
    gsap.set(stepsProgress, { width: '0%' });
    gsap.to(stepsProgress, {
      width: '72%',
      duration: 1.2,
      delay: 2.5,
      ease: 'power2.out'
    });
  }

  // ═══════════════════════════════════════════════════
  // Mouse Follower Glow Effect
  // ═══════════════════════════════════════════════════

  const glowFollower = document.createElement('div');
  glowFollower.style.cssText = `
    position: fixed;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(255, 107, 53, 0.08) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
    transform: translate(-50%, -50%);
    transition: opacity 0.3s;
    opacity: 0;
  `;
  document.body.appendChild(glowFollower);

  let isInHero = false;
  const heroSection = document.querySelector('.hero');

  document.addEventListener('mousemove', (e) => {
    if (heroSection) {
      const heroRect = heroSection.getBoundingClientRect();
      isInHero = e.clientY < heroRect.bottom;
    }

    gsap.to(glowFollower, {
      x: e.clientX,
      y: e.clientY,
      duration: 0.5,
      ease: 'power2.out'
    });

    glowFollower.style.opacity = isInHero ? '1' : '0';
  });

}); // End DOMContentLoaded
