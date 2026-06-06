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
        sceneList: [],
        openScenes: [],
        form: { label: '', size: 'MS (Medium Shot)', frame: 'Single', angle: 'Eye Level', extras: 'Static', scene: '', notes: '', placement: '' },
        currentProjectId: 1,

        async init() {
            await this.fetchShots();
            // Fetch the specific script tied to this project ID
            const res = await fetch(`/${this.currentProjectId}/get_script`);
            const data = await res.json();
            this.fullScript = data.content;
            if (this.fullScript) {
                this.processScript();
                this.editMode = false;
            }
        },

        get groupedShots() {
            return this.allShots.reduce((groups, shot) => {
                const scene = shot.scene_num;
                if (!groups[scene]) groups[scene] = [];
                groups[scene].push(shot);
                return groups;
            }, {});
        },

        async fetchShots() {
            // Dynamically query by project ID
            const res = await fetch(`/${this.currentProjectId}/get_shots`);
            this.allShots = await res.json();
            
            if (this.openScenes.length === 0 && this.allShots.length > 0) {
                const firstScene = this.allShots[0].scene_num;
                this.openScenes.push(firstScene);
            }
        },

        async toggleMode() {
            if (this.editMode) {
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
            if (!this.fullScript.trim()) return;
            let sceneCount = 0;
            this.sceneList = [];
            const lines = this.fullScript.split('\n');
            const processed = lines.map(line => {
                if (line.trim().match(/^(INT\.|EXT\.)/i)) {
                    sceneCount++;
                    const id = `scene-${sceneCount}`;
                    const name = `SC ${sceneCount}: ${line.toUpperCase()}`;
                    this.sceneList.push({ id, name });
                    return `<span id="${id}" class="scene-header">SCENE ${sceneCount}: ${line.toUpperCase()}</span>`;
                }
                return line;
            });
            this.formattedScript = processed.join('<br>');
        },

        captureSelection() {
            let sel = window.getSelection();
            let text = sel.toString().trim();
            if (!text || this.editMode) return;
            this.currentSnippet = text;
            
            const range = sel.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            const selectionTop = rect.top + window.scrollY;
            const headers = Array.from(document.querySelectorAll('.scene-header'));
            
            let activeHeader = null;
            headers.forEach(h => {
                if ((h.getBoundingClientRect().top + window.scrollY) < selectionTop) {
                    activeHeader = h.innerText;
                }
            });

            this.form.scene = activeHeader ? activeHeader.replace('SCENE ', 'SC ') : "SC 0: PROLOGUE";
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
            await this.fetchShots();
        },

        toggleScene(name) {
            this.openScenes = this.openScenes.includes(name) 
                ? this.openScenes.filter(s => s !== name) 
                : [...this.openScenes, name];
        },

        scrollToScene(id) {
            const el = document.getElementById(id);
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },

        isSceneOpen(sceneName) {
            return this.openScenes.includes(sceneName);
        },

        // Add this inside your shotApp data
        placeholder: 'https://placehold.co/600x400/111827/3b82f6?text=NO+VISUAL+ASSIGNED',

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
                    notes: this.selectedShot.notes,
                    image_url: this.selectedShot.image_url
                })
            });

            if (response.ok) {
                this.selectedShot = null;
                this.fetchShots(); // Refresh the list view
            } else {
                alert("Failed to update shot.");
            }
        },

        // Add this to your shotApp() object
        async uploadFile(event, shotId) {
            const file = event.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch(`/upload_storyboard/${shotId}`, {
                    method: 'POST',
                    body: formData
                });
                
                if (res.ok) {
                    // Refresh shots to show the new image immediately
                    await this.fetchShots();
                }
            } catch (err) {
                console.error("Upload failed", err);
            }
        }
    }
}