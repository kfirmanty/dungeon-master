/**
 * Dice roll visualization — renders dice results with animation.
 */

export function createDiceDisplay(data) {
    const el = document.createElement('div');
    const successClass = data.success === true ? 'success' :
                         data.success === false ? 'failure' : '';
    const nat20 = data.rolls && data.rolls.some(r => r === 20);
    const nat1 = data.rolls && data.rolls.some(r => r === 1) && data.rolls.length === 1;

    let extraClass = '';
    if (nat20) extraClass = 'critical';
    else if (nat1) extraClass = 'fumble';

    el.className = `dice-result ${successClass} ${extraClass}`;

    const rollsStr = data.rolls ? `[${data.rolls.join(', ')}]` : '';
    const modStr = data.modifier ? (data.modifier > 0 ? `+${data.modifier}` : data.modifier) : '';

    el.innerHTML = `
        <span class="dice-icon">${nat20 ? '\u2728' : '\u{1F3B2}'}</span>
        <span class="roll-detail">
            ${data.description || data.dice || ''}
            <span style="color: var(--text-dim); font-size: 0.8rem">
                ${rollsStr}${modStr}
            </span>
        </span>
        <span class="roll-total">${data.total}</span>
        ${data.dc ? `<span style="color: var(--text-dim); font-size: 0.8rem">vs DC ${data.dc}</span>` : ''}
    `;

    return el;
}
