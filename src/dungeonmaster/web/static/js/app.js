/**
 * Main application — glues all modules together and manages screen routing.
 */

import { GameSocket } from './websocket.js';
import {
    appendNarrative, startStream, appendStreamToken, endStream,
    appendDiceRoll, showThinking, setInputEnabled
} from './game.js';
import { renderCharacterSheet, renderParty, loadCreationOptions } from './character.js';
import { showCombat, hideCombat } from './combat.js';

let socket = null;
let currentSessionId = null;

// Selected adventure/rulebook IDs (set during adventure selection screen)
let selectedAdventureId = null;
let selectedRulebookId = null;

// ---------------------------------------------------------------------------
// Screen Management
// ---------------------------------------------------------------------------

function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const screen = document.getElementById(`screen-${name}`);
    if (screen) screen.classList.add('active');

    // Show/hide mobile tabs
    const mobileTabs = document.getElementById('mobile-tabs');
    mobileTabs.classList.toggle('hidden', name !== 'game');
}

// ---------------------------------------------------------------------------
// Start Screen
// ---------------------------------------------------------------------------

async function initStartScreen() {
    // Load saved games
    try {
        const res = await fetch('/api/saves');
        const saves = await res.json();
        const container = document.getElementById('saved-games');

        if (saves.length > 0) {
            container.innerHTML = '<h3 style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 8px;">Continue Adventure</h3>';
            saves.forEach(save => {
                const item = document.createElement('div');
                item.className = 'saved-game-item';
                item.innerHTML = `
                    <div>
                        <div class="saved-game-name">${save.character_name || save.name}</div>
                        <div class="saved-game-info">
                            ${save.character_class || ''} | Turn ${save.turn_count}
                        </div>
                    </div>
                `;
                item.addEventListener('click', () => loadAndPlay(save.id));
                container.appendChild(item);
            });
        }
    } catch (e) {
        console.log('No saves available or server not running');
    }
}

// ---------------------------------------------------------------------------
// Adventure Selection
// ---------------------------------------------------------------------------

async function showAdventureSelection() {
    showScreen('adventure');
    await loadContentList();
}

async function loadContentList() {
    const adventureSelect = document.getElementById('adventure-select');
    const rulebookSelect = document.getElementById('rulebook-select');

    try {
        const res = await fetch('/api/content');
        const content = await res.json();

        // Reset selects (keep the default "none" option)
        adventureSelect.innerHTML = '<option value="">Freeplay (no adventure)</option>';
        rulebookSelect.innerHTML = '<option value="">Default rules (LLM knowledge)</option>';

        content.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;

            const chunkInfo = Object.entries(item.content_types || {})
                .map(([type, count]) => `${count} ${type}`)
                .join(', ');
            option.textContent = `${item.title} (${item.total_chunks} chunks: ${chunkInfo})`;

            if (item.category === 'adventure') {
                adventureSelect.appendChild(option);
            } else if (item.category === 'rulebook') {
                rulebookSelect.appendChild(option);
            } else {
                // General books — add to both
                adventureSelect.appendChild(option.cloneNode(true));
                rulebookSelect.appendChild(option);
            }
        });

        // Show info on selection change
        adventureSelect.addEventListener('change', () => {
            const infoEl = document.getElementById('adventure-info');
            if (adventureSelect.value) {
                const item = content.find(c => c.id === adventureSelect.value);
                if (item) {
                    infoEl.textContent = `${item.title} — ${item.total_chunks} chunks ingested. The DM will use this for encounters, NPCs, and lore.`;
                }
            } else {
                infoEl.textContent = 'Select an adventure or play freeplay — the DM will improvise!';
            }
        });
    } catch (e) {
        console.log('Failed to load content list:', e);
    }
}

/**
 * Read a Server-Sent Events stream from a fetch response.
 * Calls onEvent for each parsed SSE data payload.
 */
async function readSSEStream(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    onEvent(data);
                } catch (e) {
                    // skip malformed SSE lines
                }
            }
        }
    }
}

async function uploadContent() {
    const title = document.getElementById('upload-title').value.trim();
    const contentType = document.getElementById('upload-type').value;
    const fileInput = document.getElementById('upload-file');
    const statusEl = document.getElementById('upload-status');

    if (!title || !fileInput.files.length) {
        statusEl.textContent = 'Please provide a title and select a file.';
        statusEl.className = 'info-box error';
        statusEl.classList.remove('hidden');
        return;
    }

    statusEl.textContent = 'Starting ingestion...';
    statusEl.className = 'info-box';
    statusEl.classList.remove('hidden');
    document.getElementById('btn-upload').disabled = true;
    document.getElementById('btn-convert').disabled = true;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('title', title);
    formData.append('content_type', contentType);

    try {
        const res = await fetch('/api/content/ingest', { method: 'POST', body: formData });

        let lastData = null;
        await readSSEStream(res, (data) => {
            lastData = data;
            if (data.status === 'error') {
                statusEl.textContent = `Error: ${data.message}`;
                statusEl.className = 'info-box error';
            } else if (data.status === 'complete') {
                const counts = Object.entries(data.content_type_counts || {})
                    .map(([type, count]) => `${count} ${type}`).join(', ');
                statusEl.textContent = `Ingested "${data.title}": ${counts}`;
                statusEl.className = 'info-box success';
            } else {
                // Progress update
                const pct = data.progress ? `${Math.round(data.progress * 100)}%` : '';
                statusEl.textContent = `${data.message || data.status} ${pct}`;
            }
        });

        if (lastData && lastData.status === 'complete') {
            document.getElementById('upload-title').value = '';
            fileInput.value = '';
            await loadContentList();
        }
    } catch (e) {
        statusEl.textContent = `Upload failed: ${e.message}`;
        statusEl.className = 'info-box error';
    } finally {
        document.getElementById('btn-upload').disabled = false;
        document.getElementById('btn-convert').disabled = false;
    }
}

async function convertBookToAdventure() {
    const title = document.getElementById('upload-title').value.trim();
    const fileInput = document.getElementById('upload-file');
    const statusEl = document.getElementById('upload-status');

    if (!title || !fileInput.files.length) {
        statusEl.textContent = 'Please provide a title and select a .txt book file.';
        statusEl.className = 'info-box error';
        statusEl.classList.remove('hidden');
        return;
    }

    statusEl.textContent = 'Starting conversion...';
    statusEl.className = 'info-box';
    statusEl.classList.remove('hidden');
    document.getElementById('btn-convert').disabled = true;
    document.getElementById('btn-upload').disabled = true;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('title', title);

    try {
        const res = await fetch('/api/content/convert', { method: 'POST', body: formData });

        let lastData = null;
        await readSSEStream(res, (data) => {
            lastData = data;
            if (data.status === 'error') {
                statusEl.textContent = `Error: ${data.message}`;
                statusEl.className = 'info-box error';
            } else if (data.status === 'complete') {
                const stats = data.stats || {};
                const statsStr = [
                    stats.locations && `${stats.locations} locations`,
                    stats.npcs && `${stats.npcs} NPCs`,
                    stats.encounters && `${stats.encounters} encounters`,
                    stats.creatures && `${stats.creatures} creatures`,
                ].filter(Boolean).join(', ');
                statusEl.textContent = `Converted "${data.title}" (${data.chapters_processed} chapters): ${statsStr || 'done'}`;
                statusEl.className = 'info-box success';
            } else if (data.status === 'converting') {
                const pct = data.progress ? `${Math.round(data.progress * 100)}%` : '';
                statusEl.textContent = `Chapter ${data.chapter}/${data.total}: ${data.title || ''} ${pct}`;
            } else {
                statusEl.textContent = data.message || data.status;
            }
        });

        if (lastData && lastData.status === 'complete') {
            document.getElementById('upload-title').value = '';
            fileInput.value = '';
            await loadContentList();
        }
    } catch (e) {
        statusEl.textContent = `Conversion failed: ${e.message}`;
        statusEl.className = 'info-box error';
    } finally {
        document.getElementById('btn-convert').disabled = false;
        document.getElementById('btn-upload').disabled = false;
    }
}

function continueToCharCreation() {
    // Save selected adventure/rulebook
    selectedAdventureId = document.getElementById('adventure-select').value || null;
    selectedRulebookId = document.getElementById('rulebook-select').value || null;

    showScreen('creation');
    loadCreationOptions();
}

// ---------------------------------------------------------------------------
// Character Creation
// ---------------------------------------------------------------------------

async function createCharacter() {
    const name = document.getElementById('char-name').value.trim();
    const race = document.getElementById('char-race').value;
    const charClass = document.getElementById('char-class').value;

    if (!name) {
        document.getElementById('char-name').focus();
        return;
    }

    try {
        const body = {
            name: `${name}'s Adventure`,
            rules_system: 'dnd5e',
            character: {
                name,
                race,
                character_class: charClass,
                is_player: true,
            },
            companions: [
                {
                    name: 'Thorin',
                    race: 'dwarf',
                    character_class: 'fighter',
                    is_player: false,
                    personality: 'Gruff but loyal dwarven warrior. Speaks bluntly and loves a good ale.',
                },
                {
                    name: 'Lyra',
                    race: 'half_elf',
                    character_class: 'cleric',
                    is_player: false,
                    personality: 'Gentle healer with a sharp wit. Devoted to her faith but not above sarcasm.',
                },
            ],
        };

        // Include adventure/rulebook IDs if selected
        if (selectedAdventureId) body.adventure_book_id = selectedAdventureId;
        if (selectedRulebookId) body.rulebook_book_id = selectedRulebookId;

        const res = await fetch('/api/game/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await res.json();
        if (data.session_id) {
            await loadAndPlay(data.session_id);
        }
    } catch (e) {
        console.error('Failed to create game:', e);
        appendNarrative('system', 'Failed to create game. Is the server running?');
    }
}

// ---------------------------------------------------------------------------
// Game Play
// ---------------------------------------------------------------------------

async function loadAndPlay(sessionId) {
    currentSessionId = sessionId;
    showScreen('game');

    // Connect WebSocket
    socket = new GameSocket(sessionId);

    socket.on('connected', () => {
        setInputEnabled(true);
        appendNarrative('system', 'Connected to the Dungeon Master.');
    });

    socket.on('disconnected', () => {
        setInputEnabled(false);
        appendNarrative('system', 'Connection lost. Attempting to reconnect...');
    });

    socket.on('narrative_chunk', (msg) => {
        if (msg.is_final) {
            endStream();
        } else {
            appendStreamToken(msg.text);
        }
    });

    socket.on('history_entry', (msg) => {
        // Replayed history entry — render with correct actor styling
        appendNarrative(msg.actor === 'player' ? 'player' : 'dm', msg.content);
    });

    socket.on('dice_roll', (msg) => {
        endStream(); // end any active stream before showing dice
        appendDiceRoll(msg);
    });

    socket.on('game_state_update', (msg) => {
        if (msg.character) renderCharacterSheet(msg.character);
        if (msg.companions) renderParty(msg.companions);
    });

    socket.on('combat_update', (msg) => {
        if (msg.active) {
            showCombat(msg);
        } else {
            hideCombat();
        }
    });

    socket.on('thinking', (msg) => {
        showThinking(msg.active);
        setInputEnabled(!msg.active);
    });

    socket.on('error', (msg) => {
        appendNarrative('system', `Error: ${msg.message}`);
        showThinking(false);
        setInputEnabled(true);
    });

    socket.connect();
}

function sendPlayerAction() {
    const input = document.getElementById('player-input');
    const text = input.value.trim();
    if (!text || !socket) return;

    appendNarrative('player', text);
    socket.sendAction(text);
    input.value = '';
    startStream(); // prepare for streamed response
}

// ---------------------------------------------------------------------------
// Event Listeners
// ---------------------------------------------------------------------------

// Start → Adventure Selection (instead of straight to character creation)
document.getElementById('btn-new-game').addEventListener('click', showAdventureSelection);

// Adventure screen
document.getElementById('btn-upload').addEventListener('click', uploadContent);
document.getElementById('btn-convert').addEventListener('click', convertBookToAdventure);
document.getElementById('btn-continue-to-char').addEventListener('click', continueToCharCreation);

// Character creation
document.getElementById('btn-create').addEventListener('click', createCharacter);

// Game input
document.getElementById('btn-send').addEventListener('click', sendPlayerAction);
document.getElementById('player-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendPlayerAction();
    }
});

document.getElementById('btn-save').addEventListener('click', () => {
    if (socket) socket.sendCommand('save');
});

// Mobile tab navigation
document.querySelectorAll('.mobile-tabs .tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.mobile-tabs .tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const panel = tab.dataset.panel;
        document.querySelectorAll('.sidebar').forEach(s => s.classList.remove('mobile-visible'));

        if (panel === 'character') {
            document.getElementById('panel-character').classList.add('mobile-visible');
        } else if (panel === 'party') {
            document.getElementById('panel-party').classList.add('mobile-visible');
        }
        // 'narrative' just hides sidebars (default)
    });
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

initStartScreen();
