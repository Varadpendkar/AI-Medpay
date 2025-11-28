// get_quote_enhanced.js
// Ensure all initialization runs after DOM ready and errors are safely caught
document.addEventListener('DOMContentLoaded', function () {
  try {
    // Helpers
    const $ = (sel, ctx=document) => ctx.querySelector(sel);
    const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

    // Elements - with existence checks
    const steps = $$('.wizard-step');
    const totalSteps = steps.length;
    let current = 0;
    const stepNum = $('#step-num');
    const stepTotal = $('#step-total'); 
    if (stepTotal) stepTotal.textContent = totalSteps;
    const nextBtn = $('#wizard-next');
    const prevBtn = $('#wizard-prev');
    const submitBtn = $('#wizard-submit');
    const form = $('#quote-form');

  // Preview elements
  const previewCoverage = $('#preview-coverage');
  const previewBudget = $('#preview-budget');
  const previewHealth = $('#preview-health');
  const confidencePercent = $('#confidence-percent');
  const confidenceText = $('#confidence-text');
  const orbWrap = document.getElementById('orb-wrap');
  const radialWrap = document.getElementById('confidence-radial');
  const reducedMotionToggle = $('#reduced-motion-toggle');

  // Settings
  const AUTOSAVE_KEY = 'get_quote_autosave_v1';

  // Reduced motion respect
  const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced && reducedMotionToggle) {
    reducedMotionToggle.checked = true;
    reducedMotionToggle.disabled = true;
  }

  // Show step
  function showStep(i) {
    current = i;
    steps.forEach((s, idx) => {
      const hidden = idx !== i;
      s.classList.toggle('hidden', hidden);
      s.setAttribute('aria-hidden', hidden ? 'true' : 'false');
    });
    if (stepNum) stepNum.textContent = i+1;
    
    // progress percent 0..100
    const pct = Math.round(((i) / (totalSteps - 1)) * 100);
    updateOrb(pct);
    
    if (prevBtn) prevBtn.style.display = i === 0 ? 'none' : 'inline-block';
    
    if (i === totalSteps - 1) {
      if (nextBtn) nextBtn.classList.add('hidden');
      if (submitBtn) submitBtn.classList.remove('hidden');
    } else {
      if (nextBtn) nextBtn.classList.remove('hidden');
      if (submitBtn) submitBtn.classList.add('hidden');
    }
    
    // save progress
    localSave();
  }

  // Basic validation
  function validateStep(i) {
    if (!steps[i]) return true;
    const required = Array.from(steps[i].querySelectorAll('[required]'));
    for (const r of required) {
      if (!r.value || r.value.trim() === '') {
        r.focus();
        r.classList.add('border-red-500');
        
        // Add validation message
        let msg = r.nextElementSibling;
        if (!msg || !msg.classList.contains('validation-message')) {
          msg = document.createElement('div');
          msg.className = 'validation-message';
          r.parentNode.insertBefore(msg, r.nextSibling);
        }
        msg.textContent = 'This field is required';
        
        setTimeout(() => {
          r.classList.remove('border-red-500');
          if (msg) msg.remove();
        }, 3000);
        return false;
      }
    }
    return true;
  }

  // Event listeners
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (!validateStep(current)) return;
      showStep(Math.min(current + 1, totalSteps - 1));
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => showStep(Math.max(current - 1, 0)));
  }

  // Input change handlers (live preview and confidence)
  const inputs = $$('input, select, textarea', form);
  inputs.forEach(inp => {
    inp.addEventListener('input', onInputChanged);
    inp.addEventListener('change', onInputChanged);
  });

  function onInputChanged(e) {
    updatePreview();
    updateConfidence();
    localSave();
  }

  // Live preview: update summary
  function updatePreview() {
    const coverage = $('#coverage_amount') ? $('#coverage_amount').value : '';
    const budget = $('#max_premium_monthly') ? $('#max_premium_monthly').value : '';
    const healthFlags = ['has_diabetes','has_hypertension','has_asthma','has_cancer_history','has_heart_disease','has_obesity']
      .map(id => {
        const el = document.getElementById(id);
        return (el && el.checked) ? id.replace('has_','') : null;
      })
      .filter(Boolean);
    
    if (previewCoverage) {
      previewCoverage.textContent = coverage ? 
        (coverage >= 1000000 ? `${Math.round(coverage/1000000)} Cr` : `${Math.round(coverage/100000)} L`) : '—';
    }
    
    if (previewBudget) {
      previewBudget.textContent = budget ? `₹${Number(budget).toLocaleString()}` : '—';
    }
    
    if (previewHealth) {
      previewHealth.textContent = healthFlags.length ? healthFlags.join(', ') : 'None';
    }
  }

  // Confidence: naive heuristic: % of required fields filled + health weight
  function updateConfidence() {
    const reqFields = ['age','annual_income','coverage_amount'];
    let filled = 0;
    reqFields.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.value && el.value.trim() !== '') filled++;
    });
    
    // health flags reduce confidence if too many high-risk flags? we add small positive weight for more inputs
    const healthCount = ['has_diabetes','has_hypertension','has_asthma','has_cancer_history','has_heart_disease','has_obesity']
      .map(id => {
        const el = document.getElementById(id);
        return el && el.checked ? 1 : 0;
      })
      .reduce((a,b)=>a+b,0);
    
    // base calculation
    let pct = Math.round((filled / reqFields.length) * 70 + (healthCount * 5)); // up to 100
    if (pct > 98) pct = 98; // leave room for backend model+bill
    
    if (confidencePercent) confidencePercent.textContent = `${pct}%`;
    if (confidenceText) {
      confidenceText.textContent = pct < 50 ? 'Add more details for better recommendations' : 'Good — results will be meaningful';
    }
    updateRadial(pct);
  }

  // Autosave to localStorage
  function localSave() {
    try {
      const data = {};
      inputs.forEach(i => {
        if (i.type === 'checkbox') {
          data[i.name] = i.checked ? i.value : '';
        } else {
          data[i.name] = i.value || '';
        }
      });
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(data));
    } catch (e) { 
      console.debug('autosave failed', e); 
    }
  }

  function localLoad() {
    try {
      const raw = localStorage.getItem(AUTOSAVE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      inputs.forEach(i => {
        if (i.type === 'checkbox') {
          i.checked = !!data[i.name];
        } else if (data[i.name]) {
          i.value = data[i.name];
        }
      });
    } catch (e) { 
      console.debug('autosave load failed', e); 
    }
  }

  // Canvas radial fallback for confidence
  function updateRadial(pct) {
    if (!radialWrap) return;
    
    const size = 64;
    radialWrap.innerHTML = '';
    const c = document.createElement('canvas');
    c.width = size; 
    c.height = size;
    radialWrap.appendChild(c);
    
    const ctx = c.getContext('2d');
    const center = size/2;
    const radius = center - 6;
    
    // background
    ctx.clearRect(0,0,size,size);
    ctx.lineWidth = 6;
    ctx.strokeStyle = '#EEF2FF';
    ctx.beginPath(); 
    ctx.arc(center,center,radius,0,Math.PI*2); 
    ctx.stroke();
    
    // arc
    const end = (Math.PI * 2) * (pct / 100) - Math.PI/2;
    ctx.strokeStyle = '#06B6D4';
    ctx.beginPath(); 
    ctx.arc(center,center,radius,-Math.PI/2,end); 
    ctx.stroke();
  }

  // 3D orb (Three.js) - dynamic load if allowed
  let orb = { ready: false, api: {} };
  
  async function initOrb() {
    if (!orbWrap) return;
    
    if (reducedMotionToggle && reducedMotionToggle.checked) { 
      initOrbFallback(); 
      return; 
    }
    
    // dynamic load three
    if (!window.THREE) {
      try {
        await loadScript('https://unpkg.com/three@0.158.0/build/three.min.js');
      } catch (e) {
        console.warn('Failed to load Three.js, using fallback', e);
        initOrbFallback();
        return;
      }
    }
    
    // init scene
    try {
      const w = orbWrap.clientWidth || 80, h = orbWrap.clientHeight || 80;
      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(w, h); 
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      orbWrap.innerHTML = ''; 
      orbWrap.appendChild(renderer.domElement);
      
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(35, w/h, 0.1, 100);
      camera.position.z = 3.2;
      
      const light = new THREE.DirectionalLight(0xffffff, 0.9);
      light.position.set(5,5,5); 
      scene.add(light);
      
      const geo = new THREE.TorusGeometry(0.8, 0.18, 32, 64);
      const mat = new THREE.MeshStandardMaterial({ 
        color: 0x06b6d4, 
        metalness: 0.4, 
        roughness: 0.5, 
        emissive: 0x062835, 
        emissiveIntensity: 0.02 
      });
      const tor = new THREE.Mesh(geo, mat); 
      tor.rotation.x = Math.PI * 0.25; 
      scene.add(tor);
      
      // small inner sphere
      const sph = new THREE.Mesh(
        new THREE.SphereGeometry(0.28, 24, 24), 
        new THREE.MeshStandardMaterial({ 
          color: 0x0ea5a4, 
          emissive: 0x062835 
        })
      );
      scene.add(sph);
      
      orb.api = { renderer, scene, camera, tor, sph };
      orb.ready = true;
      
      // animate
      const loop = () => {
        const t = performance.now() * 0.001;
        if (orb.api.tor) {
          orb.api.tor.rotation.z += 0.008;
          orb.api.tor.rotation.x += 0.004;
        }
        if (orb.api.sph) {
          orb.api.sph.position.x = Math.sin(t*1.2) * 0.05;
        }
        if (orb.api.renderer && orb.api.scene && orb.api.camera) {
          orb.api.renderer.render(orb.api.scene, orb.api.camera);
        }
        if (orb.ready) requestAnimationFrame(loop);
      };
      loop();
    } catch(e) { 
      console.warn('orb init failed', e); 
      initOrbFallback(); 
    }
  }

  function initOrbFallback() {
    if (!orbWrap) return;
    orbWrap.innerHTML = '<div class="w-full h-full rounded-full bg-gradient-to-r from-sky-100 to-blue-100 flex items-center justify-center text-sm text-slate-600 font-semibold">📊</div>';
  }

  // update orb visual (color/brightness) by pct
  function updateOrb(pct) {
    if (orb.ready && orb.api.tor) {
      const mat = orb.api.tor.material;
      const color = mixColor(0x06b6d4, 0x16a34a, pct/100);
      mat.color.setHex(color);
      orb.api.tor.scale.setScalar(0.9 + pct/200);
    } else {
      // fallback: small CSS change
      if (orbWrap) orbWrap.style.opacity = (0.6 + pct/100*0.4).toString();
    }
  }

  // tiny color mix helper
  function mixColor(a, b, t) {
    const ar = (a>>16)&255, ag=(a>>8)&255, ab=a&255;
    const br = (b>>16)&255, bg=(b>>8)&255, bb=b&255;
    const rr = Math.round(ar + (br-ar)*t);
    const rg = Math.round(ag + (bg-ag)*t);
    const rb = Math.round(ab + (bb-ab)*t);
    return (rr<<16) + (rg<<8) + rb;
  }

  // final reveal animation (DISABLED - was causing results to disappear)
  // This function was interfering with normal form submission
  async function finalReveal() {
    // Commented out to fix the disappearing results issue
    // The server now handles the transition to results page
    console.log('finalReveal disabled - letting server handle results page');
  }

  function burstConfetti() {
    // small CSS confetti squares
    for (let i = 0; i < 18; i++){
      const el = document.createElement('div');
      el.style.position = 'fixed';
      el.style.left = (50 + (Math.random()-0.5)*30)+'%';
      el.style.top = (40 + (Math.random()-0.5)*30)+'%';
      el.style.width = '8px'; 
      el.style.height = '8px';
      el.style.background = ['#06B6D4','#10B981','#F59E0B','#EF4444'][Math.floor(Math.random()*4)];
      el.style.opacity = '0.95';
      el.style.zIndex = '9999';
      el.style.pointerEvents = 'none';
      el.style.transform = `translateY(${ -20 - Math.random()*80 }px) rotate(${Math.random()*360}deg)`;
      el.style.transition = 'all 1.2s ease-out';
      document.body.appendChild(el);
      
      setTimeout(() => {
        el.style.transform += ' translateY(100px)';
        el.style.opacity = '0';
      }, 50);
      
      setTimeout(() => el.remove(), 1200 + Math.random()*800);
    }
  }

  // load script helper
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) return resolve();
      const s = document.createElement('script'); 
      s.src = src; 
      s.async = true;
      s.onload = () => resolve(); 
      s.onerror = e => reject(e);
      document.head.appendChild(s);
    });
  }

  // local load & start
  function start() {
    localLoad();
    updatePreview(); 
    updateConfidence();
    showStep(0);
    // init orb if allowed
    if (!reducedMotionToggle || !reducedMotionToggle.checked) {
      initOrb();
    } else {
      initOrbFallback();
    }
  }

  // submit handler: just let the form submit normally
  if (form) {
    form.addEventListener('submit', async (e) => {
      // Validate final step before submitting
      if (!validateStep(current)) {
        e.preventDefault();
        return false;
      }
      
      // Show a simple loading indicator
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';
        submitBtn.classList.add('opacity-75', 'cursor-not-allowed');
      }
      
      // Let the form submit normally to the server
      // The server will return the results page
    });
  }

  // init toggle
  if (reducedMotionToggle) {
    reducedMotionToggle.addEventListener('change', () => {
      if (reducedMotionToggle.checked) {
        // stop heavy anims
        orb.ready = false;
        if (orbWrap) orbWrap.innerHTML = '';
        initOrbFallback();
      } else {
        orb.ready = false;
        initOrb();
      }
      localSave();
    });
  }

  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
      return; // Don't interfere with form inputs
    }
    
    if (e.key === 'ArrowRight' && nextBtn && !nextBtn.classList.contains('hidden')) {
      e.preventDefault();
      nextBtn.click();
    } else if (e.key === 'ArrowLeft' && prevBtn && prevBtn.style.display !== 'none') {
      e.preventDefault();
      prevBtn.click();
    } else if (e.key === 'Enter' && submitBtn && !submitBtn.classList.contains('hidden')) {
      e.preventDefault();
      submitBtn.click();
    }
  });

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }

    // Demo lecturer button handlers
    const demoBtns = $$('.demo-btn');
    demoBtns.forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Get data from button
        const age = this.dataset.age;
        const dependents = this.dataset.dependents;
        const income = this.dataset.income;
        const coverage = this.dataset.coverage;
        const premium = this.dataset.premium;
        
        // Fill form fields
        if ($('#age')) $('#age').value = age;
        if ($('#dependents')) $('#dependents').value = dependents;
        if ($('#annual_income')) $('#annual_income').value = income;
        if ($('#coverage_amount')) $('#coverage_amount').value = coverage;
        if ($('#max_premium_monthly')) $('#max_premium_monthly').value = premium;
        if ($('#demo_lecturer')) $('#demo_lecturer').value = '1';
        
        // Update preview
        updatePreview();
        updateConfidence();
        
        // Visual feedback
        demoBtns.forEach(b => b.classList.remove('bg-blue-500', 'text-white'));
        this.classList.add('bg-blue-500', 'text-white');
        
        // Auto-advance to next step or submit
        if (current < totalSteps - 1) {
          showStep(totalSteps - 1); // Go to last step
        }
      });
    });

    // expose small API for debug
    window.quoteWizard = { 
      showStep, 
      updatePreview, 
      updateConfidence, 
      localSave, 
      localLoad,
      getCurrentStep: () => current,
      getTotalSteps: () => totalSteps
    };

  } catch (err) {
    // Log a helpful error so it shows up in the dev console but doesn't block the rest of the page
    console.error('get_quote_enhanced initialization failed:', err);
  }
});
// Cache buster: 1760900427
