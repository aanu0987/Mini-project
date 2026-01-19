document.addEventListener('DOMContentLoaded', () => {
    // Check for active session
    checkSession();

    function checkSession() {
        const userStr = localStorage.getItem('user');
        const loginBtn = document.getElementById('login-btn');
        const userProfile = document.getElementById('user-profile');
        const userNameSpan = document.getElementById('user-name');
        const logoutBtn = document.getElementById('logout-btn');

        if (userStr) {
            const user = JSON.parse(userStr);
            if (loginBtn) loginBtn.style.display = 'none';
            if (userProfile) {
                userProfile.style.display = 'flex';
                userNameSpan.innerText = `Welcome, ${user.fullname || user.name}`; // Handles both structures
            }

            if (logoutBtn) {
                logoutBtn.addEventListener('click', () => {
                    localStorage.removeItem('user');
                    localStorage.removeItem('role');
                    alert('Logged out successfully');
                    window.location.href = 'index.html';
                });
            }
        }
    }

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

                // Toggle fields based on role
                const donorFields = document.getElementById('donor-only-fields');
                const hospitalFields = document.getElementById('hospital-only-fields');
                const phoneLabel = document.getElementById('phone-label');
                const identifierLabel = document.getElementById('identifier-label');
                const identifierInput = document.getElementById('identifier');

                if (role === 'donor') {
                    if (donorFields) donorFields.style.display = 'block';
                    if (hospitalFields) hospitalFields.style.display = 'none';
                    if (phoneLabel) phoneLabel.innerText = "Mobile Number";

                    // For Login Page
                    if (identifierLabel) identifierLabel.innerText = "Email Address";
                    if (identifierInput) identifierInput.placeholder = "name@example.com";

                } else { // Hospital
                    if (donorFields) donorFields.style.display = 'none';
                    if (hospitalFields) hospitalFields.style.display = 'block';
                    if (phoneLabel) phoneLabel.innerText = "Contact Number";

                    // For Login Page
                    if (identifierLabel) identifierLabel.innerText = "Hospital ID";
                    if (identifierInput) identifierInput.placeholder = "HOSP1234";
                }
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
            let fullname = "";

            if (role === 'hospital') {
                fullname = document.getElementById('hospital-name').value;
            } else {
                fullname = document.getElementById('fullname').value;
            }

            const phone = document.getElementById('phone').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            let aadhar = null;
            let weight = null;
            let dob = null;

            // Get donor specific fields
            if (role === 'donor') {
                aadhar = document.getElementById('aadhar').value;
                weight = document.getElementById('weight').value;
                dob = document.getElementById('dob').value;
            }

            const userData = {
                role,
                fullname,
                phone,
                email,
                password,
                // donor_type: donorType, // donorType is not defined here, remove or define
                aadhar,
                weight,
                dob
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
                    let msg = `${role.charAt(0).toUpperCase() + role.slice(1)} Registration Successful!`;
                    if (data.hospital_id) {
                        msg += `\n\nIMPORTANT: Your Hospital ID is ${data.hospital_id}.\nPlease save this ID to login.`;
                    }
                    alert(msg);
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

    // Login Form Handling
    const loginForm = document.querySelector('form[action="#"]:not(#registerForm)'); // Identifying login form safely
    // Better way: check if we are on login page or look for specific structure
    // Since we don't have an ID on login form, let's look for the sign in button text or similar.
    // Assuming the only other form is login form on login.html
    const signInBtn = document.querySelector('button[type="submit"]');

    if (loginForm && signInBtn && signInBtn.innerText === 'Sign In') {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const role = document.getElementById('user-role').value;
            const identifier = document.getElementById('identifier').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch('http://localhost:5000/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role, identifier, password })
                });

                const data = await response.json();

                if (response.ok) {
                    // Save user info (in real app us tokens)
                    localStorage.setItem('user', JSON.stringify(data.user));
                    localStorage.setItem('role', role);

                    alert('Login Successful!');
                    window.location.href = 'index.html';
                } else {
                    alert('Login Failed: ' + (data.error || 'Invalid credentials'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Connection Error');
            }
        });
    }

    // Donor Display Logic
    const organDonorsList = document.getElementById('organ-donors-list');
    const bloodDonorsList = document.getElementById('blood-donors-list');

    if (organDonorsList || bloodDonorsList) {
        fetchDonors();
    }

    async function fetchDonors() {
        try {
            const response = await fetch('http://localhost:5000/api/donors');
            const donors = await response.json();

            if (organDonorsList) organDonorsList.innerHTML = '';
            if (bloodDonorsList) bloodDonorsList.innerHTML = '';

            if (donors.length === 0) {
                const noDataMsg = '<p style="color: white; grid-column: 1/-1; text-align: center;">No registered donors found yet.</p>';
                if (organDonorsList) organDonorsList.innerHTML = noDataMsg;
                if (bloodDonorsList) bloodDonorsList.innerHTML = noDataMsg;
                return;
            }

            donors.forEach(donor => {
                const donorCard = createDonorCard(donor);
                const type = donor.donor_type || 'both'; // Default back to both if undefined, though it should be set

                if (type === 'organ' || type === 'both') {
                    if (organDonorsList) organDonorsList.appendChild(donorCard.cloneNode(true));
                }
                if (type === 'blood' || type === 'both') {
                    if (bloodDonorsList) bloodDonorsList.appendChild(donorCard.cloneNode(true));
                }
            });

        } catch (error) {
            console.error('Error fetching donors:', error);
            const errorMsg = '<p style="color: #e74c3c; grid-column: 1/-1; text-align: center;">Failed to load donors. Make sure the backend is running.</p>';
            if (organDonorsList) organDonorsList.innerHTML = errorMsg;
            if (bloodDonorsList) bloodDonorsList.innerHTML = errorMsg;
        }
    }

    function createDonorCard(donor) {
        const card = document.createElement('div');
        card.className = 'glass-panel donor-card';
        card.style.display = 'flex'; // Ensure it's visible by default

        // Handle missing data gracefully
        const name = donor.fullname || 'Unknown Donor';
        const location = 'Location not set'; // We don't have location in registration yet, placeholder
        const phone = donor.phone || 'N/A';
        const lastDonated = 'Unknown'; // Not tracked yet

        card.innerHTML = `
            <div class="donor-header">
                <div class="donor-name">${name}</div>
                <div class="blood-group">?</div> 
            </div>
            <div class="donor-details">
                <div class="donor-detail-item">
                    <span>📍</span> ${location}
                </div>
                <div class="donor-detail-item">
                    <span>📞</span> ${phone}
                </div>
            </div>
            <a href="tel:${phone}" class="btn contact-btn">Contact Donor</a>
        `;
        return card;
    }
});
