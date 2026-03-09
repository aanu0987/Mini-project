const API_BASE = window.location.origin;
const AUTH_REQUIRED_MESSAGE = 'Please login to access Find Donors and Dashboard.';

function getToken() {
  return localStorage.getItem('token');
}

function authHeaders() {
  const token = getToken();
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}


function isLoggedIn() {
  return Boolean(getToken());
}

function updateAuthButtonState() {
  const loginBtn = document.getElementById('login-btn');
  if (!loginBtn) return;

  if (isLoggedIn()) {
    loginBtn.textContent = 'Logout';
    loginBtn.setAttribute('href', '#');
    loginBtn.addEventListener('click', (event) => {
      event.preventDefault();
      logout();
    });
  } else {
    loginBtn.textContent = 'Login / Register';
  }
}

function guardProtectedPage() {
  const path = window.location.pathname.toLowerCase();
  const isProtected =
    path.endsWith('/dashboard') ||
    path.endsWith('/dashboard.html') ||
    path.endsWith('/blood_donors') ||
    path.endsWith('/blood_donors.html');

  if (isProtected && !isLoggedIn()) {
    alert(AUTH_REQUIRED_MESSAGE);
    window.location.href = '/login';
    return true;
  }

  return false;
}

function guardProtectedNavLinks() {
  const protectedSelectors = [
    'a[href="/dashboard"]',
    'a[href="dashboard.html"]',
    'a[href="/blood_donors"]',
    'a[href="blood_donors.html"]',
  ];

  protectedSelectors.forEach((selector) => {
    document.querySelectorAll(selector).forEach((link) => {
      link.addEventListener('click', (event) => {
        if (isLoggedIn()) return;
        event.preventDefault();
        alert(AUTH_REQUIRED_MESSAGE);
        window.location.href = '/login';
      });
    });
  });
}

async function logout() {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: authHeaders(),
    });
  } catch (_) {
    // Ignore network errors and continue local logout.
  }

  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('logout-btn')?.addEventListener('click', logout);

  if (guardProtectedPage()) return;
  guardProtectedNavLinks();
  updateAuthButtonState();

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
  const donorNameGroup = document.getElementById('donor-name-group');

  tabBtns.forEach((btn) =>
    btn.addEventListener('click', () => {
      tabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const role = btn.dataset.role;
      roleInput.value = role;
      if (donorFields) donorFields.style.display = role === 'donor' ? 'block' : 'none';
      if (hospitalFields) hospitalFields.style.display = role === 'hospital' ? 'block' : 'none';
      if (donorNameGroup) donorNameGroup.style.display = role === 'donor' ? 'block' : 'none';
      const fullnameInput = document.getElementById('fullname');
      const hospitalNameInput = document.getElementById('hospital-name');
      if (fullnameInput) fullnameInput.required = role === 'donor';
      if (hospitalNameInput) hospitalNameInput.required = role === 'hospital';
    })
  );

  document.getElementById('fullname')?.setAttribute('required', 'required');
  document.getElementById('hospital-name')?.removeAttribute('required');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const role = roleInput.value;

    let res;
    if (role === 'donor') {
      const payload = {
        role,
        fullname: document.getElementById('fullname')?.value || '',
        phone: document.getElementById('phone')?.value,
        email: document.getElementById('email')?.value,
        password: document.getElementById('password')?.value,
        city: document.getElementById('city')?.value,
        donor_type: 'blood',
        aadhar: document.getElementById('aadhar')?.value,
        weight: document.getElementById('weight')?.value,
        dob: document.getElementById('dob')?.value,
        blood_group: document.getElementById('blood_group')?.value,
        last_donation_date: document.getElementById('last_donation_date')?.value,
      };

      res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
    } else {
      const formData = new FormData();
      formData.append('role', role);
      formData.append('fullname', document.getElementById('hospital-name')?.value || '');
      formData.append('phone', document.getElementById('phone')?.value || '');
      formData.append('email', document.getElementById('email')?.value || '');
      formData.append('password', document.getElementById('password')?.value || '');
      formData.append('city', document.getElementById('city')?.value || '');
      formData.append('license_number', document.getElementById('license_number')?.value || '');
      formData.append('address', document.getElementById('address')?.value || '');

      const fileInput = document.getElementById('certificate_pdf');
      if (fileInput?.files?.[0]) {
        formData.append('certificate_pdf', fileInput.files[0]);
      }

      const token = getToken();
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers,
        body: formData,
      });
    }
    const data = await res.json();
    if (res.ok) {
      alert(data.message || 'Registration successful');
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

  tabBtns.forEach((btn) =>
    btn.addEventListener('click', () => {
      tabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const role = btn.dataset.role;
      roleInput.value = role;
      if (adminEmailGroup) adminEmailGroup.style.display = role === 'admin' ? 'block' : 'none';
      if (loginIdGroup) loginIdGroup.style.display = role === 'admin' ? 'none' : 'block';
    })
  );

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const role = roleInput.value;
    const password = document.getElementById('password')?.value || document.getElementById('login-password')?.value;
    const identifier = document.getElementById('identifier')?.value || document.getElementById('login-id')?.value;

    const payload =
      role === 'admin'
        ? { role, email: document.getElementById('admin-email')?.value, password }
        : { role, login_id: identifier, email: identifier, password };

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      if (data.error && data.error.toLowerCase().includes('register')) {
        return alert('Register as donor or hospital');
      }
      return alert(data.error || 'Login failed');
    }

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
    alert(res.ok ? 'Admin registered successfully' : data.error || 'Admin registration failed');
    if (res.ok) form.reset();
  });
}

async function initAdminDashboard() {
  const pendingContainer = document.getElementById('pending-users');
  if (!pendingContainer) return;
  const allUsersContainer = document.getElementById('all-users');
  const notificationsContainer = document.getElementById('admin-notifications');

  const [pendingRes, allUsersRes, notesRes] = await Promise.all([
    fetch(`${API_BASE}/admin/pending-users`, { headers: authHeaders() }),
    fetch(`${API_BASE}/admin/all-users`, { headers: authHeaders() }),
    fetch(`${API_BASE}/admin/notifications`, { headers: authHeaders() }),
  ]);

  const pendingData = await pendingRes.json();
  const allUsersData = await allUsersRes.json();
  const notesData = await notesRes.json();

  if (!pendingRes.ok) {
    pendingContainer.innerHTML = `<p>${pendingData.error || 'Unauthorized'}</p>`;
    return;
  }

  const drawCards = (users, type) =>
    users
      .map(
        (user) => `
      <div class="glass-panel" style="padding:15px; margin:12px 0;">
        <b>${user.fullname}</b> (${user.email})<br>
        Phone: ${user.phone || 'N/A'}
        <div style="margin-top:8px; display:flex; gap:8px;">
          <button class="btn" onclick="verifyUser('${type}', '${user._id}', 'approve')">Approve</button>
          <button class="btn btn-secondary" onclick="rejectPrompt('${type}', '${user._id}')">Reject</button>
        </div>
      </div>
    `
      )
      .join('');

  pendingContainer.innerHTML = `<h3>Pending Hospital Verifications</h3>${drawCards(
    pendingData.hospitals || [],
    'hospital'
  ) || '<p>No pending hospitals.</p>'}`;

  if (allUsersContainer) {
    const drawUserLine = (u) => `${u.fullname} (${u.email}) - ${u.status || 'N/A'} ${u.login_id ? `| ID: ${u.login_id}` : ''}`;
    allUsersContainer.innerHTML = `
      <h3>Donors (${(allUsersData.donors || []).length})</h3>
      ${(allUsersData.donors || []).map((u) => `<div style="margin:6px 0;">${drawUserLine(u)}</div>`).join('') || '<p>No donor records.</p>'}
      <h3 style="margin-top:16px;">Hospitals (${(allUsersData.hospitals || []).length})</h3>
      ${(allUsersData.hospitals || []).map((u) => `<div style="margin:6px 0;">${drawUserLine(u)}</div>`).join('') || '<p>No hospital records.</p>'}
    `;
  }

  if (notificationsContainer) {
    notificationsContainer.innerHTML = (notesData.notifications || [])
      .map(
        (n) => `
        <div class="glass-panel" style="padding:12px; margin:8px 0;">
          <b>${n.type || 'notification'}</b> - ${n.message}<br>
          <small>${n.created_at || ''}</small>
        </div>
      `
      )
      .join('') || '<p>No notifications yet.</p>';
  }
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

  document.getElementById('hospital-notifications').innerHTML =
    `<h3>Recent Notifications</h3>${(data.notifications || [])
      .map((n) => `<div class="glass-panel" style="padding:12px; margin:8px 0;">${n.message}</div>`)
      .join('') || '<p>No notifications yet.</p>'}`;

  document.getElementById('organ-request-btn').addEventListener('click', () => sendHospitalEvent('request', 'organ'));
  document.getElementById('blood-request-btn').addEventListener('click', () => sendHospitalEvent('request', 'blood'));
  document.getElementById('send-received-btn').addEventListener('click', () => sendHospitalEvent('received'));
}

async function sendHospitalEvent(kind, fixedType = '') {
  const request_type = fixedType || document.getElementById('request-type').value;
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
  const ageCard = document.getElementById('donor-age');
  if (ageCard) ageCard.innerHTML = `<h3>Age</h3><p>${data.age ?? 'Not available'}</p>`;
  const donor = data.donor || {};
  const weightInput = document.getElementById('edit-weight');
  const dobInput = document.getElementById('edit-dob');
  const lastDonationInput = document.getElementById('edit-last-donation');
  if (weightInput) weightInput.value = donor.weight || '';
  if (dobInput) dobInput.value = donor.dob || '';
  if (lastDonationInput) lastDonationInput.value = donor.last_donation_date || '';

  document.getElementById('hospital-contacts').innerHTML = (data.hospital_contacts || [])
    .map(
      (h) => `<div class="glass-panel" style="padding:12px; margin:8px 0;">${h.hospital_name}<br>${h.phone || ''}<br>${h.email || ''}</div>`
    )
    .join('') || '<p>No hospitals available.</p>';

  const form = document.getElementById('donor-edit-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        weight: document.getElementById('edit-weight')?.value,
        dob: document.getElementById('edit-dob')?.value,
        last_donation_date: document.getElementById('edit-last-donation')?.value,
      };
      const updateRes = await fetch(`${API_BASE}/donor/profile`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      const updateData = await updateRes.json();
      alert(updateData.message || updateData.error);
      if (updateRes.ok) window.location.reload();
    });
  }
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

  bloodDonorsList.innerHTML =
    data
      .map(
        (d) => `
    <div class="glass-panel donor-card" style="padding:15px;">
      <b>${d.fullname}</b><br>
      Blood Group: ${d.blood_group || 'N/A'}<br>
      Phone: ${d.phone || 'N/A'}<br>
      Last Donation: ${d.last_donation_date || 'N/A'}
    </div>
  `
      )
      .join('') || '<p>No approved blood donors found.</p>';

  const organ = document.getElementById('organ-donors-list');
  if (organ) organ.innerHTML = '<p>Only blood donor registration is enabled.</p>';
}
