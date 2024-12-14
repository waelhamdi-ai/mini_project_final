// Add session check function
function checkSession() {
    fetch('/check_session')
        .then(response => response.json())
        .then(data => {
            if (data.logged_in) {
                window.location.href = data.redirect_url;
            }
        })
        .catch(error => console.error('Error checking session:', error));
}

// Check session on page load
document.addEventListener('DOMContentLoaded', checkSession);

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const submitButton = loginForm.querySelector('button[type="submit"]');

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        submitButton.disabled = true;
        submitButton.textContent = 'Signing in...';

        const formData = {
            email: document.getElementById('email').value,
            password: document.getElementById('password').value
        };

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            console.log('Server response:', data); // Debug log

            if (data.success) {
                window.location.href = data.redirect_url;
            } else {
                alert(data.message || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('An error occurred. Please try again.');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Sign In';
        }
    });
});
