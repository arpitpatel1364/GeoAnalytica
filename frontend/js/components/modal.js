/* ============================================================
   GeoAnalytica — Modal Component
   ============================================================ */

const Modal = {
  stack: [],

  open(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    Modal.stack.push(id);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) Modal.close(id);
    });

    // Close on Escape
    const escHandler = (e) => {
      if (e.key === 'Escape') {
        Modal.close(id);
        document.removeEventListener('keydown', escHandler);
      }
    };
    document.addEventListener('keydown', escHandler);
  },

  close(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.remove('open');
    Modal.stack = Modal.stack.filter(s => s !== id);
    if (Modal.stack.length === 0) document.body.style.overflow = '';
  },

  closeAll() {
    Modal.stack.forEach(id => Modal.close(id));
    Modal.stack = [];
    document.body.style.overflow = '';
  },

  // Bind close buttons
  bindCloseButtons() {
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => {
        const modalId = btn.closest('.modal-overlay')?.id;
        if (modalId) Modal.close(modalId);
      });
    });
    document.querySelectorAll('[data-modal-open]').forEach(btn => {
      btn.addEventListener('click', () => Modal.open(btn.dataset.modalOpen));
    });
  },
};

window.Modal = Modal;
document.addEventListener('DOMContentLoaded', () => Modal.bindCloseButtons());


/* ============================================================
   GeoAnalytica — Toast Notifications (Notyf wrapper)
   ============================================================ */

const Toast = {
  _notyf: null,

  _get() {
    if (!Toast._notyf && window.Notyf) {
      Toast._notyf = new Notyf({
        duration: 4000,
        position: { x: 'right', y: 'bottom' },
        ripple: false,
        dismissible: true,
        types: [
          {
            type: 'success',
            background: 'var(--accent-green)',
            icon: { className: 'notyf-icon', tagName: 'span', text: '✓' },
          },
          {
            type: 'error',
            background: 'var(--accent-red)',
            icon: { className: 'notyf-icon', tagName: 'span', text: '✕' },
          },
          {
            type: 'warning',
            background: 'var(--accent-orange)',
            icon: { className: 'notyf-icon', tagName: 'span', text: '!' },
          },
          {
            type: 'info',
            background: 'var(--accent-blue)',
            icon: { className: 'notyf-icon', tagName: 'span', text: 'i' },
          },
        ],
      });
    }
    return Toast._notyf;
  },

  success(msg) {
    const n = Toast._get();
    if (n) n.success(msg);
    else console.log('[Toast] SUCCESS:', msg);
  },

  error(msg) {
    const n = Toast._get();
    if (n) n.error(msg);
    else console.error('[Toast] ERROR:', msg);
  },

  warning(msg) {
    const n = Toast._get();
    if (n) n.open({ type: 'warning', message: msg });
    else console.warn('[Toast] WARNING:', msg);
  },

  info(msg) {
    const n = Toast._get();
    if (n) n.open({ type: 'info', message: msg });
    else console.info('[Toast] INFO:', msg);
  },
};

window.Toast = Toast;


/* ============================================================
   GeoAnalytica — Confirm Dialog
   ============================================================ */

const Confirm = {
  show({ title = 'Are you sure?', message = '', confirmText = 'Confirm', cancelText = 'Cancel', danger = false } = {}) {
    return new Promise((resolve) => {
      // Remove any existing confirm dialog
      const existing = document.getElementById('ga-confirm-dialog');
      if (existing) existing.remove();

      const overlay = document.createElement('div');
      overlay.id = 'ga-confirm-dialog';
      overlay.className = 'modal-overlay open';
      overlay.innerHTML = `
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3 class="modal-title">${title}</h3>
            <button class="modal-close" id="confirm-x">×</button>
          </div>
          <div class="modal-body">
            <p style="color:var(--text-secondary);font-size:var(--text-sm);line-height:1.6;">${message}</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary btn-sm" id="confirm-cancel">${cancelText}</button>
            <button class="btn ${danger ? 'btn-danger' : 'btn-primary'} btn-sm" id="confirm-ok">${confirmText}</button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
      document.body.style.overflow = 'hidden';

      const cleanup = (result) => {
        overlay.classList.remove('open');
        setTimeout(() => {
          overlay.remove();
          document.body.style.overflow = '';
        }, 200);
        resolve(result);
      };

      document.getElementById('confirm-ok').addEventListener('click', () => cleanup(true));
      document.getElementById('confirm-cancel').addEventListener('click', () => cleanup(false));
      document.getElementById('confirm-x').addEventListener('click', () => cleanup(false));

      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) cleanup(false);
      });
    });
  },
};

window.Confirm = Confirm;
