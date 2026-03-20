const API_BASE = window.location.origin;
const AUTH_REQUIRED_MESSAGE = 'Please login to access Find Donors and Dashboard.';

function getToken() {
  return localStorage.getItem('token');
}

function authHeaders() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function isLoggedIn() {
  return Boolean(getToken());
}

function updateAuthButtonState() {
  const loginBtn = document.getElementById('login-btn');
  const userProfile = document.getElementById('user-profile');
  const userName = document.getElementById('user-name');
  
  if (!loginBtn || !userProfile || !userName) return;

  if (isLoggedIn()) {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      const user = JSON.parse(userStr);
      loginBtn.style.display = 'none';
      userProfile.style.display = 'flex';
      userName.textContent = `Welcome, ${user.fullname || 'User'}`;
    }
  } else {
    loginBtn.style.display = 'inline-block';
    userProfile.style.display = 'none';
  }
}

function guardProtectedPage() {
  const path = window.location.pathname.toLowerCase();
  const isProtected =
    path.includes('/dashboard') ||
    path.includes('/blood_donors') ||
    path.includes('/admin') ||
    path.includes('/hospital_dashboard') ||
    path.includes('/donor_dashboard');

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
    'a[href="/blood_donors"]',
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
  } catch (_) {}

  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('user');
  window.location.href = '/logout';
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
  const fullnameInput = document.getElementById('fullname');
  const donorRequiredIds = ['gender', 'bloodGroup'];
  const hospitalRequiredIds = ['hospital-name', 'license_number', 'address', 'certificate_pdf'];

  function toggleRegistrationMode(role) {
    if (donorFields) donorFields.style.display = role === 'donor' ? 'block' : 'none';
    if (hospitalFields) hospitalFields.style.display = role === 'hospital' ? 'block' : 'none';
    if (donorNameGroup) donorNameGroup.style.display = role === 'donor' ? 'block' : 'none';
    if (fullnameInput) fullnameInput.required = role === 'donor';

    donorRequiredIds.forEach((id) => {
      const field = document.getElementById(id);
      if (field) field.required = role === 'donor';
    });

    hospitalRequiredIds.forEach((id) => {
      const field = document.getElementById(id);
      if (field) field.required = role === 'hospital';
    });
  }

  toggleRegistrationMode(roleInput.value || 'donor');

  tabBtns.forEach((btn) =>
    btn.addEventListener('click', () => {
      tabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const role = btn.dataset.role;
      roleInput.value = role;
      toggleRegistrationMode(role);
    })
  );

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
        blood_group: document.getElementById('bloodGroup')?.value,
        last_donation_date: document.getElementById('last-donation-date')?.value,
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

      res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        body: formData,
      });
    }
    
    const data = await res.json();
    if (res.ok) {
      alert(data.message || 'Registration successful');
      window.location.href = '/login';
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
    const password = document.getElementById('password')?.value;
    const identifier = document.getElementById('identifier')?.value;

    const payload = role === 'admin'
      ? { role, email: document.getElementById('admin-email')?.value, password }
      : { role, login_id: identifier, email: identifier, password };

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    
    const data = await res.json();
    if (!res.ok) {
      return alert(data.error || 'Login failed');
    }

    localStorage.setItem('token', data.token);
    localStorage.setItem('role', role);
    localStorage.setItem('user', JSON.stringify(data.user));

    if (role === 'admin') window.location.href = '/admin';
    if (role === 'hospital') window.location.href = '/hospital_dashboard';
    if (role === 'donor') window.location.href = '/donor_dashboard';
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
  const pendingCount = document.getElementById('pending-count');

  try {
    const [pendingRes, allUsersRes, notesRes] = await Promise.all([
      fetch(`${API_BASE}/admin/pending-users`, { headers: authHeaders() }),
      fetch(`${API_BASE}/admin/all-users`, { headers: authHeaders() }),
      fetch(`${API_BASE}/admin/notifications`, { headers: authHeaders() }),
    ]);

    const pendingData = await pendingRes.json();
    const allUsersData = await allUsersRes.json();
    const notesData = await notesRes.json();

    if (!pendingRes.ok) {
      pendingContainer.innerHTML = `<p class="alert alert-danger">${pendingData.error || 'Unauthorized'}</p>`;
      return;
    }

    // Update pending count
    if (pendingCount) {
      pendingCount.textContent = (pendingData.hospitals || []).length;
    }

    // Display pending hospitals
    pendingContainer.innerHTML = '';
    const hospitals = pendingData.hospitals || [];
    
    if (hospitals.length === 0) {
      pendingContainer.innerHTML = '<p class="text-muted">No pending hospital verifications.</p>';
    } else {
      hospitals.forEach(user => {
        const card = document.createElement('div');
        card.className = 'glass-panel';
        card.style.margin = '12px 0';
        card.innerHTML = `
          <div style="padding:15px;">
            <b>${user.fullname}</b> (${user.email})<br>
            Phone: ${user.phone || 'N/A'}<br>
            License: ${user.license_number || 'N/A'}<br>
            Address: ${user.address || 'N/A'}<br>
            City: ${user.city || 'N/A'}<br>
            <div style="margin-top:12px; display:flex; gap:8px;">
              <button class="btn btn-success btn-sm" onclick="verifyUser('hospital', '${user._id}', 'approve')">Approve</button>
              <button class="btn btn-danger btn-sm" onclick="rejectPrompt('hospital', '${user._id}')">Reject</button>
            </div>
          </div>
        `;
        pendingContainer.appendChild(card);
      });
    }

    // Display all users
    if (allUsersContainer) {
      allUsersContainer.innerHTML = `
        <h3>Donors (${(allUsersData.donors || []).length})</h3>
        ${(allUsersData.donors || []).map(u => `
          <div class="glass-panel" style="padding:12px; margin:8px 0;">
            <b>${u.fullname}</b> - ${u.email}<br>
            Phone: ${u.phone || 'N/A'} | Blood Group: ${u.blood_group || 'N/A'}<br>
            Status: <span class="badge ${u.is_verified ? 'badge-success' : 'badge-warning'}">${u.is_verified ? 'Verified' : 'Pending'}</span>
            ${u.login_id ? `<br>Login ID: ${u.login_id}` : ''}
          </div>
        `).join('') || '<p class="text-muted">No donor records.</p>'}
        
        <h3 style="margin-top:20px;">Hospitals (${(allUsersData.hospitals || []).length})</h3>
        ${(allUsersData.hospitals || []).map(u => `
          <div class="glass-panel" style="padding:12px; margin:8px 0;">
            <b>${u.fullname}</b> - ${u.email}<br>
            Phone: ${u.phone || 'N/A'} | City: ${u.city || 'N/A'}<br>
            Status: <span class="badge ${u.is_verified ? 'badge-success' : 'badge-warning'}">${u.is_verified ? 'Verified' : 'Pending'}</span>
            ${u.login_id ? `<br>Login ID: ${u.login_id}` : ''}
          </div>
        `).join('') || '<p class="text-muted">No hospital records.</p>'}
      `;
    }

    // Display notifications
    if (notificationsContainer) {
      const notifications = notesData.notifications || [];
      notificationsContainer.innerHTML = notifications.length === 0 
        ? '<p class="text-muted">No notifications yet.</p>'
        : notifications.map(n => `
          <div class="glass-panel" style="padding:12px; margin:8px 0;">
            <b>${n.type || 'Notification'}</b><br>
            ${n.message || ''}<br>
            <small>${n.created_at ? new Date(n.created_at).toLocaleString() : ''}</small>
          </div>
        `).join('');
    }

  } catch (error) {
    console.error('Error loading admin dashboard:', error);
    pendingContainer.innerHTML = '<p class="alert alert-danger">Error loading dashboard.</p>';
  }
}

window.rejectPrompt = function (type, userId) {
  const reason = prompt('Enter rejection reason');
  if (!reason) return;
  verifyUser(type, userId, 'reject', reason);
};

window.verifyUser = async function (user_type, user_id, action, rejection_reason = '') {
  try {
    const res = await fetch(`${API_BASE}/admin/verify-user`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ user_type, user_id, action, rejection_reason }),
    });
    const data = await res.json();
    alert(data.message || data.error);
    if (res.ok) window.location.reload();
  } catch (error) {
    console.error('Error:', error);
    alert('Error processing request');
  }
};

async function initHospitalDashboard() {
  const details = document.getElementById('hospital-details');
  if (!details) return;

  try {
    const res = await fetch(`${API_BASE}/hospital/dashboard`, { headers: authHeaders() });
    const data = await res.json();
    
    if (!res.ok) {
      details.innerHTML = `<p class="alert alert-danger">${data.error || 'Unauthorized'}</p>`;
      return;
    }

    const hospital = data.hospital;
    details.innerHTML = `
      <div style="display: grid; gap: 10px;">
        <p><strong>Hospital Name:</strong> ${hospital.hospital_name || hospital.fullname}</p>
        <p><strong>Email:</strong> ${hospital.email}</p>
        <p><strong>Phone:</strong> ${hospital.phone}</p>
        <p><strong>Address:</strong> ${hospital.address || 'Not provided'}</p>
        <p><strong>City:</strong> ${hospital.city || 'Not provided'}</p>
        <p><strong>Login ID:</strong> ${hospital.login_id}</p>
        <p><strong>Status:</strong> <span class="badge ${hospital.is_verified ? 'badge-success' : 'badge-warning'}">${hospital.is_verified ? 'Verified' : 'Pending Verification'}</span></p>
      </div>
    `;

    // Pre-fill edit form
    document.getElementById('edit-hospital-name').value = hospital.hospital_name || hospital.fullname || '';
    document.getElementById('edit-hospital-phone').value = hospital.phone || '';
    document.getElementById('edit-hospital-address').value = hospital.address || '';
    document.getElementById('edit-hospital-city').value = hospital.city || '';
    document.getElementById('edit-hospital-license').value = hospital.license_number || '';

    // Show notifications
    const notificationsEl = document.getElementById('hospital-notifications');
    if (notificationsEl) {
      notificationsEl.innerHTML = (data.notifications || []).length === 0
        ? '<p class="text-muted">No notifications yet.</p>'
        : (data.notifications || []).map(n => `
          <div class="glass-panel" style="padding:12px; margin:8px 0;">
            ${n.message}
            <br><small>${n.created_at ? new Date(n.created_at).toLocaleString() : ''}</small>
          </div>
        `).join('');
    }

    // Event listeners for buttons
    document.getElementById('organ-request-btn')?.addEventListener('click', () => sendHospitalEvent('request', 'organ'));
    document.getElementById('blood-request-btn')?.addEventListener('click', () => sendHospitalEvent('request', 'blood'));
    document.getElementById('send-received-btn')?.addEventListener('click', () => sendHospitalEvent('received'));

    // Handle form submission
    const hospitalForm = document.getElementById('hospital-edit-form');
    if (hospitalForm) {
      hospitalForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          hospital_name: document.getElementById('edit-hospital-name')?.value,
          phone: document.getElementById('edit-hospital-phone')?.value,
          address: document.getElementById('edit-hospital-address')?.value,
          city: document.getElementById('edit-hospital-city')?.value,
          license_number: document.getElementById('edit-hospital-license')?.value,
        };

        const updateRes = await fetch(`${API_BASE}/hospital/profile`, {
          method: 'PATCH',
          headers: authHeaders(),
          body: JSON.stringify(payload),
        });
        const updateData = await updateRes.json();
        alert(updateData.message || updateData.error);
        if (updateRes.ok) {
          if (updateData.hospital) {
            localStorage.setItem('user', JSON.stringify(updateData.hospital));
          }
          window.location.reload();
        }
      });
    }

  } catch (error) {
    console.error('Error loading hospital dashboard:', error);
    details.innerHTML = '<p class="alert alert-danger">Error loading dashboard.</p>';
  }
}

async function sendHospitalEvent(kind, fixedType = '') {
  const request_type = fixedType || document.getElementById('request-type').value;
  const details = document.getElementById('request-details').value;
  const endpoint = kind === 'request' ? '/hospital/request' : '/hospital/received';
  const payload = kind === 'request' ? { request_type, details } : { request_type };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    alert(data.message || data.error);
    if (res.ok) {
      document.getElementById('request-details').value = '';
    }
  } catch (error) {
    console.error('Error:', error);
    alert('Error sending request');
  }
}

async function initDonorDashboard() {
  const donation = document.getElementById('last-donation');
  if (!donation) return;

  try {
    const res = await fetch(`${API_BASE}/donor/dashboard`, { headers: authHeaders() });
    const data = await res.json();
    
    if (!res.ok) {
      donation.innerHTML = `<p class="alert alert-danger">${data.error || 'Unauthorized'}</p>`;
      return;
    }

    donation.innerHTML = `
      <div style="text-align: center;">
        <p style="font-size: 1.2rem; margin-bottom: 0.5rem;">Last Donation Date</p>
        <p style="font-size: 1.5rem; color: var(--primary-color);">${data.last_donation_date || 'No record available'}</p>
      </div>
    `;

    const ageCard = document.getElementById('donor-age');
    if (ageCard) {
      ageCard.innerHTML = `
        <div style="text-align: center;">
          <p style="font-size: 1.2rem; margin-bottom: 0.5rem;">Age</p>
          <p style="font-size: 1.5rem; color: var(--primary-color);">${data.age ?? 'Not available'}</p>
        </div>
      `;
    }

    // Update stats
    document.getElementById('donation-count').textContent = data.total_donations || 0;
    document.getElementById('donor-age-value').textContent = data.age || '-';

    const donor = data.donor || {};
    document.getElementById('edit-fullname').value = donor.fullname || '';
    document.getElementById('edit-phone').value = donor.phone || '';
    document.getElementById('edit-blood-group').value = donor.blood_group || '';
    document.getElementById('edit-weight').value = donor.weight || '';
    document.getElementById('edit-dob').value = donor.dob || '';
    document.getElementById('edit-last-donation').value = donor.last_donation_date || '';

    // Hospital contacts
    const contactsEl = document.getElementById('hospital-contacts');
    if (contactsEl) {
      contactsEl.innerHTML = (data.hospital_contacts || []).length === 0
        ? '<p class="text-muted">No hospitals available.</p>'
        : (data.hospital_contacts || []).map(h => `
          <div class="glass-panel" style="padding:12px; margin:8px 0;">
            <b>${h.hospital_name}</b><br>
            ${h.phone ? `📞 ${h.phone}<br>` : ''}
            ${h.email ? `📧 ${h.email}` : ''}
          </div>
        `).join('');
    }

    // Notifications
    const notificationsEl = document.getElementById('hospital-notifications');
    if (notificationsEl) {
      notificationsEl.innerHTML = (data.hospital_notifications || []).length === 0
        ? '<p class="text-muted">No hospital notifications yet.</p>'
        : (data.hospital_notifications || []).map(n => `
          <div class="glass-panel" style="padding:12px; margin:8px 0;">
            <b>${(n.type || 'Notification').toUpperCase()}</b><br>
            ${n.message || ''}<br>
            <small>${n.created_at ? new Date(n.created_at).toLocaleString() : ''}</small>
          </div>
        `).join('');
    }

    // Handle form submission
    const form = document.getElementById('donor-edit-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          fullname: document.getElementById('edit-fullname')?.value,
          phone: document.getElementById('edit-phone')?.value,
          blood_group: document.getElementById('edit-blood-group')?.value,
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
        if (updateRes.ok) {
          if (updateData.donor) {
            localStorage.setItem('user', JSON.stringify(updateData.donor));
          }
          window.location.reload();
        }
      });
    }

  } catch (error) {
    console.error('Error loading donor dashboard:', error);
    donation.innerHTML = '<p class="alert alert-danger">Error loading dashboard.</p>';
  }
}

async function initPublicDonorList() {
  const bloodDonorsList = document.getElementById('blood-donors-list');
  if (!bloodDonorsList) return;

  try {
    const res = await fetch(`${API_BASE}/api/donors`);
    const data = await res.json();
    
    if (!res.ok) {
      bloodDonorsList.innerHTML = '<p class="alert alert-danger">Unable to load donors.</p>';
      return;
    }

    bloodDonorsList.innerHTML = data.length === 0
      ? '<p class="text-muted" style="grid-column: 1/-1; text-align: center;">No approved blood donors found.</p>'
      : data.map(d => `
        <div class="donor-card">
          <div class="donor-header">
            <div class="donor-name">${d.fullname}</div>
            <div class="blood-group">${d.blood_group || 'N/A'}</div>
          </div>
          <div class="donor-details">
            <div class="donor-detail-item"><span>📍</span> ${d.city || 'Location not specified'}</div>
            <div class="donor-detail-item"><span>📞</span> ${d.phone || 'N/A'}</div>
            <div class="donor-detail-item"><span>🩸</span> Last Donation: ${d.last_donation_date || 'Never'}</div>
          </div>
          <a href="tel:${d.phone}" class="btn contact-btn">Contact Donor</a>
        </div>
      `).join('');

    const organ = document.getElementById('organ-donors-list');
    if (organ) {
      organ.innerHTML = '<p class="text-muted" style="grid-column: 1/-1; text-align: center;">Only blood donor registration is enabled.</p>';
    }

  } catch (error) {
    console.error('Error fetching donors:', error);
    bloodDonorsList.innerHTML = '<p class="alert alert-danger">Failed to load donors. Make sure the backend is running.</p>';
  }
}