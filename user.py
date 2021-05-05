from bottle import default_app, response, request, route
import json
import sqlite3

def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS, HEAD'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        if request.method != 'OPTIONS':
            # actual request; reply with the actual response
            return fn(*args, **kwargs)

    return _enable_cors

def connect():
    conn = sqlite3.connect('project.db')
    conn.row_factory = sqlite3.Row
    return conn

with connect() as db:
    db.execute("DROP TABLE IF EXISTS User")
    db.execute("""
               CREATE TABLE User (
                 id INTEGER PRIMARY KEY,
                 username TEXT,
                 password TEXT,
                 tid INTEGER,
                 FOREIGN KEY(tid) REFERENCES Theme(id)
               )
    """)

with connect() as db:
    db.execute("DROP TABLE IF EXISTS Theme")
    db.execute("""
               CREATE TABLE Theme (
                 id INTEGER PRIMARY KEY,
                 first TEXT,
                 second TEXT
               )
    """)

with connect() as db:
    db.execute("DROP TABLE IF EXISTS Favorites")
    db.execute("""
                CREATE TABLE Favorites (
                id INTEGER PRIMARY KEY,
                character TEXT,
                film TEXT,
                starship TEXT,
                vehicle TEXT,
                species TEXT,
                planet TEXT
                )
    """)

with connect() as db:
    db.execute("INSERT INTO Theme (first, second) VALUES (?, ?)",
                    ("black", "red"))

with connect() as db:
    db.execute("INSERT INTO Theme (first, second) VALUES (?, ?)",
                    ("blue", "green"))

@route('/', method=['HEAD', 'OPTIONS', 'GET'])
@enable_cors
def hello_world():
    return 'Hello from Bottle!'

class Theme:

    def __init__(self, id, first, second):
        self.id = id
        self.first = first
        self.second = second

    def jsonable(self):
        return {'id': self.id, 'first': self.first, 'second': self.second}

    @staticmethod
    def find(id):
        print('here')
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Theme WHERE id = ?", (id,))
            row = cursor.fetchone()

        if row is None:
            raise Exception(f'No such Theme with user: {id}')
        else:
            return Theme(row['id'], row['first'], row['second'])

    @route('/theme/<id>', method=['OPTIONS', 'GET'])
    @enable_cors
    def getThemeUser(id):
        print(id)
        try:
            theme = Theme.find(id)
        except Exception:
            response.status = 404
            return f"Theme: {id} not found"
        return theme.jsonable()

class User:

    def __init__(self, id, username, password, tid):
        self.id = id
        self.username = username
        self.password = password
        self.tid = tid

    def updateTheme(self):
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE User SET tid = ? WHERE id = ?",
                               (self.tid, self.id))
            conn.commit()

    def updatePassword(self):
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE User SET password = ? WHERE id = ?",
                               (self.password, self.id))
            conn.commit()

    def updateFromJSON(self, user_data):
        if 'tid' in user_data:
            self.tid = user_data['tid']
            self.updateTheme()
        elif 'password' in user_data:
                self.password = user_data['password']
                self.updatePassword()
        else:
            raise Exception(f"Invalid Input")


    def delete(self):
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM User WHERE id = ?", (self.id, ))


    def jsonable(self):
        return {'id': self.id, 'username': self.username, 'password': self.password, 'tid': self.tid}

    @staticmethod
    def createFromJSON(user_data):

        username = user_data['username']
        password = user_data['password']

        for char in username:
            if char==" ":
                raise Exception(f"Username cannot contain spaces")

        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM User WHERE username = ?", (username,))
            row = cursor.fetchone()

        if row is None:
            with connect() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO User (username, password, tid) VALUES (?, ?, ?)",
                                (username, password, None))
                conn.commit()
                userID = (cursor.lastrowid)
            with connect() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Favorites (id, character, film, starship, vehicle, species, planet) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (userID, None, None, None, None, None, None))
                conn.commit()
            return User.find(username)
        else:
            raise Exception(f"Username already exists")


    @staticmethod
    def find(string):
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM User WHERE username = ?", (string,))
            row = cursor.fetchone()

        if row is None:
            raise Exception(f'No such User with user: {string}')
        else:
            return User(row['id'], row['username'], row['password'], row['tid'])

    @staticmethod
    def getUserCount():
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM User")
            count = [row['id'] for row in cursor]
        return count

    @route('/user', method=['OPTIONS', 'GET'])
    @enable_cors
    def getUsers():
        users = User.getUserCount()
        response.content_type = 'application/json'
        return json.dumps(users)

    @route('/user/<string>', method=['OPTIONS', 'GET'])
    @enable_cors
    def getUser(string):
        try:
            user = User.find(string)
        except Exception as e:
            response.status = 404
            return "Error {0}".format(str(e.args[0])).encode("utf-8")
        return user.jsonable()

    @route('/user', method=['OPTIONS', 'POST'])
    @enable_cors
    def postUser():
        try:
            user = User.createFromJSON(request.json)
        except Exception:
            response.status = 400
            return f"Error"
        return user.jsonable()

    @route('/user/<string>', method=['OPTIONS', 'PUT'])
    @enable_cors
    def updateUser(string):
        try:
            user = User.find(string)
        except Exception:
            response.status = 404
            return f"User Does Not Exist"

        try:
            user.updateFromJSON(request.json)
        except Exception:
            response.status = 400
            return f"Invalid Input"
        return user.jsonable()

class Favorites:

    def __init__(self, id, character, film, starship, vehicle, species, planet):
        self.id = id
        self.character = character
        self.film = film
        self.starship = starship
        self.vehicle = vehicle
        self.species = species
        self.planet = planet

    def updateFavorites(self):
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Favorites SET character = ?, film = ?, starship = ?, vehicle = ?, species = ?, planet = ? WHERE id = ?",
                               (self.character, self.film, self.starship, self.vehicle, self.species, self.planet, self.id))
            conn.commit()

    def updateFromJSON(self, favorites_data):
        self.character = favorites_data['character']
        self.film = favorites_data['film']
        self.starship = favorites_data['starship']
        self.vehicle = favorites_data['vehicle']
        self.species = favorites_data['species']
        self.planet = favorites_data['planet']
        self.updateFavorites()

    def jsonable(self):
        return {'id': self.id, 'character': self.character, 'film': self.film, 'starship': self.starship, 'vehicle': self.vehicle, 'species': self.species, 'planet': self.planet}

    @staticmethod
    def find(id):
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Favorites WHERE id = ?", (id,))
            row = cursor.fetchone()

        if row is None:
            raise Exception(f"No such Favorites with id: {id}")
        else:
            return Favorites(row['id'], row['character'], row['film'], row['starship'], row['vehicle'], row['species'], row['planet'])

    @route('/favorites/<id>', method=['OPTIONS', 'GET'])
    @enable_cors
    def getFavorites(id):
        try:
            favorites = Favorites.find(id)
        except Exception:
            response.status = 404
            return f"Favorites with id: {id} not found"
        return favorites.jsonable()

    @route('/favorites/<id>', method=['OPTIONS', 'PUT'])
    @enable_cors
    def updateFavoritesTable(id):
        try:
            favorites = Favorites.find(id)
        except Exception:
            response.status = 404
            return f"Favorites with id: {id} not found"

        try:
            favorites.updateFromJSON(request.json)
        except Exception:
            response.status = 400
            return f"Invalid Input"
        return favorites.jsonable()


application = default_app()
