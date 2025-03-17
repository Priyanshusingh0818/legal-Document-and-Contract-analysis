import os
import re
import nltk
import spacy
import pytesseract
import numpy as np
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from collections import defaultdict
from werkzeug.utils import secure_filename
from flask import Flask, request, render_template, jsonify, redirect, url_for

# Load NLP models
nlp = spacy.load("en_core_web_sm")
nltk.download('punkt')

class ContractAnalyzer:
    def __init__(self, risk_model_path=None):
        self.risk_keywords = self.load_risk_keywords()
        self.clause_patterns = self.get_clause_patterns()
        self.ag_risk_keywords = self.load_ag_risk_keywords()
        self.recommendations = self.load_recommendations()
        
    def load_risk_keywords(self):
        # Dictionary of risky terms by category
        return {
            "penalties": ["penalty", "forfeit", "terminate", "liable", "damages", "fee", "fines"],
            "time_constraints": ["within", "deadline", "by the date", "expiration", "timely", "promptly"],
            "payment_terms": ["interest", "late fee", "overdue", "additional charge", "surcharge"],
            "liability": ["indemnify", "hold harmless", "waive", "disclaim", "liability", "obligation"],
            "termination": ["cancel", "early termination", "breach", "default", "revoke", "void"]
        }
    
    def load_ag_risk_keywords(self):
        # Agricultural-specific risk terms
        return {
            "crop_terms": ["crop failure", "yield threshold", "harvest date", "planting season", "crop insurance"],
            "land_use": ["easement", "right of way", "encumbrance", "rezoning", "development rights"],
            "weather_clauses": ["drought", "flood", "force majeure", "act of god", "weather event"],
            "price_terms": ["market price", "fixed price", "minimum price", "price floor", "commodity pricing"],
            "equipment": ["machinery breakdown", "equipment lease", "maintenance responsibility", "repair costs"],
            "pesticides": ["chemical use", "application rate", "restricted substances", "runoff", "contamination"],
            "water_rights": ["irrigation", "water allocation", "water restriction", "aquifer", "water table"]
        }
    
    def load_recommendations(self):
        # Recommendations for different risk categories
        return {
            "penalties": "Consider negotiating lower penalty fees or longer grace periods before penalties apply.",
            "time_constraints": "Ensure deadlines are realistic for agricultural operations which may be affected by weather and seasonal factors.",
            "payment_terms": "Request payment terms that align with your harvest and sales cycle to improve cash flow.",
            "liability": "Consider adding mutual indemnification or limiting liability to direct damages only.",
            "termination": "Add provisions for weather-related or crop failure exceptions to termination clauses.",
            "crop_terms": "Ensure crop failure provisions include reasonable force majeure exceptions for weather events.",
            "land_use": "Verify that land use restrictions don't prevent normal agricultural operations or future improvements.",
            "weather_clauses": "Expand force majeure definitions to include specific agricultural weather concerns.",
            "price_terms": "Add minimum price guarantees or consider price adjustment mechanisms tied to input costs.",
            "equipment": "Clarify responsibility for equipment maintenance and unexpected repair costs.",
            "pesticides": "Ensure flexibility for managing pest outbreaks while maintaining compliance requirements.",
            "water_rights": "Secure adequate water access rights and clarify drought contingency provisions."
        }
    
    def get_clause_patterns(self):
        # Common patterns for identifying clauses in contracts
        return [
            r"Section\s+(\d+\.\d+|\d+)",
            r"Clause\s+(\d+\.\d+|\d+)",
            r"Article\s+(\d+\.\d+|\d+)",
            r"^\s*(\d+\.\d+)\s+",
            r"^\s*(\d+\.\d+\.\d+)\s+",
            r"^\s*(\d+)\.\s+"
        ]
    
    def extract_text(self, document_path):
        """Extract text from PDF or image"""
        if document_path.lower().endswith('.pdf'):
            reader = PdfReader(document_path)
            text = ""
            line_map = []
            line_number = 1
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    lines = page_text.split('\n')
                    for line in lines:
                        text += line + '\n'
                        # Store mapping of text position to line number and page
                        line_map.append({
                            "line_number": line_number,
                            "page": page_num,
                            "text": line.strip(),
                            "char_start": len(text) - len(line) - 1,
                            "char_end": len(text) - 1
                        })
                        line_number += 1
            
            return text, line_map
        else:
            # Assume it's an image
            text = pytesseract.image_to_string(document_path)
            lines = text.split('\n')
            line_map = []
            
            char_pos = 0
            for i, line in enumerate(lines, 1):
                line_map.append({
                    "line_number": i,
                    "page": 1,
                    "text": line.strip(),
                    "char_start": char_pos,
                    "char_end": char_pos + len(line)
                })
                char_pos += len(line) + 1  # +1 for newline
                
            return text, line_map
    
    def identify_clauses(self, text, line_map):
        """Split text into clauses using patterns"""
        clauses = []
        current_clause = {"id": "", "text": "", "lines": [], "char_start": 0, "char_end": 0}
        paragraphs = []
        
        # Split text into paragraphs while preserving character positions
        current_paragraph = ""
        current_para_start = 0
        
        lines = text.split('\n')
        char_pos = 0
        
        for line in lines:
            if not line.strip():  # Empty line indicates paragraph break
                if current_paragraph:
                    paragraphs.append({
                        "text": current_paragraph,
                        "char_start": current_para_start,
                        "char_end": char_pos - 1
                    })
                    current_paragraph = ""
                    current_para_start = char_pos + 1
            else:
                if not current_paragraph:
                    current_para_start = char_pos
                current_paragraph += " " + line.strip() if current_paragraph else line.strip()
            
            char_pos += len(line) + 1  # +1 for newline
        
        # Add the last paragraph
        if current_paragraph:
            paragraphs.append({
                "text": current_paragraph,
                "char_start": current_para_start,
                "char_end": char_pos - 1
            })
        
        # Now identify clauses from paragraphs
        for i, paragraph in enumerate(paragraphs):
            para_text = paragraph["text"]
            # Check if paragraph starts with a clause pattern
            for pattern in self.clause_patterns:
                match = re.match(pattern, para_text.strip())
                if match:
                    # If we found a clause and already have one in progress, save it
                    if current_clause["id"]:
                        # Find which lines are in this clause
                        current_clause["lines"] = [
                            line for line in line_map 
                            if line["char_start"] >= current_clause["char_start"] and 
                               line["char_end"] <= current_clause["char_end"]
                        ]
                        clauses.append(current_clause)
                    
                    # Start a new clause
                    current_clause = {
                        "id": match.group(1),
                        "text": para_text.strip(),
                        "char_start": paragraph["char_start"],
                        "char_end": paragraph["char_end"],
                        "lines": []
                    }
                    break
            else:
                # If no pattern matched, append to current clause
                if current_clause["id"]:
                    current_clause["text"] += "\n" + para_text.strip()
                    current_clause["char_end"] = paragraph["char_end"]
        
        # Add the last clause
        if current_clause["id"]:
            current_clause["lines"] = [
                line for line in line_map 
                if line["char_start"] >= current_clause["char_start"] and 
                   line["char_end"] <= current_clause["char_end"]
            ]
            clauses.append(current_clause)
        
        return clauses
    
    def analyze_risk(self, clause_text):
        """Analyze risk level of a clause"""
        risk_score = 0
        risk_factors = defaultdict(list)
        
        # Check for standard risk keywords
        for category, keywords in self.risk_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', clause_text.lower()):
                    risk_score += 1
                    risk_factors[category].append(keyword)
        
        # Check for agriculture-specific risk keywords
        for category, keywords in self.ag_risk_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', clause_text.lower()):
                    risk_score += 1.5  # Higher weight for ag-specific terms
                    risk_factors[category].append(keyword)
        
        # Check for numeric values that might indicate penalties
        percentages = re.findall(r'(\d+(?:\.\d+)?\s*%)', clause_text)
        dollar_amounts = re.findall(r'(?:\$|USD)\s*(\d+(?:,\d+)*(?:\.\d+)?)', clause_text)
        
        if percentages:
            risk_score += len(percentages)
            risk_factors["percentages"] = percentages
        
        if dollar_amounts:
            risk_score += len(dollar_amounts)
            risk_factors["amounts"] = dollar_amounts
        
        # Analyze sentence structure using spaCy
        doc = nlp(clause_text[:10000])  # Limit to prevent memory issues
        
        # Check for conditional statements (if-then)
        if_statements = [sent.text for sent in doc.sents if "if" in sent.text.lower()]
        if if_statements:
            risk_score += len(if_statements) * 0.5
            risk_factors["conditionals"] = if_statements[:3]  # Limit to first 3
        
        # Check for negative language
        negations = [token.text for token in doc if token.dep_ == "neg"]
        if negations:
            risk_score += len(negations) * 0.5
            risk_factors["negations"] = negations
        
        # Generate recommendations
        recommendations = []
        for category in risk_factors:
            if category in self.recommendations:
                recommendations.append({
                    "category": category,
                    "recommendation": self.recommendations[category],
                    "terms": risk_factors[category]
                })
        
        return {
            "risk_score": risk_score,
            "risk_factors": dict(risk_factors),
            "recommendations": recommendations
        }
    
    def find_risk_lines(self, clause, risk_factors):
        """Identify specific lines containing risk factors"""
        risk_lines = []
        
        # Flatten all risk keywords
        all_keywords = []
        for category, terms in risk_factors.items():
            if isinstance(terms, list):
                all_keywords.extend(terms)
        
        # Check each line for keywords
        for line_info in clause["lines"]:
            line_text = line_info["text"].lower()
            found_terms = []
            
            for keyword in all_keywords:
                if isinstance(keyword, str) and keyword.lower() in line_text:
                    found_terms.append(keyword)
            
            if found_terms:
                risk_lines.append({
                    "line_number": line_info["line_number"],
                    "page": line_info["page"],
                    "text": line_info["text"],
                    "terms": found_terms
                })
        
        return risk_lines
    
    def analyze_contract(self, document_path):
        """Main function to analyze contract"""
        # Extract text from document
        text, line_map = self.extract_text(document_path)
        
        # Identify clauses
        clauses = self.identify_clauses(text, line_map)
        
        # Analyze each clause
        analysis = []
        for clause in clauses:
            risk_analysis = self.analyze_risk(clause["text"])
            risk_lines = self.find_risk_lines(clause, risk_analysis["risk_factors"])
            
            analysis.append({
                "clause_id": clause["id"],
                "text": clause["text"],
                "risk_score": risk_analysis["risk_score"],
                "risk_factors": risk_analysis["risk_factors"],
                "recommendations": risk_analysis["recommendations"],
                "risk_lines": risk_lines
            })
        
        # Sort by risk score
        analysis.sort(key=lambda x: x["risk_score"], reverse=True)
        
        return {
            "clauses": analysis,
            "total_clauses": len(clauses),
            "high_risk_count": sum(1 for item in analysis if item["risk_score"] > 5),
            "medium_risk_count": sum(1 for item in analysis if 2 < item["risk_score"] <= 5),
            "low_risk_count": sum(1 for item in analysis if item["risk_score"] <= 2)
        }


# Flask Application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file and (file.filename.lower().endswith('.pdf') or 
                file.filename.lower().endswith(('.png', '.jpg', '.jpeg'))):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze the contract
        analyzer = ContractAnalyzer()
        results = analyzer.analyze_contract(filepath)
        
        return render_template('results.html', results=results, filename=filename)
    
    return redirect(request.url)

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and (file.filename.lower().endswith('.pdf') or 
                file.filename.lower().endswith(('.png', '.jpg', '.jpeg'))):filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
        
        # Analyze the contract
    analyzer = ContractAnalyzer()
    results = analyzer.analyze_contract(filepath)
        
    return jsonify(results)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)