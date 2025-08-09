from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    make_response,
    send_file,
)
import uuid
import os
from datetime import datetime, timedelta, timezone
from utils.sql import SQL
import shutil

TRUNKS_DIR = "temp_chunks"
STORAGE_DIR = "storage"
db_url = "database.db"

app = Flask(__name__)


@app.route("/upload-chunk", methods=["POST"])
def upload_chunk():
    user_id = request.cookies.get("u_id")
    if not user_id:
        return jsonify({"msg": "missing u_id"}), 400

    try:
        file_id = request.form["fileId"]
        file_name = request.form["fileName"]
        chunk_index = int(request.form["chunkIndex"])
        total_chunks = int(request.form["totalChunks"])
        chunk = request.files["chunk"]
    except (KeyError, ValueError):
        return jsonify({"msg": "invalid form data"}), 400

    try:
        file_id = str(uuid.UUID(file_id))
    except ValueError:
        return jsonify({"msg": "invalid fileId"}), 400

    temp_dir = os.path.join(TRUNKS_DIR, file_id)
    temp_dir_abs = os.path.abspath(temp_dir)
    os.makedirs(temp_dir_abs, exist_ok=True)

    chunk_path = os.path.join(temp_dir_abs, f"chunk_{chunk_index}")
    chunk_path_abs = os.path.abspath(chunk_path)
    chunk.save(chunk_path_abs)

    if len(os.listdir(temp_dir_abs)) == total_chunks:
        final_path = os.path.join(STORAGE_DIR, file_id)
        final_path_abs = os.path.abspath(final_path)

        with open(final_path_abs, "wb") as f:
            for i in range(total_chunks):
                part_path = os.path.join(temp_dir_abs, f"chunk_{i}")
                with open(part_path, "rb") as cf:
                    f.write(cf.read())

        shutil.rmtree(temp_dir_abs)

        try:
            db = SQL(db_url)
            db.execute(
                "INSERT INTO files (id, name, u_id) VALUES (?, ?, ?)",
                (file_id, file_name, user_id),
            )
        except Exception as e:
            return jsonify({"msg": f"saving failed {e}"}), 500

    return "", 200


@app.route("/file", methods=["GET"])
def file():
    id: str = request.args["id"]

    try:
        uuid.UUID(id)
    except ValueError:
        return jsonify({"msg": "invalid id"}), 400

    db = SQL(db_url)
    file_data = db.execute("SELECT id, name, u_id FROM files WHERE id=?", (id,))

    if not file_data or isinstance(file_data, int):
        return jsonify({"msg": "file not found"}), 404

    id: str = file_data[0]["id"]
    name: str = file_data[0]["name"]

    return send_file(
        path_or_file=os.path.join(STORAGE_DIR, id),
        as_attachment=True,
        download_name=name,
    )


@app.route("/")
def home():
    db = SQL(db_url)

    user_id = request.cookies.get("u_id")
    files = db.execute("SELECT id, name FROM files WHERE u_id=?", (user_id,))
    response = make_response(render_template("home.html", files=files))

    rows = db.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not user_id or not rows or isinstance(rows, int) or len(rows) != 1:
        user_id = str(uuid.uuid4())
        db.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        expire_date = datetime.now(timezone.utc) + timedelta(days=365 * 5)

        response.set_cookie(
            key="u_id",
            value=user_id,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=157680000,
            expires=expire_date,
        )
    return response
