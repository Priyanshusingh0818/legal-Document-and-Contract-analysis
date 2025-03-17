document.addEventListener('DOMContentLoaded', function() {
    // Toggle full text of clauses
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const fullText = this.nextElementSibling;
            const isHidden = fullText.classList.contains('hidden');
            
            fullText.classList.toggle('hidden');
            this.textContent = isHidden ? 'Hide Full Text' : 'Show Full Text';
        });
    });
    
    // Highlight risk terms in the clause text
    const riskLines = document.querySelectorAll('.risk-lines-list li');
    
    riskLines.forEach(line => {
        const lineText = line.querySelector('.line-text');
        const riskTermsEl = line.querySelector('.risk-terms');
        
        if (riskTermsEl) {
            const riskTermsText = riskTermsEl.textContent;
            const riskTerms = riskTermsText.replace('Risk terms: ', '').split(', ');
            
            let highlightedText = lineText.textContent;
            
            riskTerms.forEach(term => {
                // Escape special regex characters
                const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const regex = new RegExp(`(${escapedTerm})`, 'gi');
                highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
            });
            
            lineText.innerHTML = highlightedText;
        }
    });
    
    // Calculate and update risk percentages in summary
    const totalClauses = parseInt(document.querySelector('.stat:first-child p').textContent);
    const highRisk = parseInt(document.querySelector('.high-risk p').textContent);
    const mediumRisk = parseInt(document.querySelector('.medium-risk p').textContent);
    const lowRisk = parseInt(document.querySelector('.low-risk p').textContent);
    
    if (totalClauses > 0) {
        // Create function to append percentage to stats
        function appendPercentage(selector, count) {
            const percent = ((count / totalClauses) * 100).toFixed(1);
            const el = document.querySelector(selector + ' p');
            el.innerHTML = `${count} <span class="percent">(${percent}%)</span>`;
        }
        
        appendPercentage('.high-risk', highRisk);
        appendPercentage('.medium-risk', mediumRisk);
        appendPercentage('.low-risk', lowRisk);
    }
});