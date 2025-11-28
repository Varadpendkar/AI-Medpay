// static/js/get_quote.js
// Multi-step "Get Quote" form logic

const TOTAL_STEPS = 5;
let currentStep = 1;

// Parse typed values from form data
function parseTyped(val, fieldName) {
  if (val === '' || val === null) return null;
  
  // Boolean fields
  if (['smoking_flag', 'alcohol_flag', 'maternity_required', 'critical_illness_required'].includes(fieldName)) {
    return val === 'true';
  }
  
  // Number fields
  if ([
    'age', 'income', 'premium_budget', 'bmi', 
    'dependents_count', 'coverage_amount_preference', 
    'previous_claims_count'
  ].includes(fieldName)) {
    const num = parseFloat(val);
    return isNaN(num) ? null : num;
  }
  
  return val;
}

// Show specified step
function showStep(n) {
  const sections = document.querySelectorAll('[data-step]');
  sections.forEach(section => {
    const stepNum = parseInt(section.getAttribute('data-step'));
    if (stepNum === n) {
      section.classList.remove('hidden-step');
      section.classList.add('step-active');
    } else {
      section.classList.remove('step-active');
      section.classList.add('hidden-step');
    }
  });

  // Update buttons
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const submitBtn = document.getElementById('submitBtn');

  if (n === 1) {
    prevBtn.style.display = 'none';
  } else {
    prevBtn.style.display = 'inline-block';
  }

  if (n === TOTAL_STEPS) {
    nextBtn.classList.add('hidden');
    submitBtn.classList.remove('hidden');
  } else {
    nextBtn.classList.remove('hidden');
    submitBtn.classList.add('hidden');
  }

  // Update progress
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');
  const pct = ((n - 1) / (TOTAL_STEPS - 1)) * 100;
  progressFill.style.width = pct + '%';
  progressText.textContent = `Step ${n} of ${TOTAL_STEPS}`;

  currentStep = n;
}

// Validate current step
function validateStep(n) {
  const section = document.querySelector(`[data-step="${n}"]`);
  const inputs = section.querySelectorAll('input[required], select[required]');
  let valid = true;

  inputs.forEach(input => {
    if (!input.value.trim()) {
      input.classList.add('border-red-500');
      valid = false;
    } else {
      input.classList.remove('border-red-500');
    }
  });

  if (!valid) {
    alert('Please fill all required fields.');
  }
  return valid;
}

// Build payload
function buildPayload() {
  const form = document.getElementById('getQuoteForm');
  const formData = new FormData(form);
  const payload = {};

  for (let [key, value] of formData.entries()) {
    const typed = parseTyped(value, key);
    if (typed !== null && typed !== '') {
      payload[key] = typed;
    }
  }

  // Handle comma-separated fields
  if (payload.pre_existing_conditions) {
    payload.pre_existing_conditions = payload.pre_existing_conditions
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  }
  if (payload.preferred_providers) {
    payload.preferred_providers = payload.preferred_providers
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  }

  return payload;
}

// Display recommendations
function displayRecommendations(data) {
  const resultDiv = document.getElementById('result');
  const listDiv = document.getElementById('recommendationsList');
  const jsonPre = document.getElementById('resultJson');

  resultDiv.classList.remove('hidden');
  listDiv.innerHTML = '';

  if (!data.recommendations || data.recommendations.length === 0) {
    listDiv.innerHTML = '<p class="text-slate-500">No recommendations found.</p>';
    return;
  }

  data.recommendations.forEach((rec, idx) => {
    const card = document.createElement('div');
    card.className = 'border rounded p-4 bg-slate-50';
    card.innerHTML = `
      <div class="flex justify-between items-start">
        <div>
          <h4 class="font-semibold text-base">${rec.plan_name || 'Plan'}</h4>
          <p class="text-xs text-slate-500">Provider: ${rec.provider || 'N/A'}</p>
        </div>
        <span class="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded">#${idx + 1}</span>
      </div>
      <div class="mt-2 grid grid-cols-2 gap-2 text-sm">
        <div><span class="text-slate-500">Premium:</span> ₹${rec.premium ? rec.premium.toLocaleString() : 'N/A'}</div>
        <div><span class="text-slate-500">Coverage:</span> ₹${rec.coverage_amount ? rec.coverage_amount.toLocaleString() : 'N/A'}</div>
        ${rec.score !== undefined ? `<div class="col-span-2"><span class="text-slate-500">Score:</span> ${rec.score.toFixed(4)}</div>` : ''}
      </div>
    `;
    listDiv.appendChild(card);
  });

  jsonPre.textContent = JSON.stringify(data, null, 2);
  jsonPre.classList.remove('hidden');
}

// Handle form submission
async function handleSubmit(e) {
  e.preventDefault();
  if (!validateStep(currentStep)) return;

  const payload = buildPayload();
  console.log('Submitting payload:', payload);

  // Show loading
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Loading...';

  try {
    const response = await fetch('/api/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('Response:', data);
    displayRecommendations(data);
  } catch (err) {
    console.error('Error fetching recommendations:', err);
    alert('Failed to fetch recommendations. Please try again.\n' + err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Get Quote';
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  showStep(1);

  document.getElementById('prevBtn').addEventListener('click', () => {
    if (currentStep > 1) {
      showStep(currentStep - 1);
    }
  });

  document.getElementById('nextBtn').addEventListener('click', () => {
    if (validateStep(currentStep) && currentStep < TOTAL_STEPS) {
      showStep(currentStep + 1);
    }
  });

  document.getElementById('getQuoteForm').addEventListener('submit', handleSubmit);
});
