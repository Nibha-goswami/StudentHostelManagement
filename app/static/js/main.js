// Auto-dismiss flash messages
document.querySelectorAll('.alert').forEach(el => {
  el.addEventListener('click', () => el.remove());
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(1rem)';
    el.style.transition = 'opacity 0.3s, transform 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 4000);
});

// Modal helpers
function openModal(id) {
  document.getElementById(id).classList.add('open');
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}
// Close modal on backdrop click
document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
  backdrop.addEventListener('click', e => {
    if (e.target === backdrop) backdrop.classList.remove('open');
  });
});

// Demo account quick-fill on login page
document.querySelectorAll('.demo-item').forEach(item => {
  item.addEventListener('click', () => {
    const email = item.dataset.email;
    const pass  = item.dataset.pass;
    const emailField = document.getElementById('email');
    const passField  = document.getElementById('password');
    if (emailField && email) emailField.value = email;
    if (passField  && pass)  passField.value  = pass;
    item.style.background = 'rgba(99,102,241,0.2)';
    setTimeout(() => item.style.background = '', 500);
  });
});

// Mobile sidebar toggle
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.querySelector('.sidebar');
if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
}

// Active nav link highlight
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-link').forEach(link => {
  if (link.getAttribute('href') === currentPath) {
    link.classList.add('active');
  }
});

// Progress bar animation
window.addEventListener('load', () => {
  document.querySelectorAll('.progress-bar').forEach(bar => {
    const val = bar.style.width;
    bar.style.width = '0';
    setTimeout(() => { bar.style.width = val; }, 100);
  });
});
