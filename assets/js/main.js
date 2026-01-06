document.addEventListener('DOMContentLoaded', () => {
    // Animate stats numbers
    const stats = document.querySelectorAll('.stat-number');

    const animateValue = (obj, start, end, duration) => {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start).toLocaleString();
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };

    // Simulate different stats for demo purposes
    // In a real app, these would come from a backend API
    const targets = {
        'donors': 12543,
        'hospitals': 487,
        'saved': 8932
    };

    stats.forEach(stat => {
        const type = stat.getAttribute('data-target');
        if (targets[type]) {
            animateValue(stat, 0, targets[type], 2000);
        }
    });

    // Login Tab Switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const roleInput = document.getElementById('user-role');

    if (tabBtns.length > 0) {
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active class from all
                tabBtns.forEach(b => b.classList.remove('active'));
                // Add active to clicked
                btn.classList.add('active');

                // Update hidden input for form submission
                const role = btn.getAttribute('data-role');
                if (roleInput) roleInput.value = role;

                console.log(`Switched to ${role} login`);
            });
        });
    }

    // Donor Search Functionality
    const districtSearch = document.getElementById('districtSearch');
    if (districtSearch) {
        districtSearch.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const donorCards = document.querySelectorAll('.donor-card');

            donorCards.forEach(card => {
                // Find the location text within the card
                // The structure is .donor-details -> .donor-detail-item (first one usually has location)
                const locationItem = card.querySelector('.donor-detail-item');
                // Or safely get all text content
                const cardText = card.textContent.toLowerCase();

                // More precise: check specifically for location icon or text if possible
                // For now, simple text search is robust enough
                if (cardText.includes(searchTerm)) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Registration Form Handling
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const role = document.getElementById('user-role').value;
            const fullname = document.getElementById('fullname').value;
            const phone = document.getElementById('phone').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            const userData = {
                role,
                fullname,
                phone,
                email,
                password
            };

            try {
                // Determine API endpoint (we use a single endpoint /register which handles both based on role)
                // Python Flask runs on port 5000 by default
                const response = await fetch('http://localhost:5000/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(userData)
                });

                const data = await response.json();

                if (response.ok) {
                    alert(`${role.charAt(0).toUpperCase() + role.slice(1)} Registration Successful!`);
                    window.location.href = 'login.html';
                } else {
                    alert('Registration Failed: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Connection Error: Is the backend server running? (See Console)');
            }
        });
    }
});
