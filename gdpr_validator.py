from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import os
import json
from datetime import datetime

app = Flask(__name__)

# Initialize Groq client (set your API key as environment variable)
# Get free API key from: https://console.groq.com
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

GDPR_ARTICLES = {
    "15": "Right of Access - Subject has right to obtain confirmation of data processing and access to personal data",
    "16": "Right to Rectification - Subject has right to correct inaccurate personal data",
    "17": "Right to Erasure (Right to be Forgotten) - Subject has right to request deletion of personal data",
    "18": "Right to Restriction of Processing - Subject has right to restrict processing under certain conditions",
    "19": "Right to Data Portability - Subject has right to receive data in structured, machine-readable format",
    "20": "Right to Object - Subject has right to object to processing for legitimate interests or direct marketing"
}

COMPLIANCE_PROMPT = """You are a GDPR compliance expert. Analyze the following request/response scenario and validate compliance with GDPR Article {article}.

Article {article} Context: {context}

Scenario:
Request Type: {request_type}
Organization Response: {org_response}
Response Time: {response_time} days
Additional Context: {additional_context}

Provide a detailed compliance validation including:
1. Compliance Status (Compliant/Non-Compliant/Partially Compliant)
2. Key Requirements Met
3. Key Requirements Missed (if any)
4. Specific Recommendations
5. Risk Level (Low/Medium/High)

Format your response as JSON with keys: status, requirements_met, requirements_missed, recommendations, risk_level, explanation"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>GDPR Articles 15-20 Compliance Validator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            color: #718096;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .article-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .article-card {
            padding: 15px;
            background: #f7fafc;
            border-radius: 10px;
            border: 2px solid #e2e8f0;
            cursor: pointer;
            transition: all 0.3s;
        }
        .article-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .article-card.selected {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .article-num {
            font-weight: bold;
            font-size: 1.3em;
            margin-bottom: 5px;
        }
        .article-desc {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 8px;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            width: 100%;
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .result {
            margin-top: 30px;
            padding: 25px;
            border-radius: 12px;
            background: #f7fafc;
            border-left: 5px solid #667eea;
        }
        .status {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .status.compliant { background: #c6f6d5; color: #22543d; }
        .status.non-compliant { background: #fed7d7; color: #742a2a; }
        .status.partially-compliant { background: #feebc8; color: #7c2d12; }
        .section {
            margin: 20px 0;
        }
        .section h3 {
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        .section ul {
            margin-left: 20px;
            line-height: 1.8;
        }
        .risk-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
        }
        .risk-low { background: #c6f6d5; color: #22543d; }
        .risk-medium { background: #feebc8; color: #7c2d12; }
        .risk-high { background: #fed7d7; color: #742a2a; }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            background: #fed7d7;
            color: #742a2a;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 GDPR Compliance Validator</h1>
        <p class="subtitle">Automated validation for Articles 15-20 using AI</p>
        
        <div class="form-group">
            <label>Select GDPR Article:</label>
            <div class="article-grid" id="articleGrid">
                <div class="article-card" data-article="15">
                    <div class="article-num">Article 15</div>
                    <div class="article-desc">Right of Access</div>
                </div>
                <div class="article-card" data-article="16">
                    <div class="article-num">Article 16</div>
                    <div class="article-desc">Right to Rectification</div>
                </div>
                <div class="article-card" data-article="17">
                    <div class="article-num">Article 17</div>
                    <div class="article-desc">Right to Erasure</div>
                </div>
                <div class="article-card" data-article="18">
                    <div class="article-num">Article 18</div>
                    <div class="article-desc">Restriction of Processing</div>
                </div>
                <div class="article-card" data-article="19">
                    <div class="article-num">Article 19</div>
                    <div class="article-desc">Data Portability</div>
                </div>
                <div class="article-card" data-article="20">
                    <div class="article-num">Article 20</div>
                    <div class="article-desc">Right to Object</div>
                </div>
            </div>
            <input type="hidden" id="selectedArticle" required>
        </div>

        <div class="form-group">
            <label for="requestType">Request Type:</label>
            <select id="requestType" required>
                <option value="">Select request type...</option>
                <option value="data_access">Data Access Request</option>
                <option value="data_rectification">Data Rectification Request</option>
                <option value="data_erasure">Data Erasure Request</option>
                <option value="processing_restriction">Processing Restriction Request</option>
                <option value="data_portability">Data Portability Request</option>
                <option value="objection">Objection to Processing</option>
            </select>
        </div>

        <div class="form-group">
            <label for="orgResponse">Organization's Response:</label>
            <textarea id="orgResponse" placeholder="Describe how the organization responded to the data subject's request..." required></textarea>
        </div>

        <div class="form-group">
            <label for="responseTime">Response Time (days):</label>
            <input type="number" id="responseTime" min="0" placeholder="e.g., 25" required>
        </div>

        <div class="form-group">
            <label for="additionalContext">Additional Context (optional):</label>
            <textarea id="additionalContext" placeholder="Any additional information about the scenario, exceptions claimed, etc."></textarea>
        </div>

        <button onclick="validateCompliance()">Validate Compliance</button>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 15px; color: #667eea; font-weight: 600;">Analyzing compliance...</p>
        </div>

        <div id="result"></div>
    </div>

    <script>
        let selectedArticle = null;

        document.querySelectorAll('.article-card').forEach(card => {
            card.addEventListener('click', function() {
                document.querySelectorAll('.article-card').forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                selectedArticle = this.dataset.article;
                document.getElementById('selectedArticle').value = selectedArticle;
            });
        });

        async function validateCompliance() {
            if (!selectedArticle) {
                alert('Please select a GDPR article');
                return;
            }

            const requestType = document.getElementById('requestType').value;
            const orgResponse = document.getElementById('orgResponse').value;
            const responseTime = document.getElementById('responseTime').value;
            const additionalContext = document.getElementById('additionalContext').value;

            if (!requestType || !orgResponse || !responseTime) {
                alert('Please fill in all required fields');
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';

            try {
                const response = await fetch('/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        article: selectedArticle,
                        request_type: requestType,
                        org_response: orgResponse,
                        response_time: parseInt(responseTime),
                        additional_context: additionalContext
                    })
                });

                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('result').innerHTML = `<div class="error">${data.error}</div>`;
                } else {
                    displayResult(data);
                }
            } catch (error) {
                document.getElementById('result').innerHTML = `<div class="error">Error: ${error.message}</div>`;
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        function displayResult(data) {
            const statusClass = data.status.toLowerCase().replace(/ /g, '-');
            const riskClass = `risk-${data.risk_level.toLowerCase()}`;
            
            let requirementsMetHtml = '';
            if (data.requirements_met && data.requirements_met.length > 0) {
                requirementsMetHtml = '<ul>' + data.requirements_met.map(r => `<li>${r}</li>`).join('') + '</ul>';
            }

            let requirementsMissedHtml = '';
            if (data.requirements_missed && data.requirements_missed.length > 0) {
                requirementsMissedHtml = '<ul>' + data.requirements_missed.map(r => `<li>${r}</li>`).join('') + '</ul>';
            }

            let recommendationsHtml = '';
            if (data.recommendations && data.recommendations.length > 0) {
                recommendationsHtml = '<ul>' + data.recommendations.map(r => `<li>${r}</li>`).join('') + '</ul>';
            }

            const html = `
                <div class="result">
                    <div class="status ${statusClass}">${data.status}</div>
                    
                    <div class="section">
                        <h3>Risk Level: <span class="risk-badge ${riskClass}">${data.risk_level}</span></h3>
                    </div>

                    ${requirementsMetHtml ? `
                    <div class="section">
                        <h3>✅ Requirements Met:</h3>
                        ${requirementsMetHtml}
                    </div>
                    ` : ''}

                    ${requirementsMissedHtml ? `
                    <div class="section">
                        <h3>❌ Requirements Missed:</h3>
                        ${requirementsMissedHtml}
                    </div>
                    ` : ''}

                    ${recommendationsHtml ? `
                    <div class="section">
                        <h3>💡 Recommendations:</h3>
                        ${recommendationsHtml}
                    </div>
                    ` : ''}

                    <div class="section">
                        <h3>📋 Detailed Explanation:</h3>
                        <p style="line-height: 1.8;">${data.explanation}</p>
                    </div>
                </div>
            `;

            document.getElementById('result').innerHTML = html;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/validate', methods=['POST'])
def validate():
    try:
        data = request.json
        article = data.get('article')
        request_type = data.get('request_type')
        org_response = data.get('org_response')
        response_time = data.get('response_time')
        additional_context = data.get('additional_context', 'None provided')

        if not all([article, request_type, org_response, response_time is not None]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Prepare prompt for Groq
        prompt = COMPLIANCE_PROMPT.format(
            article=article,
            context=GDPR_ARTICLES.get(article, 'Unknown article'),
            request_type=request_type,
            org_response=org_response,
            response_time=response_time,
            additional_context=additional_context
        )

        # Call Groq API (using llama-3.3-70b-versatile for best results on free tier)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a GDPR compliance expert. Provide detailed, accurate compliance analysis in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2000
        )

        response_text = chat_completion.choices[0].message.content
        
        # Extract JSON from response
        try:
            # Try to find JSON in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: create structured response from text
            result = {
                "status": "Analysis Complete",
                "requirements_met": [],
                "requirements_missed": [],
                "recommendations": [],
                "risk_level": "Medium",
                "explanation": response_text
            }

        # Ensure all required fields exist
        result.setdefault('status', 'Unknown')
        result.setdefault('requirements_met', [])
        result.setdefault('requirements_missed', [])
        result.setdefault('recommendations', [])
        result.setdefault('risk_level', 'Medium')
        result.setdefault('explanation', 'No explanation provided')

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Validation error: {str(e)}'}), 500

@app.route('/articles', methods=['GET'])
def get_articles():
    return jsonify(GDPR_ARTICLES)

if __name__ == '__main__':
    # Check if API key is set
    if not os.environ.get("GROQ_API_KEY"):
        print("\n⚠️  WARNING: GROQ_API_KEY environment variable not set!")
        print("Get your free API key from: https://console.groq.com")
        print("Then set it using: export GROQ_API_KEY='your-api-key'\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)