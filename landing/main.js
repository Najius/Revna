/**
 * Revna v8 — Landing Page Interactions
 * Scroll reveals, animated counters, sleep bars
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
    }, i * 150);
  });
}

const sleepObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      setTimeout(animateSleepBars, 300);
    }
  });
}, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

const sleepSection = document.querySelector('.sleep-bars');
if (sleepSection) {
  sleepObserver.observe(sleepSection);
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
