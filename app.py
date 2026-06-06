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

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS shots 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             scene_num TEXT, shot_label TEXT, size TEXT, 
             frame TEXT, angle TEXT, extras TEXT, placement TEXT,
             snippet TEXT, notes TEXT, image_url TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS script_data 
                        (id INTEGER PRIMARY KEY, content TEXT)''')
        conn.execute('INSERT OR IGNORE INTO script_data (id, content) VALUES (1, "")')
    conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_script')
def get_script():
    with get_db_connection() as conn:
        row = conn.execute('SELECT content FROM script_data WHERE id = 1').fetchone()
    return jsonify({"content": row['content'] if row else ""})

@app.route('/save_script', methods=['POST'])
def save_script():
    content = request.json.get('content')
    with get_db_connection() as conn:
        conn.execute('UPDATE script_data SET content = ? WHERE id = 1', (content,))
    return jsonify({"status": "success"})

@app.route('/get_shots')
def get_shots():
    with get_db_connection() as conn:
        # Sorting by scene number and then shot label
        cursor = conn.execute('SELECT * FROM shots ORDER BY cast(SUBSTR(scene_num, 4, 2) as INT), shot_label ASC;')
        shots = [dict(row) for row in cursor.fetchall()]
    return jsonify(shots)

@app.route('/save_shot', methods=['POST'])
def save_shot():
    d = request.json
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO shots (scene_num, shot_label, size, frame, angle, extras, placement, snippet, notes) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (d['scene'], d['label'], d['size'], d['frame'], d['angle'], d['extras'], d['placement'], d['snippet'], d['notes']))
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