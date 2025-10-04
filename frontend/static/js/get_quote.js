// Get Quote Form JavaScript
class GetQuoteForm {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initFileUpload();
        this.updateUI();
    }
    
    bindEvents() {
        // Navigation buttons
        document.getElementById('next-btn').addEventListener('click', () => this.nextStep());
        document.getElementById('prev-btn').addEventListener('click', () => this.prevStep());
        document.getElementById('submit-btn').addEventListener('click', () => this.submitForm());
        
        // Coverage type change
        document.querySelectorAll('input[name="coverage-type"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const familyDetails = document.getElementById('family-details');
                if (e.target.value === 'family') {
                    familyDetails.classList.remove('hidden');
                } else {
                    familyDetails.classList.add('hidden');
                }
            });
        });
        
        // Form validation on input
        document.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
        
        // Pre-existing conditions exclusive selection
        document.querySelectorAll('input[name="conditions"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.value === 'none' && e.target.checked) {
                    // Uncheck all other conditions
                    document.querySelectorAll('input[name="conditions"]:not([value="none"])').forEach(cb => {
                        cb.checked = false;
                    });
                } else if (e.target.value !== 'none' && e.target.checked) {
                    // Uncheck "none" if any other condition is selected
                    document.querySelector('input[name="conditions"][value="none"]').checked = false;
                }
            });
        });
    }
    
    initFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-upload');
        const uploadedFilesContainer = document.getElementById('uploaded-files');
        
        // Click to browse
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }
    
    handleFiles(files) {
        const uploadedFilesContainer = document.getElementById('uploaded-files');
        
        Array.from(files).forEach(file => {
            // Validate file
            if (!this.validateFile(file)) return;
            
            // Create file element
            const fileElement = this.createFileElement(file);
            uploadedFilesContainer.appendChild(fileElement);
            
            // Store file reference
            if (!this.formData.files) this.formData.files = [];
            this.formData.files.push(file);
        });
    }
    
    validateFile(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
        
        if (file.size > maxSize) {
            this.showError('File size must be less than 10MB');
            return false;
        }
        
        if (!allowedTypes.includes(file.type)) {
            this.showError('Only PDF, JPG, and PNG files are allowed');
            return false;
        }
        
        return true;
    }
    
    createFileElement(file) {
        const div = document.createElement('div');
        div.className = 'uploaded-file';
        div.innerHTML = `
            <div class="file-info">
                <div class="file-icon">${this.getFileIcon(file.type)}</div>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <p>${this.formatFileSize(file.size)}</p>
                </div>
            </div>
            <button type="button" class="remove-file" onclick="this.parentElement.remove()">
                ✕
            </button>
        `;
        return div;
    }
    
    getFileIcon(type) {
        if (type === 'application/pdf') return '📄';
        if (type.startsWith('image/')) return '🖼️';
        return '📎';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    nextStep() {
        if (this.validateCurrentStep()) {
            this.collectCurrentStepData();
            
            if (this.currentStep < this.totalSteps) {
                this.currentStep++;
                this.updateUI();
                this.animateStepTransition();
            }
        }
    }
    
    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateUI();
            this.animateStepTransition();
        }
    }
    
    updateUI() {
        // Update progress indicator
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNumber < this.currentStep) {
                step.classList.add('completed');
            } else if (stepNumber === this.currentStep) {
                step.classList.add('active');
            }
        });
        
        // Update form steps
        document.querySelectorAll('.form-step').forEach((step, index) => {
            step.classList.remove('active');
            if (index + 1 === this.currentStep) {
                step.classList.add('active');
            }
        });
        
        // Update navigation buttons
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const submitBtn = document.getElementById('submit-btn');
        
        prevBtn.classList.toggle('hidden', this.currentStep === 1);
        
        if (this.currentStep === this.totalSteps) {
            nextBtn.classList.add('hidden');
            submitBtn.classList.remove('hidden');
        } else {
            nextBtn.classList.remove('hidden');
            submitBtn.classList.add('hidden');
        }
        
        // Update next button text
        if (this.currentStep === this.totalSteps - 1) {
            nextBtn.textContent = 'Review & Submit →';
        } else {
            nextBtn.textContent = 'Next →';
        }
    }
    
    animateStepTransition() {
        // Scroll to top of form
        document.querySelector('.form-container').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
    
    validateCurrentStep() {
        const currentStepElement = document.getElementById(`step-${this.currentStep}`);
        const requiredFields = currentStepElement.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    validateField(field) {
        this.clearFieldError(field);
        
        // Check if field is required and empty
        if (field.hasAttribute('required') && !field.value.trim()) {
            this.showFieldError(field, 'This field is required');
            return false;
        }
        
        // Email validation
        if (field.type === 'email' && field.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                this.showFieldError(field, 'Please enter a valid email address');
                return false;
            }
        }
        
        // Phone validation
        if (field.type === 'tel' && field.value) {
            const phoneRegex = /^[6-9]\d{9}$/;
            if (!phoneRegex.test(field.value.replace(/\s+/g, ''))) {
                this.showFieldError(field, 'Please enter a valid 10-digit phone number');
                return false;
            }
        }
        
        // Age validation
        if (field.id === 'age' && field.value) {
            const age = parseInt(field.value);
            if (age < 18 || age > 100) {
                this.showFieldError(field, 'Age must be between 18 and 100');
                return false;
            }
        }
        
        // Radio button validation
        if (field.type === 'radio' && field.hasAttribute('required')) {
            const radioGroup = document.querySelectorAll(`input[name="${field.name}"]`);
            const isChecked = Array.from(radioGroup).some(radio => radio.checked);
            if (!isChecked) {
                this.showFieldError(field, 'Please select an option');
                return false;
            }
        }
        
        this.showFieldSuccess(field);
        return true;
    }
    
    showFieldError(field, message) {
        field.classList.add('field-error');
        field.classList.remove('field-success');
        
        // Remove existing error message
        const existingError = field.parentNode.querySelector('.error-message');
        if (existingError) existingError.remove();
        
        // Add error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }
    
    showFieldSuccess(field) {
        field.classList.remove('field-error');
        field.classList.add('field-success');
    }
    
    clearFieldError(field) {
        field.classList.remove('field-error');
        
        // Remove error message
        const errorMessage = field.parentNode.querySelector('.error-message');
        if (errorMessage) errorMessage.remove();
    }
    
    collectCurrentStepData() {
        const currentStepElement = document.getElementById(`step-${this.currentStep}`);
        const inputs = currentStepElement.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            if (input.type === 'radio' || input.type === 'checkbox') {
                if (input.checked) {
                    if (input.type === 'checkbox') {
                        if (!this.formData[input.name]) this.formData[input.name] = [];
                        this.formData[input.name].push(input.value);
                    } else {
                        this.formData[input.name] = input.value;
                    }
                }
            } else {
                this.formData[input.id] = input.value;
            }
        });
    }
    
    async submitForm() {
        if (!this.validateCurrentStep()) return;
        
        this.collectCurrentStepData();
        
        const submitBtn = document.getElementById('submit-btn');
        const originalText = submitBtn.textContent;
        
        // Show loading state
        submitBtn.textContent = 'Processing...';
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        
        try {
            // Prepare form data
            const formData = new FormData();
            
            // Add form fields
            Object.keys(this.formData).forEach(key => {
                if (key !== 'files') {
                    if (Array.isArray(this.formData[key])) {
                        this.formData[key].forEach(value => {
                            formData.append(key, value);
                        });
                    } else {
                        formData.append(key, this.formData[key]);
                    }
                }
            });
            
            // Add files
            if (this.formData.files) {
                this.formData.files.forEach(file => {
                    formData.append('files', file);
                });
            }
            
            // Submit to server
            const response = await fetch('/get-quote/submit', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccessMessage();
                // Redirect to recommendations page
                setTimeout(() => {
                    window.location.href = `/recommendation?quote_id=${result.quote_id}`;
                }, 2000);
            } else {
                throw new Error(result.error || 'Something went wrong');
            }
            
        } catch (error) {
            this.showError(error.message);
        } finally {
            // Reset button state
            submitBtn.textContent = originalText;
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    }
    
    showSuccessMessage() {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = `
            <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-green-800">Success!</h3>
                        <p class="mt-1 text-sm text-green-700">Your quote request has been submitted. Redirecting to your personalized recommendations...</p>
                    </div>
                </div>
            </div>
        `;
        
        const currentStep = document.getElementById(`step-${this.currentStep}`);
        currentStep.insertBefore(successDiv, currentStep.firstChild);
    }
    
    showError(message) {
        // Remove existing error messages
        document.querySelectorAll('.error-banner').forEach(banner => banner.remove());
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-banner';
        errorDiv.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Error</h3>
                        <p class="mt-1 text-sm text-red-700">${message}</p>
                    </div>
                </div>
            </div>
        `;
        
        const currentStep = document.getElementById(`step-${this.currentStep}`);
        currentStep.insertBefore(errorDiv, currentStep.firstChild);
    }
    
    // Auto-save to localStorage
    saveProgress() {
        localStorage.setItem('getQuoteProgress', JSON.stringify({
            currentStep: this.currentStep,
            formData: this.formData
        }));
    }
    
    loadProgress() {
        const saved = localStorage.getItem('getQuoteProgress');
        if (saved) {
            const progress = JSON.parse(saved);
            this.currentStep = progress.currentStep;
            this.formData = progress.formData;
            
            // Restore form values
            Object.keys(this.formData).forEach(key => {
                const field = document.getElementById(key);
                if (field) field.value = this.formData[key];
            });
            
            this.updateUI();
        }
    }
}

// Initialize form when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new GetQuoteForm();
});

// Add smooth scrolling for better UX
document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href^="#"]');
    if (link) {
        e.preventDefault();
        const target = document.querySelector(link.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    }
});

// Add keyboard navigation
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type !== 'submit') {
        e.preventDefault();
        const nextBtn = document.getElementById('next-btn');
        const submitBtn = document.getElementById('submit-btn');
        
        if (!nextBtn.classList.contains('hidden')) {
            nextBtn.click();
        } else if (!submitBtn.classList.contains('hidden')) {
            submitBtn.click();
        }
    }
});