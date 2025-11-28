/**
 * Bill Scanner JavaScript
 * Handles drag-and-drop upload, polling, and results rendering
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
  console.log('Bill Scanner: Initializing...');

  // Drag & drop handler setup
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const progressDiv = document.getElementById('progress');
  const resultsDiv = document.getElementById('results');
  const progressPercent = document.getElementById('progressPercent');

  // Debug: Check if elements exist
  console.log('Dropzone element:', dropzone ? 'Found' : 'NOT FOUND');
  console.log('FileInput element:', fileInput ? 'Found' : 'NOT FOUND');

  if (!dropzone || !fileInput) {
    console.error('Bill Scanner: Required elements not found! Make sure #dropzone and #fileInput exist in HTML.');
    return;
  }

  // Click to upload
  dropzone.onclick = () => {
    console.log('Dropzone clicked');
    fileInput.click();
  };

  // Drag over
  dropzone.ondragover = (e) => {
    e.preventDefault();
    dropzone.classList.add('active');
  };

  dropzone.ondragleave = () => {
    dropzone.classList.remove('active');
  };

  // Drop
  dropzone.ondrop = (e) => {
    e.preventDefault();
    dropzone.classList.remove('active');
    const file = e.dataTransfer.files[0];
    if (file) {
      console.log('File dropped:', file.name);
      uploadBill(file);
    }
  };

  // File input change
  fileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
      console.log('File selected:', file.name);
      uploadBill(file);
    }
  };

  /**
   * Upload bill file to server
   */
  async function uploadBill(file) {
    try {
      // Validate file size (10MB max)
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        alert('File too large. Maximum size is 10MB.');
        return;
      }

      // Validate file type
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf', 'image/heic'];
      if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please upload JPG, PNG, PDF, or HEIC files.');
        return;
      }

      console.log('Uploading file:', file.name, file.type, file.size);

      // Show progress
      if (dropzone) dropzone.style.display = 'none';
      if (progressDiv) progressDiv.classList.remove('hidden');
      if (progressPercent) progressPercent.textContent = '0%';

      // Create form data
      const formData = new FormData();
      formData.append('file', file);

      // Upload
      console.log('Sending POST to /bill-buster/upload-bill');
      const resp = await fetch('/bill-buster/upload-bill', {
        method: 'POST',
        body: formData
      });

      console.log('Response status:', resp.status);

      if (!resp.ok) {
        const error = await resp.json();
        throw new Error(error.error || 'Upload failed');
      }

      const data = await resp.json();
      const job_id = data.job_id;

      console.log(`Upload successful. Job ID: ${job_id}`);

      // Start polling for status
      pollStatus(job_id);

    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error.message}`);
      resetUploadUI();
    }
  }

  /**
   * Poll job status until complete
   */
  async function pollStatus(job_id) {
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`/bill-buster/upload-status/${job_id}`);
        const data = await resp.json();

        const status = data.status;
        const progress = data.progress || 0;

        // Update progress bar
        if (progressPercent) {
          progressPercent.textContent = `${progress}%`;
        }

        console.log(`Job ${job_id} status: ${status} (${progress}%)`);

        if (status === 'completed') {
          clearInterval(interval);
          loadResults(job_id);
        } else if (status === 'failed' || status === 'error') {
          clearInterval(interval);
          alert('Processing failed. Please try again.');
          resetUploadUI();
        }

      } catch (error) {
        console.error('Status check error:', error);
        clearInterval(interval);
        alert('Error checking status. Please refresh the page.');
        resetUploadUI();
      }
    }, 2000); // Poll every 2 seconds
  }

  /**
   * Load and display results
   */
  async function loadResults(job_id) {
    try {
      const resp = await fetch(`/bill-buster/scan-result/${job_id}`);

      if (!resp.ok) {
        const error = await resp.json();
        throw new Error(error.error || 'Failed to load results');
      }

      const data = await resp.json();

      // Hide progress
      if (progressDiv) progressDiv.classList.add('hidden');

      // Render results
      renderResults(data);

    } catch (error) {
      console.error('Load results error:', error);
      alert(`Error loading results: ${error.message}`);
      resetUploadUI();
    }
  }

  /**
   * Render scan results to DOM
   */
  function renderResults(data) {
    if (!resultsDiv) return;

    resultsDiv.classList.remove('hidden');

    // Extract data - support both old and new field names
    const hospitalName = data.hospital_name || data.hospital || 'Unknown Hospital';
    const billDate = data.bill_date || data.date || 'N/A';
    const invoiceNo = data.invoice_no || data.invoice_number || 'N/A';
    const totalAmount = data.total_amount || data.grand_total || 0;
    const ocrConfidence = data.ocr_confidence || 0;
    const lineItems = data.line_items || [];
    const flaggedItems = data.flagged_items || [];
    const potentialSavings = data.potential_savings || data.total_savings || 0;

    // Build flagged items lookup by line index
    const flaggedByLine = {};
    flaggedItems.forEach(flag => {
      if (flag.indices) {
        // Duplicate item - mark both indices
        flag.indices.forEach(idx => {
          if (!flaggedByLine[idx]) flaggedByLine[idx] = [];
          flaggedByLine[idx].push(flag);
        });
      } else if (flag.line_index !== undefined) {
        // Inflated item - mark single index
        const idx = flag.line_index;
        if (!flaggedByLine[idx]) flaggedByLine[idx] = [];
        flaggedByLine[idx].push(flag);
      }
    });

    // Build HTML
    let html = `
      <div class="bill-summary" style="background: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h3 style="font-size: 1.5rem; font-weight: bold; color: #1f2937; margin-bottom: 1rem;">${escapeHtml(hospitalName)}</h3>
        <p style="color: #4b5563; margin-bottom: 0.5rem;"><strong>Date:</strong> ${billDate} | <strong>Invoice:</strong> ${invoiceNo}</p>
        <p style="color: #4b5563; margin-bottom: 0.5rem;"><strong>Total Amount:</strong> ₹${totalAmount.toLocaleString('en-IN')}</p>
        <p style="color: #4b5563;"><strong>OCR Confidence:</strong> ${ocrConfidence.toFixed(1)}%</p>
      </div>

      <h4 style="margin-top: 2rem; margin-bottom: 1rem; font-size: 1.25rem; font-weight: bold;">Line Items</h4>
      <div class="table-responsive" style="overflow-x: auto; margin-bottom: 2rem;">
        <table class="bill-items" style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          <thead>
            <tr style="background: linear-gradient(135deg, #dc2626 0%, #ea580c 100%); color: white;">
              <th style="padding: 0.75rem; text-align: left; font-weight: 600;">#</th>
              <th style="padding: 0.75rem; text-align: left; font-weight: 600;">Description</th>
              <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Qty</th>
              <th style="padding: 0.75rem; text-align: right; font-weight: 600;">Unit Price</th>
              <th style="padding: 0.75rem; text-align: right; font-weight: 600;">Amount</th>
              <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Status</th>
            </tr>
          </thead>
          <tbody>
    `;

    lineItems.forEach((item, i) => {
      const hasFlags = flaggedByLine[i] && flaggedByLine[i].length > 0;
      const rowStyle = hasFlags ? 
        'background: #fef2f2; border-left: 4px solid #ef4444;' : 
        'background: white;';

      html += `
        <tr style="${rowStyle} border-bottom: 1px solid #e5e7eb;">
          <td style="padding: 0.75rem; font-weight: 500;">${i + 1}</td>
          <td style="padding: 0.75rem;">${escapeHtml(item.desc || item.description || '')}</td>
          <td style="padding: 0.75rem; text-align: center;">${item.qty || item.quantity || 1}</td>
          <td style="padding: 0.75rem; text-align: right;">${item.unit || item.unit_price ? '₹' + (item.unit || item.unit_price).toLocaleString('en-IN') : '-'}</td>
          <td style="padding: 0.75rem; text-align: right; font-weight: 600;">₹${(item.amount || 0).toLocaleString('en-IN')}</td>
          <td style="padding: 0.75rem; text-align: center;">
            ${hasFlags ? 
              '<span style="color: #ef4444; font-size: 1.25rem;">❌</span>' :
              '<span style="color: #10b981; font-size: 1.25rem;">✓</span>'
            }
          </td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
    `;

    // Analysis Summary Card
    html += `
      <div style="background: ${potentialSavings > 0 ? 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)' : 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)'}; padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; border: 2px solid ${potentialSavings > 0 ? '#ef4444' : '#10b981'};">
        <h4 style="font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem;">📊 Analysis Summary</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
          <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="color: #6b7280; font-size: 0.875rem; margin-bottom: 0.25rem;">Flagged Items:</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: ${potentialSavings > 0 ? '#dc2626' : '#059669'};">${flaggedItems.length} ${potentialSavings > 0 ? '⚠️' : ''}</div>
          </div>
          <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="color: #6b7280; font-size: 0.875rem; margin-bottom: 0.25rem;">Potential Savings:</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: ${potentialSavings > 0 ? '#dc2626' : '#059669'};">₹${potentialSavings.toLocaleString('en-IN')}</div>
          </div>
        </div>
        ${potentialSavings > 0 ? `
          <p style="background: #fef2f2; padding: 0.75rem; border-radius: 6px; border-left: 4px solid #dc2626; margin-top: 1rem;">
            💡 <strong>Tip:</strong> You may be able to recover ₹${potentialSavings.toLocaleString('en-IN')} by contesting flagged charges (conservative estimate).
          </p>
        ` : `
          <p style="background: #f0fdf4; padding: 0.75rem; border-radius: 6px; border-left: 4px solid #10b981; margin-top: 1rem;">
            ✅ <strong>No major anomalies detected.</strong> Bill appears reasonable.
          </p>
        `}
      </div>
    `;

    // Mistake Details Table (if anomalies found)
    if (flaggedItems.length > 0) {
      html += `
        <h4 style="margin-top: 2rem; margin-bottom: 1rem; font-size: 1.25rem; font-weight: bold; color: #dc2626;">❌ Bill Analysis Mistakes</h4>
        <div class="table-responsive" style="overflow-x: auto; margin-bottom: 2rem;">
          <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <thead>
              <tr style="background: linear-gradient(135deg, #dc2626 0%, #ea580c 100%); color: white;">
                <th style="padding: 0.75rem; text-align: left; font-weight: 600;">Mistake Type</th>
                <th style="padding: 0.75rem; text-align: left; font-weight: 600;">Item Line(s)</th>
                <th style="padding: 0.75rem; text-align: left; font-weight: 600;">Anomaly Detail</th>
              </tr>
            </thead>
            <tbody>
      `;

      flaggedItems.forEach((flag, idx) => {
        let mistakeType = flag.type || 'unknown';
        let lineNumbers = '';
        let anomalyDetail = '';

        // Format based on type
        if (flag.type === 'duplicate_item') {
          mistakeType = '🔄 Duplicate Billing';
          lineNumbers = `Line ${(flag.indices || []).map(i => i + 1).join(' & ')}`;
          anomalyDetail = `"${escapeHtml(flag.description || '')}" appears ${flag.indices ? flag.indices.length : 2} times with same price (₹${(flag.amount || 0).toLocaleString('en-IN')}). Potential overcharge: ₹${(flag.excess || 0).toLocaleString('en-IN')}`;
        } else if (flag.type === 'inflated_vs_expected') {
          mistakeType = '💸 Suspected Overcharge';
          lineNumbers = `Line ${(flag.line_index || 0) + 1}`;
          anomalyDetail = `"${escapeHtml(flag.description || '')}" charged at ₹${(flag.actual || 0).toLocaleString('en-IN')}, expected ₹${(flag.expected || 0).toLocaleString('en-IN')} (${flag.factor ? (flag.factor * 100).toFixed(0) + '%' : ''} of market rate)`;
        } else if (flag.type === 'subtotal_mismatch' || flag.type === 'grandtotal_mismatch') {
          mistakeType = '🧮 Logic/Calculation Error';
          lineNumbers = flag.type === 'subtotal_mismatch' ? 'Subtotal' : 'Grand Total';
          anomalyDetail = `Computed: ₹${(flag.computed_subtotal || flag.expected_grand || 0).toLocaleString('en-IN')}, Found: ₹${(flag.found_subtotal || flag.found_grand || 0).toLocaleString('en-IN')}, Difference: ₹${(flag.diff || 0).toLocaleString('en-IN')}`;
        } else {
          mistakeType = '⚠️ ' + (flag.type || 'Unknown Issue').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          lineNumbers = flag.indices ? flag.indices.map(i => i + 1).join(', ') : (flag.line_index !== undefined ? `Line ${flag.line_index + 1}` : 'N/A');
          anomalyDetail = escapeHtml(flag.reason || flag.description || 'See details above');
        }

        html += `
          <tr style="border-bottom: 1px solid #e5e7eb; background: ${idx % 2 === 0 ? '#ffffff' : '#f9fafb'};">
            <td style="padding: 0.75rem; font-weight: 600; color: #dc2626;">${mistakeType}</td>
            <td style="padding: 0.75rem; font-weight: 500;">${lineNumbers}</td>
            <td style="padding: 0.75rem; color: #4b5563;">${anomalyDetail}</td>
          </tr>
        `;
      });

      html += `
            </tbody>
          </table>
        </div>
      `;
    }

    // Action buttons
    html += `
      <div style="text-align: center; margin-top: 2rem;">
        <button onclick="window.location.href='/bill-buster/pre-auth'" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 0.75rem 2rem; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; margin-right: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">Estimate Pre-Auth OOP</button>
        <button onclick="billScanner.resetUploadUI()" style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); color: white; padding: 0.75rem 2rem; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">Scan Another Bill</button>
      </div>
    `;

    resultsDiv.innerHTML = html;
  }

  /**
   * Reset UI to initial state
   */
  function resetUploadUI() {
    if (dropzone) dropzone.style.display = 'block';
    if (progressDiv) progressDiv.classList.add('hidden');
    if (resultsDiv) {
      resultsDiv.classList.add('hidden');
      resultsDiv.innerHTML = '';
    }
    if (fileInput) fileInput.value = '';
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }

  // Expose resetUploadUI globally for button onclick
  window.billScanner = {
    resetUploadUI: resetUploadUI
  };

  console.log('Bill Scanner: Initialized successfully ✓');
});
