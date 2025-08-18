from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)

@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.now().year,
        'current_endpoint': request.endpoint 
    }

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if request.method == 'POST':
        
        user_data = request.form.to_dict()
        
        # Dummy example recommendation data
        plans = [
            {
                'name': 'Optima Secure',
                'provider': 'HDFC ERGO',
                'type': user_data.get('insurance_type', 'Health'),
                'premium': '6935', 
                'coverage': '3L to 1Cr', 
                'claim_ratio': '98',
                'co_pay': '10-20', 
                'chart_base64': None  
            },
            {
                'name': 'Complete Health Insurance ',
                'provider': 'ICICI Lombard',
                'type': user_data.get('insurance_type', 'Health'),
                'premium': '6000 to 15000',
                'coverage': '3L to 3Cr', 
                'claim_ratio': '98', 
                'co_pay': '10',
                'chart_base64': None
            }
        ]

        return render_template('recommendation.html', plans=plans)
    
    return render_template('compare.html')

@app.route('/dashboard')
def dashboard():
    # This URL is now managed from the backend.
    # In a production environment, this could be dynamically generated
    # with user-specific filters or security tokens.
    looker_studio_url = "https://lookerstudio.google.com/embed/reporting/430242fa-4162-4950-a984-336c8744b2c6/page/p_3b1b329p3c"
    return render_template('dashboard.html', looker_studio_url=looker_studio_url)

@app.route('/recommendation')
def recommendation():
    # Optional: direct access if needed
    return render_template('recommendation.html', plans=[])

@app.route('/resources')
def resources():
    return render_template('resources.html')

if __name__ == '__main__':
    app.run(debug=True)