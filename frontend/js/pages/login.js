/* ============================================================
   GeoAnalytica — Login Page
   ============================================================ */

const LoginPage = {
  init() {
    Auth.requireGuest && Auth.requireGuest();

    const form    = document.getElementById('login-form');
    const loginBtn= document.getElementById('login-btn');
    const errEl   = document.getElementById('login-error');

    if (!form) return;

    // Pre-fill redirect check
    const redirect = new URLSearchParams(window.location.search).get('redirect');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      LoginPage._submit(loginBtn, errEl, redirect);
    });

    loginBtn?.addEventListener('click', async (e) => {
      e.preventDefault();
      LoginPage._submit(loginBtn, errEl, redirect);
    });

    // Demo login button
    document.getElementById('demo-login-btn')?.addEventListener('click', () => {
      document.getElementById('email').value    = 'demo@geoanalytica.io';
      document.getElementById('password').value = 'Demo1234!';
    });
  },

  async _submit(btn, errEl, redirect) {
    const email    = document.getElementById('email')?.value?.trim();
    const password = document.getElementById('password')?.value;

    if (!email || !password) {
      if (errEl) { errEl.textContent = 'Please enter email and password.'; errEl.hidden = false; }
      return;
    }

    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner spinner-sm"></span> Signing in…'; }
    if (errEl) errEl.hidden = true;

    try {
      await Auth.login(email, password);
      // Auth.login redirects on success
    } catch (err) {
      if (errEl) { errEl.textContent = err.message || 'Login failed.'; errEl.hidden = false; }
      if (btn)   { btn.disabled = false; btn.textContent = 'Sign in'; }
    }
  },
};

window.LoginPage = LoginPage;
document.addEventListener('DOMContentLoaded', () => LoginPage.init());


/* ============================================================
   GeoAnalytica — Register Page
   ============================================================ */

const RegisterPage = {
  init() {
    const form    = document.getElementById('register-form');
    const passEl  = document.getElementById('password');
    const strengthFill  = document.getElementById('strength-fill');
    const strengthLabel = document.getElementById('strength-label');

    if (!form) return;

    // Password strength meter
    passEl?.addEventListener('input', () => {
      const s = Validate.passwordStrength(passEl.value);
      if (strengthFill)  { strengthFill.style.width = s.width; strengthFill.style.background = s.color; }
      if (strengthLabel) { strengthLabel.textContent = s.label || ''; strengthLabel.style.color = s.color; }
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await RegisterPage._submit();
    });
  },

  async _submit() {
    Validate.clearAllErrors('register-form');

    const name     = document.getElementById('name')?.value?.trim();
    const email    = document.getElementById('email')?.value?.trim();
    const password = document.getElementById('password')?.value;
    const confirm  = document.getElementById('confirm-password')?.value;
    const terms    = document.getElementById('terms')?.checked;
    const errEl    = document.getElementById('register-error');
    const btn      = document.getElementById('register-btn');

    let valid = true;

    const nameErr = Validate.required(name, 'Full name');
    if (nameErr)   { Validate.showError('name', nameErr); valid = false; }

    const emailErr = Validate.email(email);
    if (emailErr)  { Validate.showError('email', emailErr); valid = false; }

    const passErr = Validate.minLength(password, 8, 'Password');
    if (passErr)   { Validate.showError('password', passErr); valid = false; }

    const matchErr = Validate.match(password, confirm, 'Passwords');
    if (matchErr)  { Validate.showError('confirm-password', matchErr); valid = false; }

    if (!terms) {
      if (errEl) { errEl.textContent = 'Please accept the Terms of Service.'; errEl.hidden = false; }
      valid = false;
    }

    if (!valid) return;

    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner spinner-sm"></span> Creating account…'; }
    if (errEl) errEl.hidden = true;

    try {
      await API.auth.register({ full_name: name, email, password });
      await Auth.login(email, password);
    } catch (err) {
      if (errEl) { errEl.textContent = err.message || 'Registration failed.'; errEl.hidden = false; }
      if (btn)   { btn.disabled = false; btn.textContent = 'Create account'; }
    }
  },
};

window.RegisterPage = RegisterPage;
document.addEventListener('DOMContentLoaded', () => RegisterPage.init());
