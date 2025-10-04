// Resources Page JavaScript
class ResourcesApp {
    constructor() {
        this.currentPage = 1;
        this.perPage = 6;
        this.currentFilters = {
            query: '',
            category: '',
            tag: ''
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initFAQ();
        this.loadArticles();
    }
    
    bindEvents() {
        // Search input with debounce
        const searchInput = document.getElementById('search-input');
        let searchTimeout;
        
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.currentFilters.query = e.target.value;
                    this.currentPage = 1;
                    this.loadArticles();
                }, 300);
            });
        }
        
        // Category filters
        const categoryFilters = document.querySelectorAll('.category-filter');
        categoryFilters.forEach(filter => {
            filter.addEventListener('change', (e) => {
                this.currentFilters.category = e.target.value;
                this.currentPage = 1;
                this.loadArticles();
            });
        });
        
        // Tag filters
        const tagFilters = document.querySelectorAll('.tag-filter');
        tagFilters.forEach(filter => {
            filter.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Toggle active state
                const isActive = filter.classList.contains('active');
                
                // Remove active from all tags
                tagFilters.forEach(f => f.classList.remove('active'));
                
                if (!isActive) {
                    filter.classList.add('active');
                    this.currentFilters.tag = filter.dataset.tag;
                } else {
                    this.currentFilters.tag = '';
                }
                
                this.currentPage = 1;
                this.loadArticles();
            });
        });
    }
    
    async loadArticles() {
        const loadingState = document.getElementById('loading-state');
        const articlesContainer = document.getElementById('articles-container');
        
        // Show loading state
        if (loadingState) loadingState.classList.remove('hidden');
        
        try {
            const params = new URLSearchParams({
                q: this.currentFilters.query,
                category: this.currentFilters.category,
                tag: this.currentFilters.tag,
                page: this.currentPage,
                per_page: this.perPage
            });
            
            const response = await fetch(`/resources/api/search?${params}`);
            const data = await response.json();
            
            this.renderArticles(data.articles);
            this.renderPagination(data);
            
        } catch (error) {
            console.error('Error loading articles:', error);
            this.showError('Failed to load articles. Please try again.');
        } finally {
            if (loadingState) loadingState.classList.add('hidden');
        }
    }
    
    renderArticles(articles) {
        const articlesGrid = document.getElementById('articles-grid');
        
        if (!articles.length) {
            articlesGrid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <div class="max-w-md mx-auto">
                        <svg class="w-24 h-24 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <h3 class="text-xl font-medium text-gray-800 mb-2">No articles found</h3>
                        <p class="text-gray-600">Try adjusting your search terms or filters.</p>
                    </div>
                </div>
            `;
            return;
        }
        
        articlesGrid.innerHTML = articles.map(article => `
            <article class="article-card bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1">
                <div class="p-6">
                    <!-- Category Badge -->
                    <div class="mb-3">
                        <span class="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                            ${article.category}
                        </span>
                        ${article.featured ? `
                            <span class="inline-block px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full ml-2">
                                ⭐ Featured
                            </span>
                        ` : ''}
                    </div>

                    <!-- Article Content -->
                    <h2 class="text-xl font-bold text-gray-800 mb-3 hover:text-blue-600 transition-colors">
                        <a href="${article.url}">${article.title}</a>
                    </h2>
                    <p class="text-gray-600 mb-4 leading-relaxed">${article.summary}</p>

                    <!-- Tags -->
                    <div class="flex flex-wrap gap-2 mb-4">
                        ${article.tags.slice(0, 3).map(tag => `
                            <span class="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">${tag}</span>
                        `).join('')}
                    </div>

                    <!-- Meta Info -->
                    <div class="flex items-center justify-between text-sm text-gray-500">
                        <div class="flex items-center space-x-4">
                            <span>By ${article.author}</span>
                            <span>${this.formatDate(article.published)}</span>
                        </div>
                        <div class="flex items-center space-x-1">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                            </svg>
                            <span>${this.formatNumber(article.views)}</span>
                        </div>
                    </div>
                </div>
            </article>
        `).join('');
        
        // Add animation to new articles
        this.animateArticles();
    }
    
    renderPagination(data) {
        const paginationContainer = document.getElementById('pagination');
        
        if (data.total_pages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let paginationHTML = '<div class="pagination">';
        
        // Previous button
        paginationHTML += `
            <button ${this.currentPage <= 1 ? 'disabled' : ''} onclick="resourcesApp.goToPage(${this.currentPage - 1})">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                </svg>
            </button>
        `;
        
        // Page numbers
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(data.total_pages, this.currentPage + 2);
        
        if (startPage > 1) {
            paginationHTML += `<button onclick="resourcesApp.goToPage(1)">1</button>`;
            if (startPage > 2) {
                paginationHTML += '<span class="px-2">...</span>';
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <button 
                    class="${i === this.currentPage ? 'active' : ''}" 
                    onclick="resourcesApp.goToPage(${i})"
                >
                    ${i}
                </button>
            `;
        }
        
        if (endPage < data.total_pages) {
            if (endPage < data.total_pages - 1) {
                paginationHTML += '<span class="px-2">...</span>';
            }
            paginationHTML += `<button onclick="resourcesApp.goToPage(${data.total_pages})">${data.total_pages}</button>`;
        }
        
        // Next button
        paginationHTML += `
            <button ${this.currentPage >= data.total_pages ? 'disabled' : ''} onclick="resourcesApp.goToPage(${this.currentPage + 1})">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
            </button>
        `;
        
        paginationHTML += '</div>';
        paginationContainer.innerHTML = paginationHTML;
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.loadArticles();
        
        // Scroll to top of articles
        const articlesContainer = document.getElementById('articles-container');
        if (articlesContainer) {
            articlesContainer.scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    initFAQ() {
        const faqQuestions = document.querySelectorAll('.faq-question');
        
        faqQuestions.forEach(question => {
            question.addEventListener('click', () => {
                const faqItem = question.parentElement;
                const answer = faqItem.querySelector('.faq-answer');
                const isOpen = question.getAttribute('aria-expanded') === 'true';
                
                // Close all other FAQs
                faqQuestions.forEach(q => {
                    if (q !== question) {
                        q.setAttribute('aria-expanded', 'false');
                        const otherAnswer = q.parentElement.querySelector('.faq-answer');
                        otherAnswer.classList.remove('show');
                        otherAnswer.classList.add('hidden');
                    }
                });
                
                // Toggle current FAQ
                if (isOpen) {
                    question.setAttribute('aria-expanded', 'false');
                    answer.classList.remove('show');
                    answer.classList.add('hidden');
                } else {
                    question.setAttribute('aria-expanded', 'true');
                    answer.classList.remove('hidden');
                    answer.classList.add('show');
                }
            });
            
            // Initialize aria-expanded
            question.setAttribute('aria-expanded', 'false');
        });
    }
    
    animateArticles() {
        // Skip animation if user prefers reduced motion
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }
        
        const articles = document.querySelectorAll('.article-card');
        articles.forEach((article, index) => {
            article.style.opacity = '0';
            article.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                article.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                article.style.opacity = '1';
                article.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }
    
    formatNumber(num) {
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'k';
        }
        return num.toString();
    }
    
    showError(message) {
        const articlesGrid = document.getElementById('articles-grid');
        articlesGrid.innerHTML = `
            <div class="col-span-full text-center py-12">
                <div class="max-w-md mx-auto">
                    <svg class="w-24 h-24 mx-auto text-red-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <h3 class="text-xl font-medium text-gray-800 mb-2">Something went wrong</h3>
                    <p class="text-gray-600 mb-4">${message}</p>
                    <button onclick="resourcesApp.loadArticles()" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                        Try Again
                    </button>
                </div>
            </div>
        `;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.resourcesApp = new ResourcesApp();
});

// Add smooth scrolling for anchor links
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

// Add keyboard navigation for accessibility
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
        const target = e.target;
        
        // FAQ questions
        if (target.classList.contains('faq-question')) {
            e.preventDefault();
            target.click();
        }
        
        // Tag filters
        if (target.classList.contains('tag-filter')) {
            e.preventDefault();
            target.click();
        }
    }
});

// Add search suggestions (optional enhancement)
class SearchSuggestions {
    constructor() {
        this.suggestions = [
            'insurance basics',
            'bill analysis',
            'claim settlement',
            'premium calculation',
            'network hospitals',
            'deductible explained',
            'copay vs coinsurance',
            'family floater',
            'critical illness',
            'maternity coverage'
        ];
        
        this.init();
    }
    
    init() {
        const searchInput = document.getElementById('search-input');
        if (!searchInput) return;
        
        // Create suggestions dropdown
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'search-suggestions absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg shadow-lg z-50 hidden';
        searchInput.parentElement.appendChild(suggestionsDiv);
        
        searchInput.addEventListener('focus', () => this.showSuggestions(searchInput, suggestionsDiv));
        searchInput.addEventListener('blur', () => {
            setTimeout(() => suggestionsDiv.classList.add('hidden'), 200);
        });
        searchInput.addEventListener('input', (e) => this.filterSuggestions(e.target.value, suggestionsDiv));
    }
    
    showSuggestions(input, container) {
        const query = input.value.toLowerCase();
        const filtered = this.suggestions.filter(s => s.includes(query));
        
        if (filtered.length && query.length > 0) {
            container.innerHTML = filtered.map(suggestion => `
                <div class="suggestion-item px-4 py-2 hover:bg-gray-50 cursor-pointer" data-suggestion="${suggestion}">
                    ${suggestion}
                </div>
            `).join('');
            
            container.classList.remove('hidden');
            
            // Add click handlers
            container.querySelectorAll('.suggestion-item').forEach(item => {
                item.addEventListener('click', () => {
                    input.value = item.dataset.suggestion;
                    container.classList.add('hidden');
                    input.dispatchEvent(new Event('input'));
                });
            });
        } else {
            container.classList.add('hidden');
        }
    }
    
    filterSuggestions(query, container) {
        if (query.length === 0) {
            container.classList.add('hidden');
            return;
        }
        
        this.showSuggestions({ value: query }, container);
    }
}

// Initialize search suggestions
document.addEventListener('DOMContentLoaded', () => {
    new SearchSuggestions();
});