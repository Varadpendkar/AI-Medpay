// bill_buster_enhanced.js - REPLACE ENTIRE FILE
const resultsGrid = document.getElementById('resultsGrid');
let lastPlans = [];

export function showToast(msg, timeout=3000) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerText = msg;
  document.body.appendChild(t);
  setTimeout(()=> t.remove(), timeout);
}

export function renderPreAuthResults(plans = [], opts = {}) {
  lastPlans = plans;
  const recommendedOnly = opts.recommendedOnly || false;
  resultsGrid.innerHTML = '';

  const visible = recommendedOnly ? plans.filter(p => p.recommended) : plans;

  if (!visible.length) {
    resultsGrid.innerHTML = `<div class="text-slate-600 p-4">No results match your criteria.</div>`;
    return;
  }

  // create cards
  visible.forEach(plan => {
    const card = document.createElement('div');
    card.className = 'plan-card';
    card.dataset.planId = plan.id;

    card.innerHTML = `
      <div class="p-4 sm:p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <img src="${plan.logo_url || '/static/img/hospital-placeholder.svg'}" alt="${plan.name}" class="w-12 h-12 rounded-md object-cover">
            <div>
              <div class="text-sm font-semibold text-slate-900">${escapeHtml(plan.name)}</div>
              <div class="text-xs text-slate-500 mt-0.5">${escapeHtml(plan.tagline || 'Comprehensive cover')}</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-xs text-slate-500">Coverage</div>
            <div class="mt-1 inline-flex items-center gap-2">
              <svg class="w-10 h-10" viewBox="0 0 36 36">
                <path class="bg-circle" d="M18 2.0845a15.9155 15.9155 0 1 0 0 31.831" fill="none" stroke="#E6EEF8" stroke-width="3"/>
                <path class="fg-circle" d="M18 2.0845a15.9155 15.9155 0 1 0 0 31.831" fill="none" stroke="#00B4D8" stroke-width="3" stroke-linecap="round" transform="rotate(-90 18 18)"/>
              </svg>
              <div class="text-sm font-semibold">${Math.round(plan.coverage_pct || 0)}%</div>
            </div>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 items-center">
          <div>
            <div class="text-xs text-slate-500">Estimated OOP</div>
            <div class="oop-amount text-2xl font-extrabold text-slate-900">₹<span class="oop-value" data-value="${plan.oop || 0}">0</span></div>
            <div class="text-xs text-slate-500 mt-1">Est. after insurer payout</div>
          </div>

          <div class="flex flex-col gap-2">
            <ul class="flex-1 text-sm text-slate-600 space-y-1">
              ${ (plan.highlights || []).slice(0,3).map(h => `<li class="flex items-start gap-2"><svg class="w-4 h-4 mt-0.5 text-green-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 00-1.414 0L8 12.586 4.707 9.293A1 1 0 003.293 10.707l4 4a1 1 0 001.414 0l8-8a1 1 0 000-1.414z" clip-rule="evenodd"/></svg><span>${escapeHtml(h)}</span></li>`).join('') }
            </ul>

            <div class="flex gap-2 mt-2">
              <button class="btn-outline view-breakdown" data-plan="${plan.id}">View Breakdown</button>
              <button class="btn-primary compare-btn" data-plan="${plan.id}">${plan.recommended ? 'AI Recommended' : 'Compare'}</button>
            </div>
          </div>
        </div>

        <div class="breakdown mt-3 hidden text-sm text-slate-700 border-t pt-3">
          <div class="grid grid-cols-2 gap-2">
            <div>Deductible</div><div class="text-right">₹${(plan.breakdown && plan.breakdown.deductible) || 0}</div>
            <div>Room Rent</div><div class="text-right">₹${(plan.breakdown && plan.breakdown.room_rent) || 0}</div>
            <div>Implants</div><div class="text-right">₹${(plan.breakdown && plan.breakdown.implants) || 0}</div>
          </div>
        </div>
      </div>
    `;

    resultsGrid.appendChild(card);

    // animate count-up
    const el = card.querySelector('.oop-value');
    animateCountUp(el, Number(el.dataset.value || 0));

    // animate radial progress by setting stroke-dasharray
    const pct = Math.max(0, Math.min(100, Math.round(plan.coverage_pct || 0)));
    const fg = card.querySelector('.fg-circle');
    if (fg) {
      // SVG circumference approx 2πr (r ~ 15.9155) -> 100% maps to ~100 (we will calculate fraction)
      const circumference = 100;
      const dash = (pct/100) * circumference;
      fg.style.strokeDasharray = `${dash} ${circumference}`;
    }

    // wire up breakdown toggle
    card.querySelectorAll('.view-breakdown').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const br = card.querySelector('.breakdown');
        br.classList.toggle('hidden');
      });
    });

    // wire up compare button (dispatch event)
    card.querySelectorAll('.compare-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const pid = btn.dataset.plan;
        window.dispatchEvent(new CustomEvent('comparePlan', { detail: { planId: pid, plan } }));
      });
    });
  });

  // connect filter event to re-render if filter changes
  window.addEventListener('filterRecommendedChanged', (ev) => {
    renderPreAuthResults(lastPlans, { recommendedOnly: ev.detail.recommendedOnly });
  });
}

// small helper: escape HTML
function escapeHtml(s='') {
  return String(s).replace(/[&<>"'`]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','`':'&#96;'}[c]));
}

// animate simple count-up
function animateCountUp(el, target) {
  let start = 0;
  const duration = 900;
  const stepTime = 20;
  const steps = Math.ceil(duration/stepTime);
  const inc = (target - start) / steps;
  let cur = start;
  const timer = setInterval(() => {
    cur += inc;
    if ((inc>0 && cur >= target) || (inc<0 && cur <= target)) {
      el.innerText = formatNumber(Math.round(target));
      clearInterval(timer);
    } else {
      el.innerText = formatNumber(Math.round(cur));
    }
  }, stepTime);
}

function formatNumber(n) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// export default fallback
export default { renderPreAuthResults, showToast };
