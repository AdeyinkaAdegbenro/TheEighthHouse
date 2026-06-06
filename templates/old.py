from flask import Flask, render_template_string, request, jsonify, Response
import sqlite3
import io
import csv

app = Flask(__name__)

def init_db():
    with sqlite3.connect('shots.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS shots 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             scene_num TEXT, shot_label TEXT, size TEXT, 
             frame TEXT, angle TEXT, extras TEXT, 
             snippet TEXT, notes TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS script_data 
                        (id INTEGER PRIMARY KEY, content TEXT)''')
        # Ensure there is at least one row to update
        conn.execute('INSERT OR IGNORE INTO script_data (id, content) VALUES (1, "")')
    conn.commit()

@app.route('/save_script', methods=['POST'])
def save_script():
    data = request.json
    with sqlite3.connect('shots.db') as conn:
        conn.execute('UPDATE script_data SET content = ? WHERE id = 1', (data['content'],))
    return jsonify({"status": "success"})

@app.route('/get_script', methods=['GET'])
def get_script():
    with sqlite3.connect('shots.db') as conn:
        row = conn.execute('SELECT content FROM script_data WHERE id = 1').fetchone()
    return jsonify({"content": row[0] if row else ""})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_shots', methods=['GET'])
def get_shots():
    with sqlite3.connect('shots.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM shots ORDER BY cast(SUBSTR(scene_num, 4, 2) as INT), shot_label ASC')
        shots = [dict(row) for row in cursor.fetchall()]
    return jsonify(shots)

@app.route('/save_shot', methods=['POST'])
def save_shot():
    data = request.json
    with sqlite3.connect('shots.db') as conn:
        conn.execute('''INSERT INTO shots (scene_num, shot_label, size, frame, angle, extras, placement, snippet, notes) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (data['scene'], data['label'], data['size'], data['frame'], 
                      data['angle'], data['extras'], data['placement'], data['snippet'], data['notes']))
    return jsonify({"status": "success"})

@app.route('/export')
def export_csv():
    with sqlite3.connect('shots.db') as conn:
        cursor = conn.execute('SELECT scene_num, shot_label, size, frame, angle, extras, placement, notes, snippet FROM shots')
        rows = cursor.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Scene', 'Shot #', 'Size', 'Frame', 'Angle', 'Movement', 'Camera Placement', 'Notes', 'Script Snippet'])
    writer.writerows(rows)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=shot_list.csv"})

@app.route('/delete_shot/<int:shot_id>', methods=['DELETE'])
def delete_shot(shot_id):
    with sqlite3.connect('shots.db') as conn:
        conn.execute('DELETE FROM shots WHERE id = ?', (shot_id,))
    return jsonify({"status": "success"})

@app.route('/update_shot', methods=['POST'])
def update_shot():
    data = request.json
    with sqlite3.connect('shots.db') as conn:
        conn.execute('''UPDATE shots SET shot_label=?, size=?, frame=?, angle=?, extras=?, placement=?, notes=? 
                        WHERE id = ?''', 
                     (data['label'], data['size'], data['frame'], data['angle'], 
                      data['extras'], data['placement'], data['notes'], data['id']))
    return jsonify({"status": "success"})

# --- CRITICAL FIX: Added r''' to avoid Syntax Warnings and fixed the rendering logic ---
HTML_TEMPLATE = r'''
<!DOCTYPE html>
<script src="https://cdn.tailwindcss.com"></script>
<script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap" rel="stylesheet">

<style>
    .screenplay-font { font-family: 'Courier Prime', monospace; }
    .script-container { line-height: 1.5; white-space: pre-wrap; padding: 60px 80px; min-height: 100%; }
    .scene-header { font-weight: bold; color: #2563eb; border-bottom: 2px solid #dbeafe; margin-top: 2rem; margin-bottom: 1rem; display: block; text-align: center; }
</style>

<body class="bg-gray-900 text-gray-100 p-4 screenplay-font" x-data="shotApp()" x-init="async () => { 
    await fetchShots(); 
    const res = await fetch('/get_script');
    const data = await res.json();
    this.fullScript = data.content;
    if (this.fullScript) {
        this.processScript();
        this.editMode = false; // Auto-lock if script exists
    }
}">
    
    <nav class="flex justify-between items-center bg-gray-800 p-4 rounded-xl mb-6 shadow-lg font-sans">
        <div class="flex items-center gap-6">
            <h2 class="text-xl font-bold text-blue-400 italic">THE EIGHTH HOUSE</h2>
            <button @click="view = 'script'" :class="view === 'script' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400'" class="pb-1 font-bold uppercase text-xs">Script View</button>
            <button @click="view = 'list'; fetchShots()" :class="view === 'list' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400'" class="pb-1 font-bold uppercase text-xs">Shot List</button>
        </div>
        <div class="flex items-center gap-2 ml-4" x-show="view === 'script' && !editMode">
            <label class="text-[10px] text-gray-500 uppercase font-black">Jump to:</label>
            <select @change="scrollToScene($event.target.value)" class="bg-gray-900 text-blue-400 text-xs font-bold p-1 rounded border border-gray-700 outline-none">
                <option value="">Select Scene...</option>
                <template x-for="scene in sceneList" :key="scene.id">
                    <option :value="scene.id" x-text="scene.name"></option>
                </template>
            </select>
        </div>
        <a href="/export" class="bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded text-xs font-bold uppercase">Export CSV</a>
    </nav>

    <div class="grid grid-cols-12 gap-6 h-[85vh] overflow-y-auto">
        
        <template x-if="view === 'script'">
            <div class="col-span-12 grid grid-cols-12 gap-6 h-full">
                <div id="script-viewport" class="col-span-7 flex flex-col overflow-y-auto bg-gray-950 rounded-lg border border-gray-800">
                    <div class="p-2 border-b border-gray-800 flex justify-end">
                        <button @click="toggleMode()" class="text-xs bg-blue-600 px-4 py-1 rounded font-sans font-bold" x-text="editMode ? 'LOCK & FORMAT' : 'BACK TO EDIT'"></button>
                    </div>

                    <textarea x-show="editMode" x-model="fullScript" class="w-full h-full bg-transparent p-8 text-sm outline-none resize-none" placeholder="Paste your script here..."></textarea>
                    
                    <div x-show="!editMode" @mouseup="captureSelection()" 
                         class="flex-grow bg-white text-black overflow-y-auto script-container shadow-inner selection:bg-blue-200" 
                         x-html="formattedScript">
                    </div>
                </div>

                <div class="col-span-5 font-sans">
                    <template x-if="showForm">
                        <div class="bg-gray-800 p-8 rounded-xl border-l-4 border-blue-500 shadow-2xl sticky top-4">
                            <h3 class="text-blue-400 font-bold mb-4 uppercase text-sm tracking-widest" x-text="form.scene"></h3>
                            
                            <div class="bg-gray-900 p-4 rounded mb-6 italic text-gray-400 border border-gray-700 text-sm">
                                "<span x-text="currentSnippet"></span>"
                            </div>

                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="text-[10px] text-gray-500 uppercase font-black">Shot #</label>
                                    <input x-model="form.label" class="w-full bg-gray-700 p-3 rounded border border-gray-600 text-white focus:border-blue-400 outline-none">
                                </div>
                                <div>
                                    <label class="text-[10px] text-gray-500 uppercase font-black">Size</label>
                                    <select x-model="form.size" class="w-full bg-gray-700 p-3 rounded border border-gray-600 text-white">
                                        <option value="EWS (Extreme Wide Shot)">EWS (Extreme Wide Shot)</option>
                                        <option value="WS (Wide Shot)">WS (Wide Shot)</option>
                                        <option value="FS (Full Shot)">FS (Full Shot)</option>
                                        <option value="MWS (Medium Wide Shot)">MWS (Medium Wide Shot)</option>
                                        <option value="CS (Cowboy Shot)" selected>CS (Cowboy Shot)</option>
                                        <option value="MS (Medium Shot)" selected>MS (Medium Shot)</option>
                                        <option value="MCU (Medium Close Up)">MCU (Medium Close Up)</option>
                                        <option value="CU (Close Up)">CU (Close Up)</option>
                                        <option value="ECU (Extreme Close Up)">ECU (Extreme Close Up)</option>
                                        <option value="POV">POV</option>
                                        <option value="Insert">Insert</option>
                                    </select>
                                </div>
                            </div>

                            <div class="grid grid-cols-2 gap-4 mt-4">
                                <div>
                                    <label class="text-[10px] text-gray-500 uppercase font-black">Frame</label>
                                    <select x-model="form.frame" class="w-full bg-gray-700 p-3 rounded border border-gray-600 text-white">
                                        <option selected>Single</option>
                                        <option>Two-Shot</option>
                                        <option>Three-Shot</option>
                                        <option>Group Shot</option>
                                        <option>OTS (Over the Shoulder)</option>
                                        <option>POV</option>
                                        <option>Insert</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="text-[10px] text-gray-500 uppercase font-black">Angle</label>
                                    <select x-model="form.angle" class="w-full bg-gray-700 p-3 rounded border border-gray-600 text-white">
                                        <option selected>Eye Level</option>
                                        <option selected>Ground Level</option>
                                        <option>Low Angle</option>
                                        <option>High Angle</option>
                                        <option>Dutch Angle</option>
                                        <option>Bird's Eye</option>
                                        <option>Worm's Eye</option>
                                    </select>
                                </div>
                            </div>

                            <div class="mt-4">
                                <label class="text-[10px] text-gray-500 uppercase font-black">Movement</label>
                                <select x-model="form.extras" class="w-full bg-gray-700 p-3 rounded border border-gray-600 text-white">
                                    <option selected>Static</option>
                                    <option>Pan</option>
                                    <option>Tilt</option>
                                    <option>Dolly / Tracking</option>
                                    <option>Handheld</option>
                                    <option>Zoom</option>
                                    <option>Arc</option>
                                    <option>Dolly Zoom</option>
                                    <option>Crane / Jib</option>
                                </select>
                            </div>

                            <div class="mt-4">
                                <label class="text-[10px] text-gray-500 uppercase font-black">Camera Placement</label>
                                <input x-model="form.placement" placeholder="e.g. Low, behind the package" 
                                    class="w-full bg-gray-700 p-3 rounded border border-gray-600 text-white focus:border-blue-400 outline-none">
                            </div>

                            <div class="mt-4">
                                <label class="text-[10px] text-gray-500 uppercase font-black">Notes</label>
                                <textarea x-model="form.notes" placeholder="Lighting, character focus, or SFX..." class="w-full bg-gray-700 p-3 rounded border border-gray-600 h-20 outline-none focus:border-blue-400"></textarea>
                            </div>

                            <button @click="submitShot()" class="mt-6 bg-blue-600 hover:bg-blue-500 w-full py-4 rounded font-bold shadow-lg transition-transform active:scale-95">SAVE SHOT</button>
                        </div>
                    </template>
                </div>
            </div>
        </template>

        <template x-if="view === 'list'">
            <div class="col-span-12 overflow-y-auto font-sans pb-10">
                <template x-for="(sceneShots, sceneName) in groupedShots" :key="sceneName">
                    <div class="mb-4 bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
                        
                        <div @click="toggleScene(sceneName)" 
                            class="flex justify-between items-center p-4 cursor-pointer hover:bg-gray-800 transition-colors group">
                            <div class="flex items-center gap-4">
                                <svg xmlns="http://www.w3.org/2000/svg" 
                                    class="h-5 w-5 text-blue-500 transition-transform duration-200"
                                    :class="isSceneOpen(sceneName) ? 'rotate-180' : ''" 
                                    fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M19 9l-7 7-7-7" />
                                </svg>
                                <h3 class="text-lg font-bold text-blue-400 uppercase tracking-wide" x-text="sceneName"></h3>
                            </div>
                            <span class="text-[10px] text-gray-500 font-bold bg-gray-900 px-3 py-1 rounded-full group-hover:text-gray-300" 
                                x-text="sceneShots.length + ' SHOTS'"></span>
                        </div>

                        <div x-show="isSceneOpen(sceneName)" 
                            x-transition:enter="transition ease-out duration-200"
                            x-transition:enter-start="opacity-0 -translate-y-2"
                            x-transition:enter-end="opacity-100 translate-y-0"
                            class="p-4 pt-0 space-y-2">
                            
                            <template x-for="shot in sceneShots" :key="shot.id">
                                <div @click="selectedShot = shot" 
                                    class="bg-gray-800 p-4 rounded-lg flex justify-between items-center hover:bg-gray-700 cursor-pointer border border-transparent hover:border-blue-500/50 transition shadow-sm">
                                    <div class="flex gap-6 items-center">
                                        <span class="text-blue-500 font-black w-10 text-center" x-text="shot.shot_label || '-'"></span>
                                        <div class="flex flex-col">
                                            <span class="text-sm font-bold text-white uppercase" x-text="shot.size"></span>
                                            <span class="text-[10px] text-gray-500 font-mono" x-text="shot.placement || 'No placement set'"></span>
                                        </div>
                                    </div>
                                    <div class="text-xs text-gray-400 italic flex-grow px-10 truncate opacity-60" x-text="shot.snippet"></div>
                                    <div class="flex items-center gap-2">
                                        <span class="text-[9px] bg-blue-900/30 text-blue-400 px-2 py-1 rounded uppercase font-bold" x-text="shot.extras"></span>
                                        <span class="text-gray-600">→</span>
                                    </div>
                                </div>
                            </template>
                        </div>

                    </div>
                </template>
            </div>
        </template>
    </div>

    <template x-if="selectedShot">
        <div class="fixed inset-0 bg-black/90 flex items-center justify-center p-6 z-50 font-sans">
            <div class="bg-gray-800 p-8 rounded-2xl max-w-2xl w-full border border-gray-700 shadow-2xl relative max-h-[90vh] overflow-y-auto">
                
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h2 class="text-2xl font-bold text-blue-400 mb-1" x-text="'Edit Shot ' + selectedShot.shot_label"></h2>
                        <p class="text-xs text-gray-500 uppercase tracking-widest" x-text="selectedShot.scene_num"></p>
                    </div>
                    <button @click="selectedShot = null" class="text-gray-400 hover:text-white text-3xl">&times;</button>
                </div>

                <div class="grid grid-cols-2 gap-6 mb-6">
                    <div>
                        <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Shot #</label>
                        <input x-model="selectedShot.shot_label" class="w-full bg-gray-900 p-3 rounded border border-gray-700 text-white">
                    </div>

                    <div>
                        <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Size</label>
                        <select x-model="selectedShot.size" class="w-full bg-gray-900 p-3 rounded border border-gray-700 text-white">
                            <option>EWS (Extreme Wide Shot)</option>
                            <option>WS (Wide Shot)</option>
                            <option>FS (Full Shot)</option>
                            <option>MWS (Medium Wide Shot)</option>
                            <option>CS (Cowboy Shot)</option>
                            <option>MS (Medium Shot)</option>
                            <option>MCU (Medium Close Up)</option>
                            <option>CU (Close Up)</option>
                            <option>ECU (Extreme Close Up)</option>
                            <option>POV</option>
                            <option>Insert</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Frame</label>
                        <select x-model="selectedShot.frame" class="w-full bg-gray-900 p-3 rounded border border-gray-700 text-white">
                            <option>Single</option>
                            <option>Two-Shot</option>
                            <option>Three-Shot</option>
                            <option>Group Shot</option>
                            <option>OTS (Over the Shoulder)</option>
                            <option>POV</option>
                            <option>Insert</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Angle</label>
                        <select x-model="selectedShot.angle" class="w-full bg-gray-900 p-3 rounded border border-gray-700 text-white">
                            <option>Eye Level</option>
                            <option>Ground Level</option>
                            <option>Low Angle</option>
                            <option>High Angle</option>
                            <option>Dutch Angle</option>
                            <option>Bird's Eye</option>
                            <option>Worm's Eye</option>
                        </select>
                    </div>
                </div>

                <div class="mb-6">
                    <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Movement</label>
                    <select x-model="selectedShot.extras" class="w-full bg-gray-900 p-3 rounded border border-gray-700 text-white">
                        <option>Static</option>
                        <option>Pan</option>
                        <option>Tilt</option>
                        <option>Dolly / Tracking</option>
                        <option>Handheld</option>
                        <option>Zoom</option>
                        <option>Arc</option>
                        <option>Dolly Zoom</option>
                        <option>Crane / Jib</option>
                    </select>
                </div>

                <div class="mb-6">
                    <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Camera Placement</label>
                    <input x-model="selectedShot.placement" class="w-full bg-gray-900 p-3 rounded border border-gray-700 text-white">
                </div>

                <div class="mb-6">
                    <label class="text-[10px] text-gray-500 uppercase font-black block mb-1">Director Notes</label>
                    <textarea x-model="selectedShot.notes" class="w-full bg-gray-900 p-3 rounded border border-gray-700 h-24 outline-none focus:border-blue-500 transition-colors"></textarea>
                </div>

                <div class="bg-gray-950 p-4 rounded-lg border-l-2 border-blue-500 mb-8">
                    <p class="text-[10px] text-blue-500 font-bold uppercase mb-1">Original Script Snippet</p>
                    <p class="italic text-gray-400 screenplay-font text-sm" x-text="selectedShot.snippet"></p>
                </div>

                <div class="mb-6">
                    <label class="text-[10px] text-gray-500 uppercase font-black">Storyboard Filename</label>
                    <input x-model="selectedShot.image_url" placeholder="e.g. frame1.png" class="w-full bg-gray-900 p-2 rounded border border-gray-700 text-white">
                </div>
                
                <div class="flex justify-between gap-4">
                    <button @click="deleteShot(selectedShot.id)" class="bg-red-950 hover:bg-red-900 text-red-400 px-6 py-3 rounded-lg font-bold text-xs transition-colors">DELETE PERMANENTLY</button>
                    <button @click="saveChanges()" class="flex-grow bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-lg font-bold shadow-lg transition-transform active:scale-95">UPDATE SHOT</button>
                </div>
            </div>
        </div>
    </template>

    <script>
        function shotApp() {
            return {
                view: 'script',
                editMode: true,
                fullScript: '',
                formattedScript: '',
                showForm: false,
                currentSnippet: '',
                selectedShot: null,
                allShots: [],
                form: { label: '', size: 'MS (Medium Shot)', frame: 'Single', angle: 'Eye Level', extras: 'Static', scene: '', notes: '', placement: '' },
                
                get groupedShots() {
                    return this.allShots.reduce((groups, shot) => {
                        const scene = shot.scene_num;
                        if (!groups[scene]) groups[scene] = [];
                        groups[scene].push(shot);
                        return groups;
                    }, {});
                },

                openScenes: [], // Tracks which scene names are currently expanded

                toggleScene(sceneName) {
                    if (this.openScenes.includes(sceneName)) {
                        // If it's in the list, remove it (Collapse)
                        this.openScenes = this.openScenes.filter(s => s !== sceneName);
                    } else {
                        // If it's not, add it (Expand)
                        this.openScenes.push(sceneName);
                    }
                },

                isSceneOpen(sceneName) {
                    return this.openScenes.includes(sceneName);
                },

                async fetchShots() {
                    const res = await fetch('/get_shots');
                    this.allShots = await res.json();
                    
                    // OPTIONAL: Auto-expand the first scene or all scenes on load
                    if (this.openScenes.length === 0 && this.allShots.length > 0) {
                        const firstScene = this.allShots[0].scene_num;
                        this.openScenes.push(firstScene);
                    }
                },

                async toggleMode() {
                    if (this.editMode) {
                        // Save to DB when locking
                        await fetch('/save_script', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ content: this.fullScript })
                        });
                        this.processScript();
                    }
                    this.editMode = !this.editMode;
                },

                processScript() {
                    if (!this.fullScript.trim()) {
                        this.formattedScript = "Script is empty.";
                        return;
                    }
                    let sceneCount = 0;
                    this.sceneList = [];
                    const lines = this.fullScript.split('\n');
                    const processed = lines.map(line => {
                        if (line.trim().match(/^(INT\.|EXT\.)/i)) {
                            sceneCount++;
                            const sceneId = `scene-${sceneCount}`;
                            const sceneName = `SC ${sceneCount}: ${line.toUpperCase()}`;
                            
                            // Add to our navigation list
                            this.sceneList.push({ id: sceneId, name: sceneName });
                            // Wrap with an ID so we can jump to it
                            return `<span id="${sceneId}" class="scene-header">SCENE ${sceneCount}: ${line.toUpperCase()}</span>`;
                        }
                        return line;
                    });
                    this.formattedScript = processed.join('<br>');
                },

                scrollToScene(sceneId) {
                    if (!sceneId) return;
                    const element = document.getElementById(sceneId);
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                },

                async fetchShots() {
                    const res = await fetch('/get_shots');
                    this.allShots = await res.json();
                },

                captureSelection() {
                    let selection = window.getSelection();
                    let text = selection.toString().trim();
                    if (!text || this.editMode) return;
                    this.currentSnippet = text;
                    
                    // 1. Get the vertical position (Y-coordinate) of your selection
                    const range = selection.getRangeAt(0);
                    const rect = range.getBoundingClientRect();
                    const selectionTop = rect.top + window.scrollY;

                    // 2. Grab all the scene headers currently in the script
                    const headers = Array.from(document.querySelectorAll('.scene-header'));
                    
                    // 3. Find the header that is closest to the selection but ABOVE it
                    let activeHeader = null;
                    
                    headers.forEach(header => {
                        const headerTop = header.getBoundingClientRect().top + window.scrollY;
                        // If this header is above our selection, it's a candidate
                        if (headerTop < selectionTop) {
                            activeHeader = header.innerText;
                        }
                    });

                    if (activeHeader) {
                        // Formats "SCENE 1: INT. KITCHEN" to "SC 1: INT. KITCHEN"
                        this.form.scene = activeHeader.replace('SCENE ', 'SC ');
                    } else {
                        this.form.scene = "SC 0: PROLOGUE";
                    }

                    this.showForm = true;
                },

                async submitShot() {
                    await fetch('/save_shot', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({...this.form, snippet: this.currentSnippet})
                    });
                    this.showForm = false;
                    this.form.label = ''; 
                    this.form.notes = '';
                    this.fetchShots();
                },

                async deleteShot(id) {
                    if (!confirm("Are you sure you want to delete this shot?")) return;
                    const res = await fetch(`/delete_shot/${id}`, { method: 'DELETE' });
                    if (res.ok) {
                        this.selectedShot = null;
                        this.fetchShots(); // Refresh the list
                    }
                },

                async saveChanges() {
                    if (!this.selectedShot) return;
                    
                    const response = await fetch('/update_shot', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            id: this.selectedShot.id,
                            label: this.selectedShot.shot_label,
                            size: this.selectedShot.size,
                            frame: this.selectedShot.frame,
                            placement: this.selectedShot.placement,
                            angle: this.selectedShot.angle,
                            extras: this.selectedShot.extras,
                            notes: this.selectedShot.notes
                        })
                    });

                    if (response.ok) {
                        this.selectedShot = null;
                        this.fetchShots(); // Refresh the list view
                    } else {
                        alert("Failed to update shot.");
                    }
                }
            }
        }
    </script>
</body>
'''

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
