/* ============================================================
   GeoAnalytica — WebSocket Manager
   Handles live query progress updates with auto-reconnect
   ============================================================ */

const WS = {
  socket:             null,
  queryId:            null,
  handlers:           {},
  reconnectAttempts:  0,
  maxReconnect:       5,
  reconnectTimer:     null,
  pingInterval:       null,
  isConnecting:       false,

  // ── Connect ───────────────────────────────────────────────
  connect(queryId) {
    if (WS.isConnecting) return;
    WS.isConnecting = true;
    WS.queryId = queryId;

    const token = localStorage.getItem('ga_access_token');
    if (!token) {
      WS.isConnecting = false;
      return;
    }

    const url = `${GeoAnalytica.config.wsBase}/${queryId}?token=${encodeURIComponent(token)}`;

    try {
      WS.socket = new WebSocket(url);
    } catch (e) {
      console.error('WS: Failed to create WebSocket', e);
      WS.isConnecting = false;
      return;
    }

    WS.socket.onopen = () => {
      WS.isConnecting = false;
      WS.reconnectAttempts = 0;
      WS.emit('connected', { queryId });

      // Start ping/pong keepalive
      WS.pingInterval = setInterval(() => {
        if (WS.socket && WS.socket.readyState === WebSocket.OPEN) {
          WS.socket.send('ping');
        }
      }, 25000);
    };

    WS.socket.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const msg = JSON.parse(event.data);
        WS.emit(msg.type, msg);
        // Also emit a generic 'message' event
        WS.emit('message', msg);
      } catch (e) {
        console.warn('WS: Failed to parse message', event.data);
      }
    };

    WS.socket.onclose = (event) => {
      WS.isConnecting = false;
      clearInterval(WS.pingInterval);
      WS.emit('disconnected', { code: event.code, reason: event.reason });

      // Auto-reconnect unless it was a clean close or auth failure
      if (event.code !== 1000 && event.code !== 4001 && event.code !== 4002) {
        if (WS.reconnectAttempts < WS.maxReconnect) {
          const delay = Math.min(1000 * Math.pow(2, WS.reconnectAttempts), 10000);
          WS.reconnectAttempts++;
          WS.reconnectTimer = setTimeout(() => {
            WS.connect(queryId);
          }, delay);
        } else {
          WS.emit('reconnect_failed', {});
        }
      }
    };

    WS.socket.onerror = (e) => {
      WS.isConnecting = false;
      WS.emit('error', { message: 'WebSocket connection error' });
    };
  },

  // ── Disconnect ────────────────────────────────────────────
  disconnect() {
    clearTimeout(WS.reconnectTimer);
    clearInterval(WS.pingInterval);
    WS.reconnectAttempts = WS.maxReconnect; // Prevent reconnects
    if (WS.socket) {
      WS.socket.close(1000, 'Client disconnect');
      WS.socket = null;
    }
    WS.queryId = null;
    WS.isConnecting = false;
  },

  // ── Send ─────────────────────────────────────────────────
  send(data) {
    if (WS.socket && WS.socket.readyState === WebSocket.OPEN) {
      WS.socket.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  },

  // ── Event bus ─────────────────────────────────────────────
  on(event, handler) {
    if (!WS.handlers[event]) WS.handlers[event] = [];
    WS.handlers[event].push(handler);
    return () => WS.off(event, handler); // Returns unsubscribe fn
  },

  off(event, handler) {
    if (WS.handlers[event]) {
      WS.handlers[event] = WS.handlers[event].filter(h => h !== handler);
    }
  },

  emit(event, data) {
    const handlers = WS.handlers[event] || [];
    handlers.forEach(h => {
      try { h(data); }
      catch (e) { console.error(`WS handler error [${event}]`, e); }
    });
  },

  // ── Clear all handlers ────────────────────────────────────
  clearHandlers(event) {
    if (event) {
      WS.handlers[event] = [];
    } else {
      WS.handlers = {};
    }
  },

  // ── State helpers ─────────────────────────────────────────
  isOpen() {
    return WS.socket && WS.socket.readyState === WebSocket.OPEN;
  },

  getState() {
    if (!WS.socket) return 'disconnected';
    const states = ['connecting', 'open', 'closing', 'closed'];
    return states[WS.socket.readyState] || 'unknown';
  },
};

window.WS = WS;
