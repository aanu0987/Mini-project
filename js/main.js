document.addEventListener('DOMContentLoaded', () => {
    checkSession();

    function checkSession() {
        const userStr = localStorage.getItem('user');
        const loginBtn = document.getElementById('login-btn');
        const userProfile = document.getElementById('user-profile');
        const userNameSpan = document.getElementById('user-name');
        const logoutBtn = document.getElementById('logout-btn');
        const dashboardLink = document.getElementById('dashboard-link');

        if (userStr) {
            const user = JSON.parse(userStr);
            if (loginBtn) loginBtn.style.display = 'none';
            if (userProfile) {
                userProfile.style.display = 'flex';
                userNameSpan.innerText = `Welcome, ${user.fullname || user.name}`;
            }

            if (dashboardLink) {
                const role = localStorage.getItem('role');
                if (role === 'hospital') {
                    dashboardLink.textContent = 'Hospital Dashboard';
                } else if (role === 'admin') {
                    dashboardLink.textContent = 'Admin Dashboard';
                } else {
                    dashboardLink.textContent = 'My Dashboard';
                }
            }
        }
    }

    // Tab switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const roleInput = document.getElementById('user-role');

    if (tabBtns.length > 0) {
        const toggleRoleFields = (role) => {
            const donorFields = document.getElementById('donor-only-fields');
            const hospitalFields = document.getElementById('hospital-only-fields');
            const phoneLabel = document.getElementById('phone-label');
            const identifierLabel = document.getElementById('identifier-label');
            const identifierInput = document.getElementById('identifier');
            const fullnameInput = document.getElementById('fullname');
            const aadharInput = document.getElementById('aadhar');
            const weightInput = document.getElementById('weight');
            const dobInput = document.getElementById('dob');
            const hospitalNameInput = document.getElementById('hospital-name');
            const licenseInput = document.getElementById('license_number');
            const bloodGroupSelect = document.getElementById('blood_group');

            if (role === 'donor') {
                if (donorFields) donorFields.style.display = 'block';
                if (hospitalFields) hospitalFields.style.display = 'none';
                if (phoneLabel) phoneLabel.innerText = 'Mobile Number';
                if (identifierLabel) identifierLabel.innerText = 'Email Address';
                if (identifierInput) identifierInput.placeholder = 'name@example.com';
                if (identifierInput) identifierInput.type = 'email';

                if (fullnameInput) fullnameInput.required = true;
                if (aadharInput) aadharInput.required = true;
                if (weightInput) weightInput.required = true;
                if (dobInput) dobInput.required = true;
                if (bloodGroupSelect) bloodGroupSelect.required = true;
                if (hospitalNameInput) hospitalNameInput.required = false;
                if (licenseInput) licenseInput.required = false;
            } else {
                if (donorFields) donorFields.style.display = 'none';
                if (hospitalFields) hospitalFields.style.display = 'block';
                if (phoneLabel) phoneLabel.innerText = 'Contact Number';
                if (identifierLabel) identifierLabel.innerText = 'Hospital ID';
                if (identifierInput) identifierInput.placeholder = 'HOSP1234';
                if (identifierInput) identifierInput.type = 'text';

                if (fullnameInput) fullnameInput.required = false;
                if (aadharInput) aadharInput.required = false;
                if (weightInput) weightInput.required = false;
                if (dobInput) dobInput.required = false;
                if (bloodGroupSelect) bloodGroupSelect.required = false;
                if (hospitalNameInput) hospitalNameInput.required = true;
                if (licenseInput) licenseInput.required = true;
            }
        };

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const role = btn.getAttribute('data-role');
                if (roleInput) roleInput.value = role;
                toggleRoleFields(role);
            });
        });

        if (roleInput) {
            toggleRoleFields(roleInput.value);
        }
    }

    // Registration Form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const role = document.getElementById('user-role').value;
            let fullname = "";
            let license_number = "";

            if (role === 'hospital') {
                fullname = document.getElementById('hospital-name').value;
                license_number = document.getElementById('license_number')?.value || '';
            } else {
                fullname = document.getElementById('fullname').value;
            }

            const phone = document.getElementById('phone').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const city = document.getElementById('city').value;

            let aadhar = null;
            let weight = null;
            let dob = null;
            let blood_group = null;

            if (role === 'donor') {
                aadhar = document.getElementById('aadhar').value;
                weight = document.getElementById('weight').value;
                dob = document.getElementById('dob').value;
                blood_group = document.getElementById('blood_group').value;
            }

            const userData = {
                role,
                fullname,
                phone,
                email,
                password,
                city,
                aadhar,
                weight,
                dob,
                blood_group,
                license_number
            };

            try {
                const response = await fetch('http://localhost:5000/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
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

    // Login Form
    const loginForm = document.querySelector('form[action="#"]:not(#registerForm)');
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
                    body: JSON.stringify({ role, identifier, password }),
                    credentials: 'include'
                });

                const data = await response.json();

                if (response.ok) {
                    localStorage.setItem('user', JSON.stringify(data.user));
                    localStorage.setItem('role', role);

                    alert('Login Successful!');
                    
                    // Redirect based on role
                    if (role === 'admin') {
                        window.location.href = 'dashboard.html';
                    } else if (role === 'hospital') {
                        window.location.href = 'dashboard.html';
                    } else {
                        window.location.href = 'index.html';
                    }
                } else {
                    alert('Login Failed: ' + (data.error || 'Invalid credentials'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Connection Error');
            }
        });
    }
});