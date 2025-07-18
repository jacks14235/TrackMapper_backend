# type: ignore
# app/routes.py
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory, abort, current_app
from werkzeug.utils import secure_filename
from .extensions import db
from .models import Map, User, Activity
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from typing import List, TYPE_CHECKING

bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'gpx'}

def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No selected file"), 400
    if not allowed_file(file.filename):
        return jsonify(error="File type not allowed"), 400

    raw = secure_filename(file.filename)
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    fname = f"{ts}_{raw}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    path = os.path.join(upload_folder, fname)
    file.save(path)

    ext = raw.rsplit('.', 1)[1].lower()
    rec = File(filename=fname, filetype=('gpx' if ext=='gpx' else 'image'))
    db.session.add(rec)
    db.session.commit()
    return jsonify(rec.to_dict()), 201

@bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    safe = secure_filename(filename)
    folder = current_app.config['UPLOAD_FOLDER']
    full = os.path.join(folder, safe)
    if not os.path.exists(full):
        abort(404)
    return send_from_directory(folder, safe, as_attachment=True)

@bp.route('/maps/nearest')
def maps_nearest():
    # please don't ask why I flipped lat/lon
    try:
        lat0 = float(request.args.get('lon'))
        lon0 = float(request.args.get('lat'))
    except (TypeError, ValueError):
        return abort(400, "Must provide numeric 'lat' and 'lon' query params")

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify(error="Invalid 'page' parameter, must be a positive integer"), 400

    per_page = 20  # Number of maps per page

    # build the query, ordering by our hybrid distance_to expression
    qry = (
        Map.query
           .options(joinedload(Map.user))
           .add_columns(Map.distance_to(lat0, lon0).label('distance_km'))
           .order_by('distance_km')
           .offset((page - 1) * per_page)
           .limit(per_page)
    )

    results = qry.all()
    return jsonify([
        {
          **m.to_dict(),
          'username': m.user.username,
          'distance': dist
        }
        for m, dist in results
    ])

@bp.route('/users/<int:user_id>/maps')
def user_maps(user_id):

    try:
        lat0 = float(request.args.get('lat'))
        lon0 = float(request.args.get('lon'))
    except (TypeError, ValueError):
        lat0 = None
        lon0 = None

    user = User.query.get(user_id)
    if lat0 is not None and lon0 is not None:
        all_maps = (
            Map.query
                .options(joinedload(Map.user))
                .filter(Map.user_id == user_id)
                .add_columns(Map.distance_to(lat0, lon0).label('distance_km'))
                .order_by('distance_km')
                .all()
        )
    else:
        all_maps = (
            Map.query
                .options(joinedload(Map.user))
                .filter(Map.user_id == user_id)
                .order_by(Map.uploaded_at.desc())
                .all()
        )

    return jsonify([
        {**m.to_dict(), 'username': m.user.username}
        for m in all_maps
    ])

class Coordinate:
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

class CoordPair:
    def __init__(self, map: Coordinate, real: Coordinate):
        self.map = map
        self.real = real


@bp.route('/maps/upload', methods=['POST'])
def create_map():

    user = User.query.get(1)  # TODO: replace with actual user ID from session or token
    # 1) pull out form fields + files
    title       = request.form.get('title')
    latitude    = request.form.get('latitude')
    longitude   = request.form.get('longitude')
    num_points  = request.form.get('num_points')
    points_raw  = request.form.get('points')      # expecting JSON text
    image_file  = request.files.get('image')      # the uploaded image

    # 2) validate
    missing = []
    for name, val in [
        ('title', title),
        ('latitude', latitude),
        ('longitude', longitude),
        ('num_points', num_points),
        ('points', points_raw),
        ('image', image_file),
    ]:
        if not val:
            missing.append(name)
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    try:
        # 3) parse and create the Map without file paths yet
        points = json.loads(points_raw)
        new_map = Map(
            title       = title,
            description = request.form.get('description'),
            user_id     = user.id,
            latitude    = float(latitude),
            longitude   = float(longitude),
            num_points  = int(num_points),
            image_path  = "",      # placeholder
        )
        db.session.add(new_map)
        db.session.flush()     # so new_map.id is populated

        # 4) build file names
        upload_dir     = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        # points JSON
        pts_fname      = f"points_{new_map.id}.json"
        pts_full_path  = os.path.join(upload_dir, pts_fname)
        with open(pts_full_path, 'w') as f:
            json.dump(points, f)

        img_fname      = f"image_{new_map.id}.jpg"
        img_full_path  = os.path.join(upload_dir, img_fname)
        image_file.save(img_full_path)

        # 5) update the Map record
        new_map.image_path  = img_fname

        # 6) final commit
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Error during map creation:", e)
        return jsonify(error=str(e)), 500

    return jsonify({**new_map.to_dict(), "username": user.username}), 201


@bp.route('/maps/<map_id>', methods=['DELETE'])
def delete_map(map_id):
    # 1) fetch or 404
    print("Deleting map with ID:", map_id)
    m = Map.query.get_or_404(map_id)
    print("Found map:", m)

    upload_dir = current_app.config['UPLOAD_FOLDER']
    img_fp = os.path.join(upload_dir, f'image_{m.id}.jpg')
    if os.path.exists(img_fp):
        os.remove(img_fp)
    points_fp = os.path.join(upload_dir, f'points_{m.id}.json')
    if os.path.exists(points_fp):
        os.remove(points_fp)

    # 4) delete DB record
    try:
        db.session.delete(m)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        abort(500, f"Failed to delete map: {e}")

    # 5) no content
    return '', 204

@bp.route('/activities/upload', methods=['POST'])
def create_activity():
    title        = request.form.get('title')
    description  = request.form.get('description')
    date         = request.form.get('date')
    user_id      = request.form.get('user_id')
    map_id       = request.form.get('map_id')
    gpx_file     = request.files.get('gpx')
    distance     = request.form.get('distance')
    elapsed_time = request.form.get('elapsed_time')

    print("Distance", distance)


    # 2) validate
    missing = []
    for name, val in [
        ('title', title),
        ('date', date),
        ('user_id', user_id),
        ('map_id', map_id),
        ('gpx', gpx_file),
        ('distance', distance),
        ('elapsed_time', elapsed_time)
    ]:
        if not val:
            missing.append(name)
    if missing:
        print("Missing fields:", missing)
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    try:
        # 3) parse and create the Activity
        new_activity = Activity(
            title=title,
            description=description,
            created_at=datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
            user_id=int(user_id),
            map_id=map_id,  # No longer converting to int since it's now a UUID string
            distance=float(distance),
            elapsed_time=float(elapsed_time)
        )
        db.session.add(new_activity)
        db.session.flush()

        # save the GPX file
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        gpx_fname = f"gpx_{new_activity.id}.gpx"
        gpx_full_path = os.path.join(upload_dir, gpx_fname)
        gpx_file.save(gpx_full_path)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Error during activity creation:", e)
        return jsonify(error=str(e)), 500

    return jsonify(new_activity.to_dict()), 201

@bp.route('/users/<int:user_id>/activities', methods=['GET'])
def user_activities(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify(error="User not found"), 404
    activities = user.activities.all()
    return jsonify([
        {
            'id': activity.id,
            'title': activity.title,
            'description': activity.description,
            'created_at': activity.created_at.isoformat(),
            'user_id': activity.user_id,
            'map_id': activity.map_id,
            'username': user.username,
            'distance': activity.distance,
            'elapsed_time': activity.elapsed_time
        }
        for activity in activities
    ])

# get most recent activities from a user's friend
@bp.route('/users/<int:user_id>/friends/activities', methods=['GET'])
def user_friends_activities(user_id):
    user = User.query.get_or_404(user_id)
    friend_ids = [f.id for f in user.friends] + [user.id]  # Include the user's own ID

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify(error="Invalid 'page' parameter, must be a positive integer"), 400

    per_page = 20  # Number of activities per page
    activities = (
        Activity.query
                .options(joinedload(Activity.user))
                .filter(Activity.user_id.in_(friend_ids))
                .order_by(desc(Activity.created_at))
                .offset((page - 1) * per_page)
                .limit(per_page)
    )

    return jsonify([
        {
            'id':           act.id,
            'title':        act.title,
            'description':  act.description,
            'created_at':   act.created_at.isoformat(),
            'map_id':       act.map_id,
            'user_id':      act.user_id,
            'username':     act.user.username,
            'distance':     act.distance,
            'elapsed_time': act.elapsed_time
        }
        for act in activities
    ])