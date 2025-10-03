// main.js - simple interactivity hooks
document.addEventListener('DOMContentLoaded', function() {
  // Chatbot launcher demo behavior - replace with actual chat integration
  const chatBtn = document.getElementById('chatbot-launch');
  chatBtn.addEventListener('click', () => {
    alert('Open Chatbot (replace this with real chat integration).');
  });

  // Simple Demo: animate counters on scroll into view
  const counters = document.querySelectorAll('[data-count]');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const to = parseInt(el.getAttribute('data-count'), 10);
        let current = 0;
        const step = Math.max(1, Math.floor(to / 60));
        const t = setInterval(() => {
          current += step;
          if (current >= to) {
            el.textContent = to.toLocaleString();
            clearInterval(t);
          } else {
            el.textContent = current.toLocaleString();
          }
        }, 12);
        obs.unobserve(el);
      }
    });
  }, {threshold: 0.5});

  counters.forEach(c => obs.observe(c));
});