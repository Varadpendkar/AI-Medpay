// Bill Buster JavaScript functionality
class BillBuster {
    constructor() {
        this.uploadZone = document.getElementById('upload-zone');
        this.fileInput = document.getElementById('file-input');
        this.browseBtn = document.getElementById('browse-btn');
        this.filePreview = document.getElementById('file-preview');
        this.fileName = document.getElementById('file-name');
        this.analyzeBtn = document.getElementById('analyze-btn');
        this.form = document.getElementById('bill-upload-form');
        this.scanOverlay = document.getElementById('scan-overlay');
        this.resultsSection = document.getElementById('results-section');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Browse button click
        this.browseBtn.addEventListener('click', () => {
            this.fileInput.click();
        });

        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files[0]);
        });

        // Drag and drop events
        this.uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadZone.classList.add('dragover');
        });

        this.uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.uploadZone.classList.remove('dragover');
        });

        this.uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadZone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelection(files[0]);
            }
        });

        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.analyzeBill();
        });
    }

    handleFileSelection(file) {
        if (!file) return;

        // Validate file type
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
        if (!allowedTypes.includes(file.type)) {
            this.showError('Please upload a PDF, JPG, or PNG file.');
            return;
        }

        // Validate file size (10MB limit)
        const maxSize = 10 * 1024 * 1024; // 10MB in bytes
        if (file.size > maxSize) {
            this.showError('File size must be less than 10MB.');
            return;
        }

        // Update UI
        this.fileName.textContent = file.name;
        this.filePreview.classList.remove('hidden');
        this.analyzeBtn.disabled = false;
        
        // Set the file input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        this.fileInput.files = dataTransfer.files;
    }

    showError(message) {
        // Create error alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-50 border border-red-200 rounded-lg p-4 mt-4';
        errorDiv.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm text-red-700">${message}</p>
                </div>
            </div>
        `;

        // Remove existing errors
        const existingErrors = this.uploadZone.querySelectorAll('.bg-red-50');
        existingErrors.forEach(error => error.remove());

        // Add new error
        this.uploadZone.appendChild(errorDiv);

        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    async analyzeBill() {
        if (!this.fileInput.files[0]) {
            this.showError('Please select a file first.');
            return;
        }

        try {
            // Show scanning animation
            this.showScanAnimation();

            // Create FormData for file upload
            const formData = new FormData();
            formData.append('bill_file', this.fileInput.files[0]);

            // Submit to backend
            const response = await fetch('/bill-buster/submit', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Failed to analyze bill');
            }

            const result = await response.json();
            
            // Hide scanning animation
            this.hideScanAnimation();
            
            // Show results
            this.displayResults(result);

        } catch (error) {
            console.error('Error analyzing bill:', error);
            this.hideScanAnimation();
            this.showError('Failed to analyze bill. Please try again.');
        }
    }

    showScanAnimation() {
        this.scanOverlay.style.display = 'flex';
        
        // Add some dynamic text updates
        const messages = [
            'Scanning document structure...',
            'Extracting line items...',
            'Checking for duplicates...',
            'Comparing against benchmarks...',
            'Calculating potential savings...'
        ];
        
        let messageIndex = 0;
        const messageElement = this.scanOverlay.querySelector('p');
        
        this.scanInterval = setInterval(() => {
            messageElement.textContent = messages[messageIndex];
            messageIndex = (messageIndex + 1) % messages.length;
        }, 1000);
    }

    hideScanAnimation() {
        this.scanOverlay.style.display = 'none';
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
        }
    }

    displayResults(data) {
        // Update total savings
        const totalSavings = data.total_savings || 0;
        document.getElementById('total-savings').textContent = `₹${totalSavings.toLocaleString()}`;

        // Update duplicate charges
        const duplicateList = document.getElementById('duplicate-list');
        if (data.duplicates && data.duplicates.length > 0) {
            duplicateList.innerHTML = data.duplicates.map(duplicate => `
                <div class="duplicate-item">
                    <h4 class="font-bold text-red-800">${duplicate.item_name} - ${duplicate.issue_type}</h4>
                    <p class="text-red-600">${duplicate.description}</p>
                    <p class="font-semibold">Overcharge: ₹${duplicate.amount.toLocaleString()}</p>
                </div>
            `).join('');
        } else {
            duplicateList.innerHTML = `
                <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                    <p class="text-green-700">✅ No duplicate charges found in your bill.</p>
                </div>
            `;
        }

        // Update benchmark analysis
        const benchmarkAnalysis = document.getElementById('benchmark-analysis');
        if (data.benchmark) {
            benchmarkAnalysis.innerHTML = `
                <p class="text-gray-700">
                    <strong>Your bill total:</strong> ₹${data.benchmark.bill_total?.toLocaleString() || 'N/A'}<br>
                    <strong>Expected range:</strong> ₹${data.benchmark.expected_min?.toLocaleString() || 'N/A'} - ₹${data.benchmark.expected_max?.toLocaleString() || 'N/A'}<br>
                    <strong>Benchmark deviation:</strong> ${data.benchmark.deviation || 'N/A'}<br><br>
                    <em>${data.benchmark.note || 'Analysis based on regional pricing data'}</em>
                </p>
            `;
        } else {
            benchmarkAnalysis.innerHTML = `
                <p class="text-gray-700">
                    Benchmark analysis will be available after processing your bill.
                </p>
            `;
        }

        // Show results section
        this.resultsSection.classList.remove('hidden');
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Download report function
window.downloadReport = function() {
    // This could be implemented to generate and download a PDF report
    alert('Report download feature coming soon! You can screenshot the results for now.');
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new BillBuster();
});