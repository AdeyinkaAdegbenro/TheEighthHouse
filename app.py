from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import io
import os
import csv
from flask import send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Define where your project images live
UPLOAD_FOLDER = 'static/projects/last_parcel'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('shots.db')
    conn.row_factory = sqlite3.Row
    return conn

# SURGICAL UPDATE: Replace init_db() in app.py
def init_db():
    with get_db_connection() as conn:
        # 1. Master Projects Table
        conn.execute('''CREATE TABLE IF NOT EXISTS projects 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             title TEXT NOT NULL,
             folder_name TEXT NOT NULL UNIQUE)''') # e.g., 'last_parcel'

        # 2. Shots Table (Ensure project_id column exists)
        conn.execute('''CREATE TABLE IF NOT EXISTS shots 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             project_id INTEGER, -- Will set as foreign key constraint later if needed
             scene_num TEXT, shot_label TEXT, size TEXT, 
             frame TEXT, angle TEXT, extras TEXT, placement TEXT,
             snippet TEXT, notes TEXT, image_url TEXT)''')
        
        # 3. Script Data Table
        conn.execute('''CREATE TABLE IF NOT EXISTS script_data 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             project_id INTEGER UNIQUE, 
             content TEXT)''')

        # --- SEAMLESS MIGRATION PATCHES ---
        # Seed your first project baseline safely
        conn.execute('INSERT OR IGNORE INTO projects (id, title, folder_name) VALUES (1, "The Last Parcel", "last_parcel")')
        conn.execute('INSERT OR IGNORE INTO script_data (project_id, content) VALUES (1, "")')

        # Migration: Safely add project_id to shots table if it wasn't there
        try:
            conn.execute('ALTER TABLE shots ADD COLUMN project_id INTEGER DEFAULT 1')
            print("Migration Successful: project_id added to shots table.")
        except sqlite3.OperationalError:
            pass # Column already exists

    conn.commit()

# SURGICAL UPDATE: Update routes to target the unique project_id integer
@app.route('/<int:project_id>/get_shots', methods=['GET'])
def get_shots(project_id):
    with get_db_connection() as conn:
        cursor = conn.execute('SELECT * FROM shots WHERE project_id = ? ORDER BY id ASC', (project_id,))
        shots = [dict(row) for row in cursor.fetchall()]
    return jsonify(shots)

@app.route('/<int:project_id>/get_script', methods=['GET'])
def get_script(project_id):
    with get_db_connection() as conn:
        row = conn.execute('SELECT content FROM script_data WHERE project_id = ?', (project_id,)).fetchone()
    return jsonify({"content": row['content'] if row else ""})

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/save_script', methods=['POST'])
def save_script():
    content = request.json.get('content')
    with get_db_connection() as conn:
        conn.execute('UPDATE script_data SET content = ? WHERE project_id = ?', (content, 1))
    return jsonify({"status": "success"})



@app.route('/save_shot', methods=['POST'])
def save_shot():
    d = request.json
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO shots (project_id, scene_num, shot_label, size, frame, angle, extras, placement, snippet, notes) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (d['project_id'], d['scene'], d['label'], d['size'], d['frame'], d['angle'], d['extras'], d['placement'], d['snippet'], d['notes']))
    return jsonify({"status": "success"})

@app.route('/update_shot', methods=['POST'])
def update_shot():
    d = request.json
    with get_db_connection() as conn:
        conn.execute('''UPDATE shots SET shot_label=?, size=?, frame=?, angle=?, extras=?, placement=?, notes=?, image_url=? 
                        WHERE id = ?''', 
                     (d['label'], d['size'], d['frame'], d['angle'], d['extras'], d['placement'], d['notes'], d.get('image_url'), d['id']))
    return jsonify({"status": "success"})

@app.route('/delete_shot/<int:shot_id>', methods=['DELETE'])
def delete_shot(shot_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM shots WHERE id = ?', (shot_id,))
    return jsonify({"status": "success"})

@app.route('/media/<path:full_path>')
def serve_external_file(full_path):
    # This route bridges your Mac file system to the browser
    # We add the leading '/' back for Mac paths
    absolute_path = '/' + full_path
    if os.path.exists(absolute_path):
        return send_file(absolute_path)
    return "File not found", 404

@app.route('/upload_storyboard/<int:shot_id>', methods=['POST'])
def upload_storyboard(shot_id):
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        # Ensure directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Update Database
        with sqlite3.connect('shots.db') as conn:
            conn.execute('UPDATE shots SET image_url = ? WHERE id = ?', (filename, shot_id))
        
        return jsonify({"status": "success", "filename": filename})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)