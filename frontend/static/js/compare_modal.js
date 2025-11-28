// compare_modal.js - REPLACE ENTIRE FILE
(function(){
  const root = document.getElementById('compareModalRoot');

  function showModal(plan) {
    root.innerHTML = `
      <div class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="fixed inset-0 bg-black/40" id="cmp-backdrop"></div>
        <div class="bg-white rounded-lg shadow-lg w-[90%] md:w-2/3 p-6 z-50">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">Compare Plan</h3>
            <button id="cmp-close" class="text-slate-500">Close</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 class="font-semibold">${escapeHtml(plan.name)}</h4>
              <p class="text-sm text-slate-600 mt-1">${escapeHtml(plan.tagline || '')}</p>
              <div class="mt-3">
                <div class="text-xs text-slate-500">Estimated OOP</div>
                <div class="text-2xl font-extrabold">₹${formatNumber(plan.oop || 0)}</div>
              </div>
            </div>
            <div>
              <div class="text-xs text-slate-500">Highlights</div>
              <ul class="mt-2 text-sm text-slate-700">${ (plan.highlights || []).map(h => `<li>• ${escapeHtml(h)}</li>`).join('') }</ul>
            </div>
          </div>
        </div>
      </div>
    `;
    root.querySelector('#cmp-close').addEventListener('click', hideModal);
    root.querySelector('#cmp-backdrop').addEventListener('click', hideModal);
  }

  function hideModal() { root.innerHTML = ''; }

  window.addEventListener('comparePlan', (ev) => {
    const plan = ev.detail.plan;
    if (!plan) return;
    showModal(plan);
  });

  function escapeHtml(s='') { return String(s).replace(/[&<>"'`]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','`':'&#96;'}[c])); }
  function formatNumber(n) { return (n||0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
})();
