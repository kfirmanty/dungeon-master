/**
 * Narrative rendering with streaming typewriter effect.
 */

const log = document.getElementById('narrative-log');
let currentStreamEl = null;

export function appendNarrative(actor, content) {
    const entry = document.createElement('div');
    entry.className = `narrative-entry ${actor}`;
    entry.textContent = content;
    log.appendChild(entry);
    scrollToBottom();
    return entry;
}

export function startStream() {
    currentStreamEl = document.createElement('div');
    currentStreamEl.className = 'narrative-entry dm';
    log.appendChild(currentStreamEl);
    return currentStreamEl;
}

export function appendStreamToken(token) {
    if (!currentStreamEl) currentStreamEl = startStream();
    currentStreamEl.textContent += token;
    scrollToBottom();
}

export function endStream() {
    currentStreamEl = null;
}

export function appendDiceRoll(data) {
    const el = document.createElement('div');
    el.className = 'narrative-entry system';

    const dice = document.createElement('div');
    const successClass = data.success === true ? 'success' :
                         data.success === false ? 'failure' : '';
    const isCrit = data.rolls && data.rolls.length === 1 && data.rolls[0] === 20;

    dice.className = `dice-result ${successClass} ${isCrit ? 'critical' : ''}`;
    dice.innerHTML = `
        <span class="dice-icon">\u{1F3B2}</span>
        <span>${data.description || data.dice}</span>
        <span class="roll-total">${data.total}</span>
    `;

    el.appendChild(dice);
    log.appendChild(el);
    scrollToBottom();
}

export function showThinking(active) {
    const el = document.getElementById('thinking-indicator');
    el.classList.toggle('hidden', !active);
    if (active) scrollToBottom();
}

export function setInputEnabled(enabled) {
    const input = document.getElementById('player-input');
    const btn = document.getElementById('btn-send');
    input.disabled = !enabled;
    btn.disabled = !enabled;
    if (enabled) input.focus();
}

function scrollToBottom() {
    log.scrollTop = log.scrollHeight;
}
