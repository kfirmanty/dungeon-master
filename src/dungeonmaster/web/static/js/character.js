/**
 * Character sheet rendering and creation flow.
 */

export function renderCharacterSheet(character) {
    const el = document.getElementById('character-sheet');
    if (!character || !character.name) {
        el.innerHTML = '<p class="text-dim">No character loaded</p>';
        return;
    }

    const hp = character.hp || {};
    const hpPct = hp.max ? Math.round((hp.current / hp.max) * 100) : 100;
    const hpClass = hpPct <= 25 ? 'low' : hpPct <= 50 ? 'medium' : '';

    const abilities = character.abilities || {};
    const abilityMod = (score) => {
        const mod = Math.floor((score - 10) / 2);
        return mod >= 0 ? `+${mod}` : `${mod}`;
    };

    el.innerHTML = `
        <div class="stat-block">
            <div class="char-name">${character.name}</div>
            <div class="char-subtitle">
                Level ${character.level || 1}
                ${(character.race || '').replace('_', ' ')}
                ${(character.character_class || '').replace('_', ' ')}
            </div>

            <div class="stat-row">
                <span class="stat-label">HP</span>
                <span class="stat-value">${hp.current || 0}/${hp.max || 0}</span>
            </div>
            <div class="hp-bar">
                <div class="hp-bar-fill ${hpClass}" style="width: ${hpPct}%"></div>
            </div>

            <div class="stat-row">
                <span class="stat-label">AC</span>
                <span class="stat-value">${character.ac || 10}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Speed</span>
                <span class="stat-value">${character.speed || 30} ft</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Prof. Bonus</span>
                <span class="stat-value">+${character.proficiency_bonus || 2}</span>
            </div>
        </div>

        <div class="abilities-grid">
            ${['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].map(a => `
                <div class="ability-box">
                    <div class="ability-label">${a.slice(0, 3).toUpperCase()}</div>
                    <div class="ability-score">${abilities[a] || 10}</div>
                    <div class="ability-mod">${abilityMod(abilities[a] || 10)}</div>
                </div>
            `).join('')}
        </div>

        ${character.proficiencies && character.proficiencies.length ? `
        <div class="stat-block">
            <div class="stat-label" style="margin-bottom: 4px">Skills</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary)">
                ${character.proficiencies.join(', ')}
            </div>
        </div>
        ` : ''}

        ${character.inventory && character.inventory.length ? `
        <div class="stat-block">
            <div class="stat-label" style="margin-bottom: 4px">Inventory</div>
            ${character.inventory.map(item => `
                <div style="font-size: 0.8rem; color: var(--text-secondary)">
                    ${item.equipped ? '\u2694\uFE0F' : '\u{1F4E6}'} ${item.name}${item.quantity > 1 ? ` (x${item.quantity})` : ''}
                </div>
            `).join('')}
        </div>
        ` : ''}

        ${character.gold ? `
        <div class="stat-row">
            <span class="stat-label">Gold</span>
            <span class="stat-value">${character.gold} gp</span>
        </div>
        ` : ''}
    `;
}

export function renderParty(companions) {
    const el = document.getElementById('party-list');
    if (!companions || !companions.length) {
        el.innerHTML = '<p style="font-size: 0.85rem; color: var(--text-dim)">No companions</p>';
        return;
    }

    el.innerHTML = companions.map(c => {
        const hp = c.hp || {};
        const hpPct = hp.max ? Math.round((hp.current / hp.max) * 100) : 100;
        const hpClass = hpPct <= 25 ? 'low' : hpPct <= 50 ? 'medium' : '';

        return `
            <div class="party-member">
                <div class="party-member-name">${c.name}</div>
                <div class="party-member-info">
                    Lvl ${c.level || 1} ${(c.character_class || '').replace('_', ' ')}
                </div>
                <div class="stat-row">
                    <span class="stat-label">HP</span>
                    <span class="stat-value">${hp.current || 0}/${hp.max || 0}</span>
                </div>
                <div class="hp-bar">
                    <div class="hp-bar-fill ${hpClass}" style="width: ${hpPct}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

export async function loadCreationOptions() {
    try {
        const res = await fetch('/api/rules/dnd5e/creation-options');
        const data = await res.json();

        const raceSelect = document.getElementById('char-race');
        const classSelect = document.getElementById('char-class');

        if (data.races) {
            raceSelect.innerHTML = data.races.map(r =>
                `<option value="${r}">${r.replace('_', ' ')}</option>`
            ).join('');
        }

        if (data.classes) {
            classSelect.innerHTML = data.classes.map(c =>
                `<option value="${c}">${c.replace('_', ' ')}</option>`
            ).join('');
        }

        // Show race info on change
        if (data.race_details) {
            raceSelect.addEventListener('change', () => {
                const info = data.race_details[raceSelect.value];
                if (info) {
                    const bonuses = Object.entries(info.bonuses || {})
                        .map(([k, v]) => `${k.slice(0, 3).toUpperCase()} +${v}`)
                        .join(', ');
                    document.getElementById('race-info').textContent =
                        `Speed: ${info.speed} ft | Bonuses: ${bonuses || 'none'}`;
                }
            });
            raceSelect.dispatchEvent(new Event('change'));
        }

        return data;
    } catch (e) {
        console.error('Failed to load creation options:', e);
        return null;
    }
}
