/**
 * WebSocket connection manager with automatic reconnection.
 */

export class GameSocket {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.ws = null;
        this.handlers = {};
        this.reconnectAttempts = 0;
        this.maxReconnects = 5;
    }

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/api/game/${this.sessionId}/play`;

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this._emit('connected');
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._emit(msg.type, msg);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this._emit('disconnected');
            this._tryReconnect();
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    sendAction(text) {
        this.send({ type: 'player_action', text });
    }

    sendCommand(command) {
        this.send({ type: 'system_command', command });
    }

    on(type, handler) {
        if (!this.handlers[type]) this.handlers[type] = [];
        this.handlers[type].push(handler);
    }

    _emit(type, data) {
        const handlers = this.handlers[type] || [];
        handlers.forEach(h => h(data));
    }

    _tryReconnect() {
        if (this.reconnectAttempts >= this.maxReconnects) return;
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }

    close() {
        if (this.ws) {
            this.maxReconnects = 0; // prevent reconnection
            this.ws.close();
        }
    }
}
