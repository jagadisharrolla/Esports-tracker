import pymongo
from datetime import datetime

MONGO_CLIENT = pymongo.MongoClient("mongodb://localhost:27017/")
db = MONGO_CLIENT["esports_tracker"]
players_collection = db["players"]
tournaments_collection = db["tournaments"]
users_collection = db["users"]
teams_collection = db["teams"]

class PlayerDB:
    @staticmethod
    def create(username, avatar_url=""):
        players_collection.insert_one({"username": username, "avatar": avatar_url, "matches": []})

    @staticmethod
    def get_all():
        return list(players_collection.find())

    @staticmethod
    def get_by_username(username):
        return players_collection.find_one({"username": username})

    @staticmethod
    def add_match(username, match):
        players_collection.update_one({"username": username}, {"$push": {"matches": match}})

    @staticmethod
    def kd_ratio(player):
        matches = player.get("matches", [])
        if not matches: return 0
        kills = sum(m["kills"] for m in matches)
        deaths = sum(m["deaths"] for m in matches) or 1
        return round(kills / deaths, 2)

    @staticmethod
    def win_rate(player):
        matches = player.get("matches", [])
        if not matches: return 0
        wins = sum(1 for m in matches if m["result"] == "win")
        return round((wins / len(matches)) * 100, 1)

    @staticmethod
    def total_matches(player):
        return len(player.get("matches", []))

    @staticmethod
    def total_kills(player):
        return sum(m.get("kills", 0) for m in player.get("matches", []))

    @staticmethod
    def total_deaths(player):
        return sum(m.get("deaths", 0) for m in player.get("matches", []))
        
    @staticmethod
    def get_performance_trend(player):
        matches = player.get("matches", [])
        if len(matches) < 3: return "CALIBRATING ⚙️"
        recent = matches[-5:]
        recent_kds = [round(m.get("kills", 0) / (m.get("deaths", 0) or 1), 2) for m in recent]
        avg_recent_kd = sum(recent_kds) / len(recent_kds)
        overall_kd = PlayerDB.kd_ratio(player)
        if avg_recent_kd > overall_kd + 0.5: return "ON FIRE 🔥"
        elif avg_recent_kd < overall_kd - 0.5: return "SLUMPING 📉"
        return "STABLE ⚖️"

class TeamDB:
    @staticmethod
    def create(name, tag, owner_username, logo_url=""):
        teams_collection.insert_one({
            "name": name, "tag": tag.upper()[:4], "owner": owner_username,
            "logo": logo_url, "members": [owner_username], "created_at": datetime.now().strftime("%Y-%m-%d")
        })

    @staticmethod
    def get_all(): return list(teams_collection.find())

    @staticmethod
    def get_by_name(name): return teams_collection.find_one({"name": name})

    @staticmethod
    def add_member(team_name, username):
        teams_collection.update_one({"name": team_name}, {"$addToSet": {"members": username}})

    @staticmethod
    def get_team_stats(team_name):
        team = TeamDB.get_by_name(team_name)
        if not team: return None
        total_kills = total_deaths = 0
        for member in team.get("members", []):
            p = PlayerDB.get_by_username(member)
            if p:
                total_kills += PlayerDB.total_kills(p)
                total_deaths += PlayerDB.total_deaths(p)
        kd = round(total_kills / (total_deaths or 1), 2)
        return {"kd": kd, "total_kills": total_kills}

class TournamentDB:
    @staticmethod
    def create(data):
        data.update({"created_at": datetime.now().strftime("%Y-%m-%d"), "registrations": [], "results": [], "bracket": {}, "status": "upcoming"})
        tournaments_collection.insert_one(data)

    @staticmethod
    def get_all(): return list(tournaments_collection.find())

    @staticmethod
    def get_by_slug(slug): return tournaments_collection.find_one({"slug": slug})

    @staticmethod
    def register_player(slug, username):
        t = TournamentDB.get_by_slug(slug)
        if not t or username in [r["username"] for r in t.get("registrations", [])]: return False
        tournaments_collection.update_one({"slug": slug}, {"$push": {"registrations": {"username": username, "registered_at": datetime.now().strftime("%Y-%m-%d"), "status": "approved"}}})
        return True

    @staticmethod
    def add_result(slug, result): tournaments_collection.update_one({"slug": slug}, {"$push": {"results": result}})

    @staticmethod
    def update_status(slug, status): tournaments_collection.update_one({"slug": slug}, {"$set": {"status": status}})

    @staticmethod
    def total_registered(tournament):
        if not tournament: return 0
        return len(tournament.get("registrations", []))

    @staticmethod
    def generate_bracket(slug):
        import random
        t = TournamentDB.get_by_slug(slug)
        if not t or not t.get("registrations"): return False
        players = [r["username"] for r in t["registrations"]]
        random.shuffle(players)
        round_1 = []
        for i in range(0, len(players), 2):
            p1 = players[i]
            p2 = players[i+1] if i+1 < len(players) else None
            round_1.append({"p1": p1, "p2": p2, "winner": p1 if not p2 else None})
        tournaments_collection.update_one({"slug": slug}, {"$set": {"bracket": {"round_1": round_1}, "status": "live"}})
        return True

class UserDB:
    @staticmethod
    def create(username, password, role):
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        users_collection.insert_one({"username": username, "password": hashed, "role": role, "created_at": datetime.now().strftime("%Y-%m-%d")})

    @staticmethod
    def get_by_username(username): return users_collection.find_one({"username": username})

    @staticmethod
    def verify(username, password):
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        return users_collection.find_one({"username": username, "password": hashed})

    @staticmethod
    def exists(username): return users_collection.find_one({"username": username}) is not None