from app.models import db, User, Map, Activity, friend
from faker import Faker
import random
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
import os

fake = Faker()
Faker.seed(777)

NUM_USERS = 10
MAPS_PER_USER = 3
ACTIVITIES_PER_USER = 4
MAX_FRIENDS_PER_USER = 3

def create_users():
    users = []
    for _ in range(NUM_USERS):
        user = User(
            firstname=fake.first_name(),  # type: ignore
            lastname=fake.last_name(),  # type: ignore
            username=fake.unique.user_name(),  # type: ignore
            email=fake.unique.email()  # type: ignore
        )
        db.session.add(user)
        users.append(user)
    db.session.commit()
    return users

def create_friendships(users):
    for user in users:
        possible_friends = [u for u in users if u != user]
        friends = random.sample(possible_friends, k=min(MAX_FRIENDS_PER_USER, len(possible_friends)))
        for friend in friends:
            if friend not in user.friends:
                user.friends.append(friend)
    db.session.commit()

def create_maps(users):
    all_maps = []
    for user in users:
        for _ in range(MAPS_PER_USER):
            lon = fake.latitude()
            lat = fake.longitude()
            map = Map(
                title=fake.sentence(nb_words=3),  # type: ignore
                description=fake.text(max_nb_chars=100),  # type: ignore
                image_path="",  # Will be set after we have the UUID  # type: ignore
                latitude=lat,  # type: ignore
                longitude=lon,  # type: ignore
                num_points=random.randint(50, 500),  # type: ignore
                user=user  # type: ignore
            )
            db.session.add(map)
            db.session.flush()  # Ensure the map object gets a UUID
            
            # Now set the image_path using the UUID
            map.image_path = f"image_{map.id}.jpg"
            
            all_maps.append(map)
            file_number = random.randint(1, 3)
            image_file = f'app/uploads_old/image_{file_number}.jpg'
            points_files = [f'app/uploads_old/points_{file_number}.json']
            new_image_path = os.path.join('app', 'uploads', f'image_{map.id}.jpg')
            if not os.path.exists(new_image_path):
                with open(image_file, 'rb') as fsrc:
                    with open(new_image_path, 'wb') as fdst:
                        fdst.write(fsrc.read())
            points_file = random.choice(points_files)
            new_points_file_path = os.path.join('app', 'uploads', f'points_{map.id}.json')
            if not os.path.exists(new_points_file_path):
                with open(points_file, 'rb') as fsrc:
                    with open(new_points_file_path, 'wb') as fdst:
                        fdst.write(fsrc.read())
    db.session.commit()
    return all_maps

gpx_files = [f'app/uploads_old/gpx_{i}.gpx' for i in range(1,4)]
def create_activities(users, maps_by_user):
    for user in users:
        maps = maps_by_user[user.id]
        for _ in range(ACTIVITIES_PER_USER):
            # choose time in the last 30 days
            created = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
            activity = Activity(
                title=fake.sentence(nb_words=3),  # type: ignore
                description=fake.text(max_nb_chars=100),  # type: ignore
                user=user,  # type: ignore
                map_id=random.choice(maps).id if maps and random.random() < 0.7 else None,  # 70% chance to attach to a map  # type: ignore
                created_at=created,  # type: ignore
                distance=random.random() * 20000, # random distance in meters  # type: ignore
                elapsed_time=random.randint(3600, 7200),  # random duration between 1 and 2 hours  # type: ignore
            )
            db.session.add(activity)
            db.session.flush()  # Ensure the activity object gets an ID
            
            file = random.choice(gpx_files)
            # copy the file and rename it based on the activity ID
            new_file_path = os.path.join('app', 'uploads', f'gpx_{activity.id}.gpx')
            if not os.path.exists(new_file_path):
                with open(file, 'rb') as fsrc:
                    with open(new_file_path, 'wb') as fdst:
                        fdst.write(fsrc.read())
            
            
    db.session.commit()

def run():
    print("Creating users...")
    users = create_users()

    print("Creating friendships...")
    create_friendships(users)

    print("Creating maps...")
    all_maps = create_maps(users)
    maps_by_user = {}
    for map in all_maps:
        maps_by_user.setdefault(map.user_id, []).append(map)

    print("Creating activities...")
    create_activities(users, maps_by_user)

    print("✅ Done seeding the database.")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        try:
            db.drop_all()
            db.create_all()
            run()
        except IntegrityError as e:
            db.session.rollback()
            print("❌ Integrity Error:", e)
