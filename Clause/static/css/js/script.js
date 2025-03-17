document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const selectedFileDiv = document.getElementById('selected-file');
    const uploadForm = document.getElementById('upload-form');
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    // Handle selected files
    fileInput.addEventListener('change', handleFiles, false);
    
    // Prevent defaults for drag events
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        dropArea.classList.add('dragover');
    }
    
    function unhighlight() {
        dropArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length) {
            fileInput.files = files;
            handleFiles();
        }
    }
    
    function handleFiles() {
        const file = fileInput.files[0];
        if (file) {
            // Check if file is PDF or image
            const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
            if (!validTypes.includes(file.type)) {
                alert('Please upload a PDF or image file (PNG, JPG)');
                fileInput.value = '';
                selectedFileDiv.innerHTML = '<p>No file selected</p>';
                return;
            }
            
            // Display file information
            const fileSize = (file.size / 1024 / 1024).toFixed(2); // Convert to MB
            selectedFileDiv.innerHTML = `
                <p><strong>${file.name}</strong> (${fileSize} MB)</p>
                <span class="file-type">${file.type}</span>
            `;
        } else {
            selectedFileDiv.innerHTML = '<p>No file selected</p>';
        }
    }
    
    // Submit form validation
    uploadForm.addEventListener('submit', function(e) {
        if (!fileInput.files.length) {
            e.preventDefault();
            alert('Please select a file to analyze');
        }
    });
});