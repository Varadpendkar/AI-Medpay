// bill_buster_preauth.js - REPLACE ENTIRE FILE
import { renderPreAuthResults, showToast } from './bill_buster_enhanced.js';

const calculateBtn = document.getElementById('calculateBtn');
const clearBtn = document.getElementById('clearBtn');
const resultsGrid = document.getElementById('resultsGrid');
const filterRecommended = document.getElementById('filterRecommended');

function showSkeleton(count = 3) {
  resultsGrid.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const s = document.createElement('div');
    s.className = 'skeleton-card skeleton';
    resultsGrid.appendChild(s);
  }
}

async function fetchEstimates(payload) {
  const res = await fetch('/pre-auth-estimate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || 'Server error');
  }
  return res.json();
}

calculateBtn.addEventListener('click', async () => {
  const procedure = document.getElementById('procedure').value;
  const insurer = document.getElementById('insurer').value;
  const patient_type = document.getElementById('patient_type').value;

  if (!procedure) {
    showToast('Please select a procedure.');
    return;
  }

  const payload = { procedure, insurer, patient_type };
  // show skeletons
  showSkeleton();
  try {
    const data = await fetchEstimates(payload);
    // data expected: { plans: [ { id, name, oop, coverage_pct, highlights:[], logo_url, breakdown:{...}, recommended: true/false } ] }
    renderPreAuthResults(data.plans || [], { recommendedOnly: filterRecommended.checked });
    document.getElementById('resultsCount').innerText = `${(data.plans||[]).length} estimates found`;
  } catch (err) {
    resultsGrid.innerHTML = `<div class="text-red-600 p-4">Error fetching estimates: ${err.message}</div>`;
  }
});

clearBtn.addEventListener('click', () => {
  document.getElementById('procedure').value = '';
  document.getElementById('insurer').value = '';
  document.getElementById('patient_type').value = 'standard';
  resultsGrid.innerHTML = '';
  document.getElementById('resultsCount').innerText = 'No estimates yet';
});

// filter toggle to re-filter visible cards (simple)
filterRecommended.addEventListener('change', () => {
  // re-run last-known render if available (we store lastData in enhanced module)
  // dispatch custom event consumed by enhanced module:
  window.dispatchEvent(new CustomEvent('filterRecommendedChanged', { detail: { recommendedOnly: filterRecommended.checked } }));
});
