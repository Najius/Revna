/**
 * Revna Landing Page - Interactive Animations
 * Scroll-triggered reveals, animated counters, parallax, mouse-following glow
 */

// ═══════════════════════════════════════════════════
// Intersection Observer for Scroll-Triggered Reveals
// ═══════════════════════════════════════════════════

const observerOptions = {
  threshold: 0.15,
  rootMargin: '0px 0px -50px 0px'
};

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      // Optional: unobserve after revealing to save performance
      // revealObserver.unobserve(entry.target);
    }
  });
}, observerOptions);

// Observe all reveal elements
document.querySelectorAll('.reveal').forEach((element) => {
  revealObserver.observe(element);
});

// ═══════════════════════════════════════════════════
// Animated Counter for Stats
// ═══════════════════════════════════════════════════

const countObserverOptions = {
  threshold: 0.4
};

const countObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting && !entry.target.dataset.counted) {
      entry.target.dataset.counted = 'true';
      const target = parseInt(entry.target.dataset.count, 10);
      const isPlus = entry.target.textContent.includes('+') || entry.target.innerHTML.includes('stat-accent');
      animateCounter(entry.target, target, isPlus);
    }
  });
}, countObserverOptions);

function animateCounter(element, target, hasPlus = false) {
  const duration = 1600;
  const startTime = performance.now();

  function frame(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeOutExpo(progress);
    const current = Math.round(target * eased);

    element.textContent = current;
    if (hasPlus && progress >= 0.1) {
      element.textContent = current + '+';
    }

    if (progress < 1) {
      requestAnimationFrame(frame);
    } else {
      // Final value
      element.textContent = target + (hasPlus ? '+' : '');
    }
  }

  requestAnimationFrame(frame);
}

function easeOutExpo(t) {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

// Observe all counter elements
document.querySelectorAll('[data-count]').forEach((element) => {
  countObserver.observe(element);
});

// ═══════════════════════════════════════════════════
// Sleep Bars Width Animation
// ═══════════════════════════════════════════════════

function animateSleepBars() {
  const sleepBars = document.querySelector('.sleep-bars');
  if (!sleepBars || sleepBars.dataset.animated) return;
  sleepBars.dataset.animated = 'true';
  const fills = sleepBars.querySelectorAll('.sleep-fill');
  fills.forEach((fill, i) => {
    const target = parseInt(fill.dataset.target, 10);
    setTimeout(() => {
      fill.style.width = target + '%';
    }, i * 120);
  });
}

const sleepObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      setTimeout(animateSleepBars, 400);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -20px 0px' });

const sleepBarsSection = document.querySelector('.sleep-bars');
if (sleepBarsSection) {
  sleepObserver.observe(sleepBarsSection);
}

// ═══════════════════════════════════════════════════
// Mouse-Following Glow Effect
// ═══════════════════════════════════════════════════

const cursorGlow = document.querySelector('.cursor-glow');
const hero = document.querySelector('.hero');

if (cursorGlow && hero) {
  let mouseX = 0;
  let mouseY = 0;
  let animationFrameId;

  hero.addEventListener('mouseenter', () => {
    cursorGlow.classList.add('active');
  });

  hero.addEventListener('mouseleave', () => {
    cursorGlow.classList.remove('active');
  });

  document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;

    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
    }

    animationFrameId = requestAnimationFrame(() => {
      if (cursorGlow.classList.contains('active')) {
        cursorGlow.style.left = (mouseX - 200) + 'px';
        cursorGlow.style.top = (mouseY - 200) + 'px';
      }
    });
  });
}

// ═══════════════════════════════════════════════════
// Parallax Float Effect on Phone Mockup
// ═══════════════════════════════════════════════════

const phone = document.querySelector('.phone');

if (phone) {
  let parallaxFrameId;

  window.addEventListener('scroll', () => {
    if (parallaxFrameId) {
      cancelAnimationFrame(parallaxFrameId);
    }

    parallaxFrameId = requestAnimationFrame(() => {
      const phoneSection = phone.closest('.demo');
      if (!phoneSection) return;

      const rect = phoneSection.getBoundingClientRect();
      const sectionProgress = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);

      // Clamp between 0 and 1
      const clampedProgress = Math.max(0, Math.min(1, sectionProgress));

      // Create a subtle Y translate effect (-20px to 20px based on scroll)
      const translateY = (clampedProgress - 0.5) * 40;

      phone.style.transform = `translateY(${translateY}px)`;
    });
  });
}

// ═══════════════════════════════════════════════════
// Typing Indicator (3 bouncing dots after last message)
// ═══════════════════════════════════════════════════

// The typing indicator is already in HTML and styled with CSS animations
// The JavaScript ensures proper animation timing in relation to chat messages

// ═══════════════════════════════════════════════════
// Floating Orbs Background Animation (CSS handles it)
// ═══════════════════════════════════════════════════

// Orbs are animated purely with CSS keyframes
// JavaScript not needed - just ensure .floating-orbs parent exists

// ═══════════════════════════════════════════════════
// Smooth Scroll Optimization & Performance
// ═══════════════════════════════════════════════════

// Throttle scroll events for better performance
let scrollTimeout;

window.addEventListener('scroll', () => {
  if (scrollTimeout) {
    clearTimeout(scrollTimeout);
  }

  scrollTimeout = setTimeout(() => {
    // Optional: add any scroll-based logic here
  }, 100);
}, { passive: true });

// ═══════════════════════════════════════════════════
// Prefers Reduced Motion Detection
// ═══════════════════════════════════════════════════

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (prefersReducedMotion) {
  // CSS media query already handles this
  // but we can optionally disable JS animations here
  console.log('Reduced motion preference detected');
}

// ═══════════════════════════════════════════════════
// Ensure smooth form interactions
// ═══════════════════════════════════════════════════

const forms = document.querySelectorAll('.waitlist-form');

forms.forEach((form) => {
  const input = form.querySelector('input[type="email"]');
  const button = form.querySelector('button[type="submit"]');

  if (input && button) {
    input.addEventListener('focus', () => {
      form.style.animation = 'none';
    });

    button.addEventListener('click', (e) => {
      // Prevent default form submission if needed
      // Form will naturally submit to Formspree
      button.style.pointerEvents = 'none';
      setTimeout(() => {
        button.style.pointerEvents = 'auto';
      }, 2000);
    });
  }
});

// ═══════════════════════════════════════════════════
// Ensure DOM is ready before running animations
// ═══════════════════════════════════════════════════

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeAnimations);
} else {
  initializeAnimations();
}

function initializeAnimations() {
  // Re-check all reveal elements in case some loaded dynamically
  document.querySelectorAll('.reveal:not(.visible)').forEach((element) => {
    const rect = element.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.85) {
      element.classList.add('visible');
    }
  });
}

// ═══════════════════════════════════════════════════
// Mobile-Specific Optimizations
// ═══════════════════════════════════════════════════

const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

if (isMobile) {
  // Reduce animation complexity on mobile
  document.querySelectorAll('.reveal').forEach((el) => {
    const style = el.style;
    style.transitionDuration = '0.4s';
  });
}
