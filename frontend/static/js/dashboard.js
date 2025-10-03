// dashboard.js
document.addEventListener('DOMContentLoaded', function () {
  // Setup accordion toggles
  document.querySelectorAll('.explain-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const body = btn.parentElement.querySelector('.explain-body');
      const plus = btn.querySelector('div:last-child') || btn.lastElementChild;
      if (!body) return;
      const isHidden = body.classList.contains('hidden');
      if (isHidden) {
        body.classList.remove('hidden');
        if (plus) plus.textContent = '-';
        btn.setAttribute('aria-expanded', 'true');
      } else {
        body.classList.add('hidden');
        if (plus) plus.textContent = '+';
        btn.setAttribute('aria-expanded', 'false');
      }
    });
  });

  // Setup Chart.js savings tracker - sample data; replace from server if needed
  const ctx = document.getElementById('savingsChart');
  if (ctx) {
    const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const data = {
      labels,
      datasets: [{
        label: 'Savings (₹)',
        data: [1200, 3000, 5200, 8000, 9500, (window.SAVINGS_YEAR || 12000)],
        fill: true,
        tension: 0.4,
        backgroundColor: 'rgba(0,166,147,0.08)',
        borderColor: '#00a693',
        pointRadius: 3,
        pointBackgroundColor: '#00a693',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2
      }]
    };
    
    new Chart(ctx, { 
      type: 'line', 
      data, 
      options: { 
        responsive: true, 
        maintainAspectRatio: false,
        plugins: { 
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: '#00a693',
            borderWidth: 1
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(0,0,0,0.05)'
            },
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        }
      }
    });
  }

  // Animate counter numbers on load
  const animateCounters = () => {
    document.querySelectorAll('[data-count]').forEach(el => {
      const target = parseInt(el.getAttribute('data-count'));
      const duration = 1000;
      const step = target / (duration / 16);
      let current = 0;
      
      const timer = setInterval(() => {
        current += step;
        if (current >= target) {
          el.textContent = '₹' + target.toLocaleString();
          clearInterval(timer);
        } else {
          el.textContent = '₹' + Math.floor(current).toLocaleString();
        }
      }, 16);
    });
  };

  // Start counter animation after short delay
  setTimeout(animateCounters, 500);
});