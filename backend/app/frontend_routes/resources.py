from flask import Blueprint, render_template, request, jsonify
import json
import os
from datetime import datetime

resources_bp = Blueprint(
    'frontend_resources',
    __name__,
    url_prefix='/resources',
    static_folder='../../frontend/static'
)


def load_articles():
    """Load articles from JSON file with fallback to sample data"""
    try:
        articles_path = os.path.join(os.path.dirname(
            __file__), 'content', 'articles.json')
        with open(articles_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback sample data
        return [
            {
                "id": "how-insurance-works",
                "title": "How Health Insurance Works — A Beginner's Guide",
                "summary": "Understand premiums, deductibles, copays, network hospitals, and how to choose the right coverage.",
                "category": "Basics",
                "tags": ["premium", "deductible", "network"],
                "author": "AI-MEDPAY",
                "published": "2025-01-15",
                "featured": True,
                "views": 4200,
                "url": "/resources/how-insurance-works"
            }
        ]


@resources_bp.route('/')
def resources_page():
    """Render the main resources/knowledge hub page"""
    articles = load_articles()

    # Get unique categories and tags for filters
    categories = list(set(article['category'] for article in articles))
    all_tags = []
    for article in articles:
        all_tags.extend(article['tags'])
    tags = list(set(all_tags))

    # Sort articles by views (trending) and publication date
    trending_articles = sorted(
        articles, key=lambda x: x['views'], reverse=True)[:3]
    featured_articles = [
        article for article in articles if article.get('featured', False)]

    return render_template('resources.html',
                           articles=articles,
                           categories=sorted(categories),
                           tags=sorted(tags),
                           trending_articles=trending_articles,
                           featured_articles=featured_articles)


@resources_bp.route('/api/search')
def search_articles():
    """API endpoint for searching and filtering articles"""
    articles = load_articles()

    # Get query parameters
    query = request.args.get('q', '').lower()
    category = request.args.get('category', '')
    tag = request.args.get('tag', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 6))

    # Filter articles
    filtered_articles = articles

    if query:
        filtered_articles = [
            article for article in filtered_articles
            if query in article['title'].lower() or
            query in article['summary'].lower() or
            any(query in t.lower() for t in article['tags'])
        ]

    if category:
        filtered_articles = [
            article for article in filtered_articles
            if article['category'] == category
        ]

    if tag:
        filtered_articles = [
            article for article in filtered_articles
            if tag in article['tags']
        ]

    # Pagination
    total = len(filtered_articles)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_articles = filtered_articles[start:end]

    return jsonify({
        'articles': paginated_articles,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@resources_bp.route('/<article_id>')
def article_detail(article_id):
    """Render individual article page"""
    articles = load_articles()
    article = next((a for a in articles if a['id'] == article_id), None)

    if not article:
        return render_template('404.html'), 404

    # Get related articles (same category, excluding current)
    related_articles = [
        a for a in articles
        if a['category'] == article['category'] and a['id'] != article_id
    ][:3]

    return render_template('article_detail.html',
                           article=article,
                           related_articles=related_articles)
