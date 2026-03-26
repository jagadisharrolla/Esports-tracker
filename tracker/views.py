from django.shortcuts import render, redirect
from .models import PlayerDB, players_collection, TournamentDB, tournaments_collection, UserDB, TeamDB
import json, os, re
from django.conf import settings

def get_session_user(request):
    return {
        'username': request.session.get('username'),
        'role': request.session.get('role'),
    }

def make_slug(name):
    # Fixed loop to handle infinite tournaments with same name
    base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = base_slug
    counter = 2
    while TournamentDB.get_by_slug(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

# ─── AUTH ──────────────────────────────────────────────────
def login_page(request):
    if request.session.get('username'):
        if request.session.get('role') == 'org':
            return redirect('org_dashboard')
        return redirect('home')
    return render(request, 'login.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = UserDB.verify(username, password)
        if user:
            request.session['username'] = user['username']
            request.session['role'] = user['role']
            if user['role'] == 'org':
                return redirect('org_dashboard')
            return redirect('home')
        return render(request, 'login.html', {
            'error': 'Invalid username or password',
            'tab': request.POST.get('tab', 'player')
        })
    return redirect('login_page')

def logout_view(request):
    request.session.flush()
    return redirect('login_page')

def register_org(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm = request.POST.get('confirm', '').strip()
        if password != confirm:
            return render(request, 'login.html', {'error': 'Passwords do not match', 'tab': 'org', 'show_register': True})
        if UserDB.exists(username):
            return render(request, 'login.html', {'error': 'Username already taken', 'tab': 'org', 'show_register': True})
        UserDB.create(username, password, 'org')
        request.session['username'] = username
        request.session['role'] = 'org'
        return redirect('org_dashboard')
    return redirect('login_page')

def register_player_account(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm = request.POST.get('confirm', '').strip()
        if password != confirm:
            return render(request, 'login.html', {'error': 'Passwords do not match', 'tab': 'player', 'show_register': True})
        if UserDB.exists(username):
            return render(request, 'login.html', {'error': 'Username already taken', 'tab': 'player', 'show_register': True})
        UserDB.create(username, password, 'player')
        PlayerDB.create(username=username)
        request.session['username'] = username
        request.session['role'] = 'player'
        return redirect('home')
    return redirect('login_page')

# ─── HOME ──────────────────────────────────────────────────
def home(request):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    tournaments = TournamentDB.get_all()
    for t in tournaments:
        t['_id'] = str(t['_id'])
        t['total_registered'] = TournamentDB.total_registered(t)
    live = [t for t in tournaments if t.get('status') == 'live']
    upcoming = [t for t in tournaments if t.get('status') == 'upcoming']
    completed = [t for t in tournaments if t.get('status') == 'completed']

    if user['role'] == 'player':
        username = user['username']
        player = PlayerDB.get_by_username(username)
        all_players = PlayerDB.get_all()
        for p in all_players:
            p['kd'] = PlayerDB.kd_ratio(p)
            p['wr'] = PlayerDB.win_rate(p)
            p['tm'] = PlayerDB.total_matches(p)
            p['kills'] = PlayerDB.total_kills(p)
            p['_id'] = str(p['_id'])
        ranked = sorted(all_players, key=lambda p: p['kd'], reverse=True)
        global_rank = next((i+1 for i, p in enumerate(ranked) if p['username'] == username), '-')

        player_data = None
        games_stats = []
        recent_matches = []
        my_tournaments = []

        if player:
            matches = player.get('matches', [])
            player_data = {
                'kd': PlayerDB.kd_ratio(player),
                'wr': PlayerDB.win_rate(player),
                'tm': PlayerDB.total_matches(player),
                'total_kills': PlayerDB.total_kills(player),
                'global_rank': global_rank,
                'game_count': len(set(m.get('game','') for m in matches if m.get('game'))),
            }

            game_icons = {
                'BGMI': ('🔫','rgba(255,150,0,0.3)','rgba(255,0,110,0.2)','Battle Royale'),
                'Call of Duty': ('💥','rgba(0,245,255,0.2)','rgba(123,47,255,0.2)','Team Deathmatch'),
                'Valorant': ('🎯','rgba(255,0,110,0.25)','rgba(123,47,255,0.2)','Tactical FPS'),
                'Free Fire': ('🔥','rgba(255,100,0,0.3)','rgba(255,200,0,0.2)','Battle Royale'),
                'CS2': ('💣','rgba(255,200,0,0.2)','rgba(255,100,0,0.15)','Tactical FPS'),
                'Fortnite': ('🏗️','rgba(0,245,255,0.2)','rgba(0,255,136,0.15)','Battle Royale'),
            }

            games_played = {}
            for m in matches:
                g = m.get('game','')
                if not g: continue
                if g not in games_played:
                    games_played[g] = {'kills':0,'deaths':0,'wins':0,'total':0}
                games_played[g]['kills'] += m.get('kills',0)
                games_played[g]['deaths'] += m.get('deaths',0)
                if m.get('result') == 'win': games_played[g]['wins'] += 1
                games_played[g]['total'] += 1

            reg_tournament_names = {}
            for t in tournaments:
                regs = [r['username'] for r in t.get('registrations', [])]
                if username in regs:
                    g = t.get('game','')
                    if g not in reg_tournament_names:
                        reg_tournament_names[g] = t.get('name','')

            upcoming_by_game = {}
            for t in upcoming:
                g = t.get('game','')
                if g and g not in upcoming_by_game:
                    upcoming_by_game[g] = t.get('name','')

            for game, stats in games_played.items():
                icon_data = game_icons.get(game, ('🎮','rgba(0,245,255,0.2)','rgba(123,47,255,0.2)','Competitive'))
                d = stats['deaths'] or 1
                kd = round(stats['kills'] / d, 2)
                wr = round((stats['wins'] / stats['total']) * 100, 1) if stats['total'] else 0
                t_for_game = [t for t in tournaments if t.get('game') == game]
                has_live = any(t.get('status') == 'live' for t in t_for_game)
                has_upcoming = any(t.get('status') == 'upcoming' for t in t_for_game)
                games_stats.append({
                    'game': game,
                    'icon': icon_data[0],
                    'color1': icon_data[1],
                    'color2': icon_data[2],
                    'mode': icon_data[3],
                    'kd': kd,
                    'wr': wr,
                    'kills': stats['kills'],
                    'has_live': has_live,
                    'has_upcoming': has_upcoming,
                    'tournament': reg_tournament_names.get(game,''),
                    'upcoming_name': upcoming_by_game.get(game,''),
                })

            recent_matches = []
            for m in reversed(matches[-5:]):
                m_copy = dict(m)
                d = m.get('deaths',0) or 1
                m_copy['kd'] = round(m.get('kills',0) / d, 2)
                recent_matches.append(m_copy)

        for t in tournaments:
            regs = [r['username'] for r in t.get('registrations', [])]
            if username in regs:
                my_tournaments.append(t)

        my_t_slugs = [t['slug'] for t in my_tournaments]
        open_tournaments = [t for t in upcoming if t.get('slug') not in my_t_slugs][:4]
        new_tournaments = [t for t in upcoming if t.get('slug') not in my_t_slugs][:2]

        return render(request, 'home.html', {
            'user': user,
            'player_data': player_data,
            'games_stats': games_stats,
            'recent_matches': recent_matches,
            'my_tournaments': my_tournaments,
            'open_tournaments': open_tournaments,
            'new_tournaments': new_tournaments,
            'leaderboard_mini': ranked[:5],
        })
    else:
        total_players = len(PlayerDB.get_all())
        return render(request, 'home.html', {
            'user': user,
            'live': live,
            'upcoming': upcoming,
            'completed': completed,
            'total_tournaments': len(tournaments),
            'total_players': total_players,
        })

# ─── DASHBOARD ─────────────────────────────────────────────
def dashboard(request):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    query = request.GET.get('q', '')
    players = list(players_collection.find({"username": {"$regex": query, "$options": "i"}})) if query else PlayerDB.get_all()
    for p in players:
        p['kd'] = PlayerDB.kd_ratio(p)
        p['wr'] = PlayerDB.win_rate(p)
        p['tm'] = PlayerDB.total_matches(p)
        p['_id'] = str(p['_id'])
    return render(request, 'dashboard.html', {'players': players, 'query': query, 'user': user})

def leaderboard(request):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    players = PlayerDB.get_all()
    for p in players:
        p['kd'] = PlayerDB.kd_ratio(p)
        p['wr'] = PlayerDB.win_rate(p)
        p['tm'] = PlayerDB.total_matches(p)
        p['kills'] = PlayerDB.total_kills(p)
        p['_id'] = str(p['_id'])
    ranked = sorted(players, key=lambda p: p['kd'], reverse=True)
    return render(request, 'leaderboard.html', {'players': ranked, 'user': user})

def player_profile(request, username):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    player = PlayerDB.get_by_username(username)
    if not player:
        return redirect('dashboard')
    
    trend = PlayerDB.get_performance_trend(player)
    
    player['kd'] = PlayerDB.kd_ratio(player)
    player['wr'] = PlayerDB.win_rate(player)
    player['tm'] = PlayerDB.total_matches(player)
    player['total_kills'] = PlayerDB.total_kills(player)
    player['total_deaths'] = PlayerDB.total_deaths(player)
    player['_id'] = str(player['_id'])
    matches = player.get('matches', [])
    filter_map = request.GET.get('map', '')
    filter_mode = request.GET.get('mode', '')
    filter_result = request.GET.get('result', '')
    filtered = matches
    if filter_map: filtered = [m for m in filtered if m.get('map','').lower() == filter_map.lower()]
    if filter_mode: filtered = [m for m in filtered if m.get('mode','').lower() == filter_mode.lower()]
    if filter_result: filtered = [m for m in filtered if m.get('result','').lower() == filter_result.lower()]
    recent = filtered[-10:]
    dates = [m['date'] for m in recent]
    kds = [round(m['kills'] / (m['deaths'] or 1), 2) for m in recent]
    kills_data = [m['kills'] for m in recent]
    deaths_data = [m['deaths'] for m in recent]
    map_counts = {}
    for m in matches:
        mp = m.get('map', 'Unknown')
        map_counts[mp] = map_counts.get(mp, 0) + 1
    sorted_maps = sorted(map_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    all_maps = sorted(set(m.get('map','') for m in matches if m.get('map')))
    all_modes = sorted(set(m.get('mode','') for m in matches if m.get('mode')))
    streak = 0
    streak_type = ''
    for m in reversed(matches):
        if streak == 0: streak_type = m.get('result',''); streak = 1
        elif m.get('result') == streak_type: streak += 1
        else: break
    best_match = max(matches, key=lambda m: m['kills'] - m['deaths']) if matches else None
    all_tournaments = TournamentDB.get_all()
    player_tournaments = []
    for t in all_tournaments:
        regs = [r['username'] for r in t.get('registrations', [])]
        if username in regs:
            t['_id'] = str(t['_id'])
            player_result = next((r for r in t.get('results', []) if r.get('username') == username), None)
            t['player_result'] = player_result
            player_tournaments.append(t)
    return render(request, 'player_profile.html', {
        'player': player, 'user': user, 'trend': trend,
        'recent_matches': recent,
        'all_matches': filtered,
        'chart_dates': json.dumps(dates),
        'chart_kds': json.dumps(kds),
        'kills_data': json.dumps(kills_data),
        'deaths_data': json.dumps(deaths_data),
        'map_labels': json.dumps([x[0] for x in sorted_maps]),
        'map_values': json.dumps([x[1] for x in sorted_maps]),
        'all_maps': all_maps, 'all_modes': all_modes,
        'filter_map': filter_map, 'filter_mode': filter_mode, 'filter_result': filter_result,
        'streak': streak, 'streak_type': streak_type,
        'best_match': best_match,
        'player_tournaments': player_tournaments,
    })

def add_player(request):
    if not request.session.get('username'):
        return redirect('login_page')
    if request.method == 'POST':
        username = request.POST.get('username')
        avatar = request.FILES.get('avatar')
        avatar_url = ""
        if avatar:
            media_path = os.path.join(settings.MEDIA_ROOT, 'avatars')
            os.makedirs(media_path, exist_ok=True)
            file_path = os.path.join(media_path, avatar.name)
            with open(file_path, 'wb+') as f:
                for chunk in avatar.chunks(): f.write(chunk)
            avatar_url = f"/media/avatars/{avatar.name}"
        PlayerDB.create(username=username, avatar_url=avatar_url)
        return redirect('dashboard')
    return render(request, 'add_player.html', {'user': get_session_user(request)})

def delete_player(request, username):
    if request.session.get('role') != 'org':
        return redirect('login_page')
    if request.method == 'POST':
        players_collection.delete_one({"username": username})
    return redirect('dashboard')

def add_match(request, username):
    if not request.session.get('username'):
        return redirect('login_page')
    player = PlayerDB.get_by_username(username)
    if request.method == 'POST':
        match = {
            'match_id': f"m{PlayerDB.total_matches(player)+1}",
            'game': request.POST.get('game'),
            'mode': request.POST.get('mode'),
            'map': request.POST.get('map'),
            'date': request.POST.get('date'),
            'kills': int(request.POST.get('kills')),
            'deaths': int(request.POST.get('deaths')),
            'assists': int(request.POST.get('assists')),
            'result': request.POST.get('result'),
            'weapon': request.POST.get('weapon', ''),
            'notes': request.POST.get('notes', ''),
        }
        PlayerDB.add_match(username, match)
        return redirect('player_profile', username=username)
    return render(request, 'add_match.html', {'player': player, 'user': get_session_user(request)})

def match_detail(request, username, match_id):
    if not request.session.get('username'):
        return redirect('login_page')
    player = PlayerDB.get_by_username(username)
    if not player: return redirect('dashboard')
    match = next((m for m in player.get('matches', []) if m.get('match_id') == match_id), None)
    if not match: return redirect('player_profile', username=username)
    kd = round(match['kills'] / (match['deaths'] or 1), 2)
    return render(request, 'match_detail.html', {
        'player': player, 'match': match, 'kd': kd,
        'user': get_session_user(request)
    })

def compare(request):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    all_players = PlayerDB.get_all()
    for p in all_players:
        p['kd'] = PlayerDB.kd_ratio(p)
        p['wr'] = PlayerDB.win_rate(p)
        p['tm'] = PlayerDB.total_matches(p)
        p['_id'] = str(p['_id'])
    p1_name = request.GET.get('p1', '')
    p2_name = request.GET.get('p2', '')
    p1 = next((p for p in all_players if p['username'] == p1_name), None)
    p2 = next((p for p in all_players if p['username'] == p2_name), None)
    return render(request, 'compare.html', {
        'all_players': all_players, 'p1': p1, 'p2': p2,
        'p1_name': p1_name, 'p2_name': p2_name, 'user': user
    })

def tournament_list(request):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    tournaments = TournamentDB.get_all()
    game_filter = request.GET.get('game', '')
    status_filter = request.GET.get('status', '')
    for t in tournaments:
        t['_id'] = str(t['_id'])
        t['total_registered'] = TournamentDB.total_registered(t)
    if game_filter:
        tournaments = [t for t in tournaments if t.get('game','').lower() == game_filter.lower()]
    if status_filter:
        tournaments = [t for t in tournaments if t.get('status','') == status_filter]
    games = list(set(t.get('game','') for t in TournamentDB.get_all() if t.get('game')))
    return render(request, 'tournament_list.html', {
        'tournaments': tournaments, 'user': user,
        'game_filter': game_filter, 'status_filter': status_filter, 'games': games,
    })

def tournament_create(request):
    if request.session.get('role') != 'org':
        return redirect('login_page')
    if request.method == 'POST':
        name = request.POST.get('name')
        data = {
            'name': name,
            'slug': make_slug(name),
            'game': request.POST.get('game'),
            'mode': request.POST.get('mode'),
            'prize': request.POST.get('prize'),
            'max_players': int(request.POST.get('max_players', 32)),
            'start_date': request.POST.get('start_date'),
            'end_date': request.POST.get('end_date'),
            'description': request.POST.get('description', ''),
            'rules': request.POST.get('rules', ''),
            'organizer': request.session.get('username'),
            'location': request.POST.get('location', 'Online'),
            'format': request.POST.get('format', 'Battle Royale'),
        }
        TournamentDB.create(data)
        return redirect('tournament_list')
    return render(request, 'tournament_create.html', {'user': get_session_user(request)})

def tournament_detail(request, slug):
    if not request.session.get('username'):
        return redirect('login_page')
    user = get_session_user(request)
    tournament = TournamentDB.get_by_slug(slug)
    if not tournament: return redirect('tournament_list')
    tournament['_id'] = str(tournament['_id'])
    tournament['total_registered'] = TournamentDB.total_registered(tournament)
    enriched_regs = []
    for reg in tournament.get('registrations', []):
        player = PlayerDB.get_by_username(reg['username'])
        if player:
            result = next((r for r in tournament.get('results', []) if r.get('username') == reg['username']), None)
            enriched_regs.append({
                'username': reg['username'],
                'avatar': player.get('avatar',''),
                'registered_at': reg.get('registered_at',''),
                'status': reg.get('status','approved'),
                'kd': PlayerDB.kd_ratio(player),
                'wr': PlayerDB.win_rate(player),
                'tm': PlayerDB.total_matches(player),
                'kills': PlayerDB.total_kills(player),
                'result': result,
            })
    enriched_regs.sort(key=lambda x: x['kills'], reverse=True)
    all_players = PlayerDB.get_all()
    reg_names = [r['username'] for r in tournament.get('registrations', [])]
    available_players = [p for p in all_players if p['username'] not in reg_names]
    is_registered = request.session.get('username') in reg_names
    return render(request, 'tournament_detail.html', {
        'tournament': tournament, 'user': user,
        'registrations': enriched_regs,
        'available_players': available_players,
        'results': tournament.get('results', []),
        'is_registered': is_registered,
    })

def tournament_register(request, slug):
    if not request.session.get('username'):
        return redirect('login_page')
    if request.method == 'POST':
        if request.session.get('role') == 'org':
            username = request.POST.get('username')
        else:
            username = request.session.get('username')
        TournamentDB.register_player(slug, username)
    return redirect('tournament_detail', slug=slug)

def tournament_add_result(request, slug):
    if request.session.get('role') != 'org':
        return redirect('login_page')
    if request.method == 'POST':
        result = {
            'username': request.POST.get('username'),
            'kills': int(request.POST.get('kills', 0)),
            'deaths': int(request.POST.get('deaths', 0)),
            'assists': int(request.POST.get('assists', 0)),
            'rank': int(request.POST.get('rank', 0)),
            'result': request.POST.get('result', 'loss'),
            'date': request.POST.get('date', ''),
        }
        TournamentDB.add_result(slug, result)
    return redirect('tournament_detail', slug=slug)

def tournament_update_status(request, slug):
    if request.session.get('role') != 'org':
        return redirect('login_page')
    if request.method == 'POST':
        TournamentDB.update_status(slug, request.POST.get('status'))
    return redirect('tournament_detail', slug=slug)

def org_dashboard(request):
    if request.session.get('role') != 'org':
        return redirect('login_page')
    user = get_session_user(request)
    tournaments = TournamentDB.get_all()
    for t in tournaments:
        t['_id'] = str(t['_id'])
        t['total_registered'] = TournamentDB.total_registered(t)
    total_players = len(PlayerDB.get_all())
    live = [t for t in tournaments if t.get('status') == 'live']
    upcoming = [t for t in tournaments if t.get('status') == 'upcoming']
    completed = [t for t in tournaments if t.get('status') == 'completed']
    return render(request, 'org_dashboard.html', {
        'tournaments': tournaments, 'user': user,
        'total_players': total_players,
        'live': live, 'upcoming': upcoming, 'completed': completed,
        'total_tournaments': len(tournaments),
    })

# ─── TEAMS & SQUADS ────────────────────────────────────────
def teams_hub(request):
    if not request.session.get('username'): 
        return redirect('login_page')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        tag = request.POST.get('tag')
        TeamDB.create(name, tag, request.session.get('username'))
        return redirect('teams_hub')
        
    teams = TeamDB.get_all()
    for t in teams:
        stats = TeamDB.get_team_stats(t['name'])
        t['kd'] = stats['kd'] if stats else 0
        t['total_kills'] = stats['total_kills'] if stats else 0
        
    sorted_teams = sorted(teams, key=lambda x: x['kd'], reverse=True)
        
    return render(request, 'teams.html', {
        'teams': sorted_teams, 
        'user': get_session_user(request)
    })

def generate_bracket_view(request, slug):
    if request.session.get('role') == 'org':
        TournamentDB.generate_bracket(slug)
    return redirect('tournament_detail', slug=slug)