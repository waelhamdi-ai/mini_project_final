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
            roleButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            const isDoctor = button.dataset.role === 'doctor';
            doctorFields.classList.toggle('hidden', !isDoctor);
            appointmentDetails.classList.toggle('hidden', isDoctor);
            
            // Update required fields
            toggleRequiredFields(isDoctor);
        });
    });

    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitButton = signupForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;

        try {
            const activeRole = document.querySelector('.role-btn.active').dataset.role;
            const formData = {
                name: document.getElementById('name').value,
                email: document.getElementById('email').value,
                password: document.getElementById('password').value,
                phone: document.getElementById('phone').value,
                role: activeRole
            };

            if (activeRole === 'patient') {
                // Add appointment details
                formData.appointment_date = document.getElementById('appointment_date').value;
                formData.appointment_time = document.getElementById('appointment_time').value;
                formData.doctor_email = document.getElementById('doctor_email').value;
                formData.appointment_reason = document.getElementById('appointment_reason').value;
            } else {
                // Add doctor details
                formData.specialty = document.getElementById('specialty').value;
                formData.experience = document.getElementById('license').value;
            }

            console.log('Sending signup data:', formData); // Debug log

            const response = await fetch('/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
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
});

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
