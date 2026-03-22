/**
 * Combat mode UI — initiative tracker and action buttons.
 */

export function showCombat(data) {
    const panel = document.getElementById('combat-panel');
    panel.classList.remove('hidden');

    renderInitiative(data.initiative_order, data.current_turn);

    if (data.available_actions) {
        renderActions(data.available_actions);
    }
}

export function hideCombat() {
    document.getElementById('combat-panel').classList.add('hidden');
}

function renderInitiative(order, currentTurn) {
    const el = document.getElementById('initiative-order');
    if (!order || !order.length) {
        el.innerHTML = '';
        return;
    }

    el.innerHTML = order.map(c => {
        const isCurrent = c.name === currentTurn;
        const hpPct = c.hp_max ? Math.round((c.hp_current / c.hp_max) * 100) : 100;

        return `
            <div class="party-member ${isCurrent ? 'current-turn' : ''}"
                 style="${isCurrent ? 'border-color: var(--accent-gold);' : ''}">
                <div class="party-member-name">
                    ${isCurrent ? '\u25B6 ' : ''}${c.name}
                </div>
                <div class="hp-bar">
                    <div class="hp-bar-fill ${hpPct <= 25 ? 'low' : ''}"
                         style="width: ${hpPct}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

function renderActions(actions) {
    const el = document.getElementById('combat-actions');
    el.innerHTML = actions.map(a =>
        `<button class="btn btn-secondary combat-action-btn" data-action="${a}">
            ${a.replace('_', ' ')}
        </button>`
    ).join('');

    // Attach click handlers
    el.querySelectorAll('.combat-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = document.getElementById('player-input');
            input.value = `I ${btn.dataset.action}`;
            input.focus();
        });
    });
}
