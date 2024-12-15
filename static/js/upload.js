document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('uploadForm');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('medical_image');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const removeButton = document.getElementById('removeImage');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const closeModal = document.getElementsByClassName('modal-close')[0];

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight);
    });

    function highlight() {
        dropZone.classList.add('dragover');
    }

    function unhighlight() {
        dropZone.classList.remove('dragover');
    }

    // Handle file selection
    dropZone.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileSelect);
    removeButton.addEventListener('click', removeImage);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        handleFile(file);
    }

    function handleFileSelect(e) {
        const file = this.files[0];
        handleFile(file);
    }

    function handleFile(file) {
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                previewContainer.style.display = 'block';
                dropZone.style.display = 'none';
            };
            reader.readAsDataURL(file);
        } else {
            showToast('Please select a valid image file', 'error');
        }
    }

    function removeImage() {
        imagePreview.src = '';
        previewContainer.style.display = 'none';
        dropZone.style.display = 'block';
        fileInput.value = '';
    }

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!fileInput.files[0]) {
            showToast('Please select an image', 'error');
            return;
        }

        const formData = new FormData(this);
        loadingSpinner.style.display = 'flex';  // Show spinner

        try {
            const response = await fetch('/upload_medical_image', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                let message = `Image uploaded successfully!\nAI Prediction: ${data.prediction}\nConfidence: ${(data.confidence * 100).toFixed(2)}%`;
                showToast(message, 'success');
                setTimeout(() => {
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    }
                }, 2000);
            } else {
                showToast(data.message || 'Upload failed', 'error');
            }
        } catch (error) {
            showToast('Upload failed: ' + error, 'error');
        } finally {
            loadingSpinner.style.display = 'none';  // Hide spinner
        }
    });

    // Modal handling
    window.viewImage = function(url) {
        modal.style.display = 'block';
        modalImg.src = url;
    }

    closeModal.onclick = function() {
        modal.style.display = 'none';
    }

    // Toast notification
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
});

// Add this function to handle page load
window.addEventListener('load', function() {
    // Hide loading spinner when page loads
    const loadingSpinner = document.getElementById('loadingSpinner');
    if (loadingSpinner) {
        loadingSpinner.style.display = 'none';
    }
});