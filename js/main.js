const API_BASE = 'http://localhost:5000';

function getToken() {
  return localStorage.getItem('token');
}

function authHeaders() {
  const token = getToken();
  return token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('user');
  window.location.href = 'login.html';
}

document.addEventListener('DOMContentLoaded', () => {
<<<<<<< HEAD
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
=======
  document.getElementById('logout-btn')?.addEventListener('click', logout);

  initRegister();
  initLogin();
  initAdminRegister();
  initAdminDashboard();
  initHospitalDashboard();
  initDonorDashboard();
  initPublicDonorList();
});

function initRegister() {
  const form = document.getElementById('registerForm');
  if (!form) return;

  const tabBtns = document.querySelectorAll('.tab-btn');
  const roleInput = document.getElementById('user-role');
  const donorFields = document.getElementById('donor-fields');
  const hospitalFields = document.getElementById('hospital-fields');

  tabBtns.forEach(btn => btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const role = btn.dataset.role;
    roleInput.value = role;
    donorFields.style.display = role === 'donor' ? 'block' : 'none';
    hospitalFields.style.display = role === 'hospital' ? 'block' : 'none';
  }));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const role = roleInput.value;
    const payload = {
      role,
      fullname: document.getElementById('fullname').value,
      phone: document.getElementById('phone').value,
      email: document.getElementById('email').value,
      password: document.getElementById('password').value,
    };

    if (role === 'donor') {
      Object.assign(payload, {
        donor_type: 'blood',
        aadhar: document.getElementById('aadhar').value,
        weight: document.getElementById('weight').value,
        dob: document.getElementById('dob').value,
        blood_group: document.getElementById('blood_group').value,
        last_donation_date: document.getElementById('last_donation_date').value,
      });
    } else {
      Object.assign(payload, {
        address: document.getElementById('address').value,
        contact_person: document.getElementById('contact_person').value,
      });
    }

    const res = await fetch(`${API_BASE}/auth/register`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    const data = await res.json();
    if (res.ok) {
      alert('Registration submitted. Wait for admin approval and login ID email.');
      window.location.href = 'login.html';
    } else {
      alert(data.error || 'Registration failed');
    }
  });
}

function initLogin() {
  const form = document.getElementById('loginForm');
  if (!form) return;

  const tabBtns = document.querySelectorAll('.tab-btn');
  const roleInput = document.getElementById('user-role');
  const adminEmailGroup = document.getElementById('admin-email-group');
  const loginIdGroup = document.getElementById('login-id-group');

  tabBtns.forEach(btn => btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const role = btn.dataset.role;
    roleInput.value = role;
    adminEmailGroup.style.display = role === 'admin' ? 'block' : 'none';
    loginIdGroup.style.display = role === 'admin' ? 'none' : 'block';
  }));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const role = roleInput.value;
    const payload = role === 'admin'
      ? { role, email: document.getElementById('admin-email').value, password: document.getElementById('login-password').value }
      : { role, login_id: document.getElementById('login-id').value, password: document.getElementById('login-password').value };

    const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) return alert(data.error || 'Login failed');

    localStorage.setItem('token', data.token);
    localStorage.setItem('role', role);
    localStorage.setItem('user', JSON.stringify(data.user));

    if (role === 'admin') window.location.href = 'admin.html';
    if (role === 'hospital') window.location.href = 'hospital_dashboard.html';
    if (role === 'donor') window.location.href = 'donor_dashboard.html';
  });
}

function initAdminRegister() {
  const form = document.getElementById('adminRegisterForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      fullname: document.getElementById('admin-name').value,
      email: document.getElementById('admin-register-email').value,
      password: document.getElementById('admin-register-password').value,
    };

    const res = await fetch(`${API_BASE}/auth/admin/register`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    alert(res.ok ? 'Admin registered successfully' : (data.error || 'Admin registration failed'));
    if (res.ok) form.reset();
  });
}

async function initAdminDashboard() {
  const container = document.getElementById('pending-users');
  if (!container) return;

  const res = await fetch(`${API_BASE}/admin/pending-users`, { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) {
    container.innerHTML = `<p>${data.error || 'Unauthorized'}</p>`;
    return;
  }

  const drawCards = (users, type) => users.map(user => `
    <div class="glass-panel" style="padding:15px; margin:12px 0;">
      <b>${user.fullname}</b> (${user.email})<br>
      Phone: ${user.phone || 'N/A'}
      <div style="margin-top:8px; display:flex; gap:8px;">
        <button class="btn" onclick="verifyUser('${type}', '${user._id}', 'approve')">Approve</button>
        <button class="btn btn-secondary" onclick="rejectPrompt('${type}', '${user._id}')">Reject</button>
      </div>
    </div>
  `).join('');

  container.innerHTML = `<h3>Donors</h3>${drawCards(data.donors, 'donor') || '<p>No pending donors.</p>'}<h3>Hospitals</h3>${drawCards(data.hospitals, 'hospital') || '<p>No pending hospitals.</p>'}`;
}

window.rejectPrompt = function (type, userId) {
  const reason = prompt('Enter rejection reason');
  if (!reason) return;
  verifyUser(type, userId, 'reject', reason);
};

window.verifyUser = async function (user_type, user_id, action, rejection_reason = '') {
  const res = await fetch(`${API_BASE}/admin/verify-user`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ user_type, user_id, action, rejection_reason }),
  });
  const data = await res.json();
  alert(data.message || data.error);
  if (res.ok) window.location.reload();
};

async function initHospitalDashboard() {
  const details = document.getElementById('hospital-details');
  if (!details) return;

  const res = await fetch(`${API_BASE}/hospital/dashboard`, { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) {
    details.innerHTML = data.error || 'Unauthorized';
    return;
  }

  const hospital = data.hospital;
  details.innerHTML = `
    <h3>${hospital.hospital_name || hospital.fullname}</h3>
    <p>Email: ${hospital.email}</p>
    <p>Phone: ${hospital.phone}</p>
    <p>Login ID: ${hospital.login_id}</p>
  `;

  document.getElementById('hospital-notifications').innerHTML = `<h3>Recent Notifications</h3>${(data.notifications || []).map(n => `<div class="glass-panel" style="padding:12px; margin:8px 0;">${n.message}</div>`).join('') || '<p>No notifications yet.</p>'}`;

  document.getElementById('send-request-btn').addEventListener('click', () => sendHospitalEvent('request'));
  document.getElementById('send-received-btn').addEventListener('click', () => sendHospitalEvent('received'));
}

async function sendHospitalEvent(kind) {
  const request_type = document.getElementById('request-type').value;
  const details = document.getElementById('request-details').value;
  const endpoint = kind === 'request' ? '/hospital/request' : '/hospital/received';
  const payload = kind === 'request' ? { request_type, details } : { request_type };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  alert(data.message || data.error);
}

async function initDonorDashboard() {
  const donation = document.getElementById('last-donation');
  if (!donation) return;

  const res = await fetch(`${API_BASE}/donor/dashboard`, { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) {
    donation.innerHTML = data.error || 'Unauthorized';
    return;
  }

  donation.innerHTML = `<h3>Last Donation Date</h3><p>${data.last_donation_date || 'No record available'}</p>`;
  document.getElementById('donor-notifications').innerHTML = (data.notifications || []).map(n => `<div class="glass-panel" style="padding:12px; margin:8px 0;">${n.message}</div>`).join('') || '<p>No notifications.</p>';
  document.getElementById('hospital-contacts').innerHTML = (data.hospital_contacts || []).map(h => `<div class="glass-panel" style="padding:12px; margin:8px 0;">${h.hospital_name}<br>${h.phone || ''}<br>${h.email || ''}</div>`).join('') || '<p>No hospitals available.</p>';
}

async function initPublicDonorList() {
  const bloodDonorsList = document.getElementById('blood-donors-list');
  if (!bloodDonorsList) return;

  const res = await fetch(`${API_BASE}/api/donors`);
  const data = await res.json();
  if (!res.ok) {
    bloodDonorsList.innerHTML = '<p>Unable to load donors.</p>';
    return;
  }

  bloodDonorsList.innerHTML = data.map(d => `
    <div class="glass-panel donor-card" style="padding:15px;">
      <b>${d.fullname}</b><br>
      Blood Group: ${d.blood_group || 'N/A'}<br>
      Phone: ${d.phone || 'N/A'}<br>
      Last Donation: ${d.last_donation_date || 'N/A'}
    </div>
  `).join('') || '<p>No approved blood donors found.</p>';

  const organ = document.getElementById('organ-donors-list');
  if (organ) organ.innerHTML = '<p>Only blood donor registration is enabled.</p>';
}
>>>>>>> 8fdc6419965a389e519d555259ecf47be6c7e872
