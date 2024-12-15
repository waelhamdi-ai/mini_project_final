document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signup-form');
    const roleButtons = document.querySelectorAll('.role-btn');
    const doctorFields = document.querySelector('.doctor-fields');
    const patientFields = document.querySelector('.patient-fields');
    const appointmentDetails = document.getElementById('appointmentDetails');
    
    // Set minimum date for appointment
    const dateInput = document.getElementById('appointment_date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today;
    }

    // Role toggle handling
    roleButtons.forEach(button => {
        button.addEventListener('click', () => {
            toggleRole(button.dataset.role);
        });
    });

    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitButton = signupForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;

        try {
            const formData = new FormData();
            const activeRole = document.querySelector('.role-btn.active').dataset.role;
            
            // Add basic form data
            formData.append('name', document.getElementById('name').value);
            formData.append('email', document.getElementById('email').value);
            formData.append('password', document.getElementById('password').value);
            formData.append('phone', document.getElementById('phone').value);
            formData.append('role', activeRole);

            // Add profile picture if selected
            const profilePicture = document.getElementById('profile_picture').files[0];
            if (profilePicture) {
                formData.append('profile_picture', profilePicture);
            }

            // Add role-specific data
            if (activeRole === 'patient') {
                formData.append('appointment_date', document.getElementById('appointment_date').value);
                formData.append('appointment_time', document.getElementById('appointment_time').value);
                formData.append('doctor_email', document.getElementById('doctor_email').value);
                formData.append('appointment_reason', document.getElementById('appointment_reason').value);
            } else {
                formData.append('specialty', document.getElementById('specialty').value);
                formData.append('license', document.getElementById('license').value);
            }

            const response = await fetch('/signup', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.success) {
                alert('Signup successful! Please login.');
                window.location.href = '/login';
            } else {
                alert(data.message || 'Signup failed. Please try again.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during signup.');
        } finally {
            submitButton.disabled = false;
        }
    });

    const termsCheckbox = document.getElementById('terms');
    const submitButton = signupForm.querySelector('button[type="submit"]');
    const modals = document.querySelectorAll('.modal');
    const modalTriggers = document.querySelectorAll('[data-modal]');
    const closeButtons = document.querySelectorAll('.close');
    
    // Enable/disable submit button based on terms checkbox
    termsCheckbox.addEventListener('change', () => {
        submitButton.disabled = !termsCheckbox.checked;
    });

    // Modal handling
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            const modalId = trigger.getAttribute('data-modal') + 'Modal';
            document.getElementById(modalId).style.display = 'block';
        });
    });

    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            button.closest('.modal').style.display = 'none';
        });
    });

    window.addEventListener('click', (e) => {
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });

    // File input preview (for profile picture)
    const fileInput = document.getElementById('profile_picture');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                if (file.size > 5 * 1024 * 1024) { // 5MB limit
                    alert('File size must be less than 5MB');
                    this.value = '';
                    return;
                }
                
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file');
                    this.value = '';
                    return;
                }
            }
        });
    }

    // Input validation
    const inputs = signupForm.querySelectorAll('input[required]');
    inputs.forEach(input => {
        input.addEventListener('invalid', (e) => {
            e.preventDefault();
            input.classList.add('invalid');
        });

        input.addEventListener('input', () => {
            input.classList.remove('invalid');
        });
    });

    // Separate initialization function
    function initializeFormState() {
        // Get elements
        const appointmentDetails = document.getElementById('appointmentDetails');
        const doctorFields = document.querySelector('.doctor-fields');
        
        // Show appointment details and hide doctor fields by default
        if (appointmentDetails) {
            appointmentDetails.classList.remove('hidden');
            appointmentDetails.style.display = 'block';
        }
        if (doctorFields) {
            doctorFields.classList.add('hidden');
            doctorFields.style.display = 'none';
        }

        // Set patient button as active
        const patientBtn = document.querySelector('[data-role="patient"]');
        const doctorBtn = document.querySelector('[data-role="doctor"]');
        if (patientBtn && doctorBtn) {
            patientBtn.classList.add('active');
            doctorBtn.classList.remove('active');
        }

        // Set required fields for patient
        toggleRequiredFields(false);
    }

    // Call initialization immediately when page loads
    initializeFormState();

    // Set initial state
    toggleRole('patient');

    // Remove the old initialization code and replace with this new function
    function showInitialState() {
        const appointmentDetails = document.getElementById('appointmentDetails');
        const doctorFields = document.querySelector('.doctor-fields');
        const patientBtn = document.querySelector('[data-role="patient"]');
        const doctorBtn = document.querySelector('[data-role="doctor"]');

        // Show appointment details immediately
        appointmentDetails.style.display = 'block';
        appointmentDetails.classList.remove('hidden');
        
        // Hide doctor fields
        doctorFields.style.display = 'none';
        doctorFields.classList.add('hidden');

        // Set active state for patient button
        patientBtn.classList.add('active');
        doctorBtn.classList.remove('active');

        // Set required fields
        toggleRequiredFields(false);
    }

    // Call this function immediately after DOM loads
    showInitialState();

    // Remove the old toggleRole call
    // toggleRole('patient');  <- Remove this line
});

function toggleRole(role) {
    // Update buttons
    document.querySelectorAll('.role-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.role === role) {
            btn.classList.add('active');
        }
    });

    // Get the sections
    const appointmentDetails = document.getElementById('appointmentDetails');
    const doctorFields = document.querySelector('.doctor-fields');

    // Reset form fields
    document.getElementById('signup-form').reset();

    // Toggle visibility based on role with both classList and style
    if (role === 'patient') {
        if (appointmentDetails) {
            appointmentDetails.classList.remove('hidden');
            appointmentDetails.style.display = 'block';
        }
        if (doctorFields) {
            doctorFields.classList.add('hidden');
            doctorFields.style.display = 'none';
        }
    } else {
        if (appointmentDetails) {
            appointmentDetails.classList.add('hidden');
            appointmentDetails.style.display = 'none';
        }
        if (doctorFields) {
            doctorFields.classList.remove('hidden');
            doctorFields.style.display = 'block';
        }
    }

    // Update required fields
    toggleRequiredFields(role === 'doctor');
}

function toggleRequiredFields(isDoctor) {
    // Doctor fields
    const doctorFields = ['specialty', 'license'];
    // Client fields
    const clientFields = ['appointment_date', 'appointment_time', 'doctor_email', 'appointment_reason'];
    
    doctorFields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.required = isDoctor;
        }
    });

    clientFields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.required = !isDoctor;
        }
    });
}
