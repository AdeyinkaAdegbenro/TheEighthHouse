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
        projectList: [],

        // breakdown states
        breakdownItems: [],
        editingBreakdownItem: null, // Holds the item currently being edited
        showBreakdownPanel: false, // Toggles the breakdown view
        activeBreakdownScene: '', // Track which scene we are currently viewing/editing details for
        newBreakdownItem: {
            category: 'Props',
            item_name: '',
            notes: ''
        },

        breakdownForm: {
            category: 'Props',
            item_name: '',
            notes: '',
            scene_num: ''
        },

        async init() {
            try {
                const pRes = await fetch('/get_projects');
                this.projectList = await pRes.json();
            } catch (err) {
                console.error("Error loading project list:", err);
            }
            await this.loadProjectWorkspace(); // Load the workspace for the initial project
        },

        async loadProjectWorkspace() {
            this.showForm = false; // Hide any open highlighting cards
            this.allShots = [];
            this.breakdownItems = [];
            
            // Fetch shots for the newly active movie
            await this.fetchShots();

            // Fetch and process the screenplay script tied to this project ID
            const res = await fetch(`/${this.currentProjectId}/get_script`);
            const data = await res.json();
            this.fullScript = data.content || "";
            
            if (this.fullScript) {
                this.processScript();
                this.editMode = false;
            } else {
                this.formattedScript = "";
                this.sceneList = [];
                this.editMode = true; // Open editor if the new film has no text yet
            }

            // If you are currently sitting on the Breakdown View tab, refresh its master sheet list too
            if (this.view === 'breakdown') {
                await this.fetchAllBreakdowns();
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

            const computedScene = activeHeader ? activeHeader.replace('SCENE ', 'SC ') : "SC 0: PROLOGUE";

            this.form.scene = computedScene;

            // 2. Populate the Selection Tagging setup with highlighted text
            this.breakdownForm.scene_num = computedScene;
            this.breakdownForm.item_name = text;
            this.breakdownForm.notes = '';

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
        },
        // --- BREAKDOWN METHODS ---

        async fetchAllBreakdowns() {
            try {
                const res = await fetch(`/${this.currentProjectId}/get_all_breakdowns`);
                this.breakdownItems = await res.json();
            } catch (err) {
                console.error("Error fetching project breakdowns:", err);
            }
        },

        // Fetch all breakdown items for a specific scene
        async fetchBreakdown(sceneNum) {
            this.activeBreakdownScene = sceneNum;
            try {
                const res = await fetch(`/${this.currentProjectId}/${sceneNum}/get_breakdown`);
                this.breakdownItems = await res.json();
                this.showBreakdownPanel = true;
            } catch (err) {
                console.error("Error fetching breakdown:", err);
            }
        },

        // Save a newly created breakdown item
        async saveBreakdownItem() {
            if (!this.newBreakdownItem.item_name.trim()) return;

            const payload = {
                project_id: this.currentProjectId,
                scene_num: this.activeBreakdownScene,
                category: this.newBreakdownItem.category,
                item_name: this.newBreakdownItem.item_name,
                notes: this.newBreakdownItem.notes
            };

            try {
                const res = await fetch('/save_breakdown_item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    // Reset input form
                    this.newBreakdownItem.item_name = '';
                    this.newBreakdownItem.notes = '';
                    // Refresh list
                    await this.fetchBreakdown(this.activeBreakdownScene);
                }
            } catch (err) {
                console.error("Error saving breakdown item:", err);
            }
        },

        async submitBreakdownForm() {
            if (!this.breakdownForm.item_name.trim()) return;

            const payload = {
                project_id: this.currentProjectId,
                scene_num: this.breakdownForm.scene_num,
                category: this.breakdownForm.category,
                item_name: this.breakdownForm.item_name,
                notes: this.breakdownForm.notes
            };

            try {
                const res = await fetch('/save_breakdown_item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    this.showForm = false; // Close the right-hand panel card
                    this.breakdownForm.item_name = '';
                    this.breakdownForm.notes = '';
                    
                    // If the sliding list panel is currently open for this scene, refresh it!
                    if (this.showBreakdownPanel && this.activeBreakdownScene === payload.scene_num) {
                        await this.fetchBreakdown(this.activeBreakdownScene);
                    }
                }
            } catch (err) {
                console.error("Error saving highlighted breakdown item:", err);
            }
        },

        // Put an item into edit mode
        startEditBreakdown(item) {
            this.editingBreakdownItem = { ...item };
        },

        // Cancel editing
        cancelEditBreakdown() {
            this.editingBreakdownItem = null;
        },

        // Update an existing breakdown item
        async updateBreakdownItem() {
            if (!this.editingBreakdownItem.item_name.trim()) return;

            try {
                const res = await fetch('/update_breakdown_item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.editingBreakdownItem)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    this.editingBreakdownItem = null;
                    await this.fetchBreakdown(this.activeBreakdownScene);
                }
            } catch (err) {
                console.error("Error updating breakdown item:", err);
            }
        },

        // Delete a breakdown item
        async deleteBreakdownItem(itemId) {
            if (!confirm("Are you sure you want to remove this item from the breakdown?")) return;

            try {
                const res = await fetch(`/delete_breakdown_item/${itemId}`, {
                    method: 'DELETE'
                });
                const data = await res.json();
                if (data.status === 'success') {
                    if (this.view === 'breakdown') {
                        await this.fetchAllBreakdowns(); // Refreshes the master view state instantly!
                    } else {
                        // Fallback for the side panel overlay context
                        await this.fetchBreakdown(this.activeBreakdownScene);
                    }

                }
            } catch (err) {
                console.error("Error deleting breakdown item:", err);
            }
        }
    }
}