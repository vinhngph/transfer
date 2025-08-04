from flask import Flask, request, abort, jsonify, send_from_directory, render_template, make_response
from werkzeug.datastructures.file_storage import FileStorage
import uuid
import os
from utils.sql import SQL

storage_dir = "storage"
db_url = "database.db"

app = Flask(__name__)


@app.route("/file", methods=["GET", "POST"])
def file():
    if request.method == "GET":
        id: str = request.args["id"]

        try:
            uuid.UUID(id)
        except ValueError:
            return jsonify({"msg": "invalid id"}), 400

        db = SQL(db_url)
        file_data = db.execute(
            "SELECT id, name, u_id FROM files WHERE id=?", (id,))

        if not file_data or isinstance(file_data, int):
            return jsonify({"msg": "file not found"}), 404

        id: str = file_data[0]["id"]
        name: str = file_data[0]["name"]

        return send_from_directory(storage_dir, id, as_attachment=False, download_name=name)

    elif request.method == "POST":
        user_id = request.cookies.get("user_id")
        if not user_id:
            return jsonify({"msg": "missing user_id"}), 400

        file: FileStorage = request.files["f"]
        if not file:
            return jsonify({"msg": "invalid file"}), 400

        file_id = str(uuid.uuid4())
        file_name = file.filename

        try:
            db = SQL(db_url)
            db.execute("INSERT INTO files (id, name, u_id) VALUES (?, ?, ?)",
                       (file_id, file_name, user_id))
            file.save(os.path.join("storage", file_id))
        except Exception as e:
            return jsonify({"msg": f"saving failed {e}"}), 500

        return jsonify({"id": file_id, "name": file_name}), 201
    else:
        abort(404)


@app.route("/")
def home():
    db = SQL(db_url)

    user_id = request.cookies.get("user_id")
    files = db.execute("SELECT id, name FROM files WHERE u_id=?", (user_id,))
    response = make_response(render_template("home.html", files=files))

    rows = db.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not user_id or not rows or isinstance(rows, int) or len(rows) != 1:
        user_id = str(uuid.uuid4())
        db.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        response.set_cookie(
            "user_id",
            user_id,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=3600
        )
    return response
