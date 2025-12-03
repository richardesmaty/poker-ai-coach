"""
Flask Backend API for Poker Game
This is your NEW backend/app.py file - replaces the Streamlit version

KEY DIFFERENCES FROM STREAMLIT:
1. Uses Flask instead of Streamlit
2. Creates REST API endpoints instead of web interface
3. Your React frontend will call these endpoints
4. Can be deployed to Render/Railway/etc.
"""




# ============================================
# IMPORTS
# ============================================
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from poker_engine import PokerGame
from poker_coach import get_poker_advice
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if exists)
load_dotenv()


# ============================================
# CREATE FLASK APP
# ============================================
app = Flask(__name__)

# IMPORTANT: Set secret key for sessions
# In production, this comes from environment variable
# In development, uses fallback
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Enable CORS so your React frontend can call this API
# This allows requests from your Netlify frontend to this backend
CORS(app)
@app.route("/")
def home():
    return jsonify({"status": "Poker AI Coach Backend is Running!"})
# ============================================
# STORE ACTIVE GAMES
# ============================================
# In-memory storage (in production, use Redis or database)
# Key = game_id, Value = PokerGame instance
active_games = {}

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_position_name(game, player):
    """Determine player position (UTG, MP, CO, BTN, SB, BB)"""
    state = game.state
    sb_seat, bb_seat = game.blind_seats()
    
    if player.seat == state.button_seat:
        return "BTN"
    elif player.seat == sb_seat:
        return "SB"
    elif player.seat == bb_seat:
        return "BB"
    return "MP"


def serialize_game_state(game):
    """
    Convert game state to JSON-friendly format
    This is sent to the React frontend
    """
    state = game.state
    hero = game.hero
    sb_seat, bb_seat = game.blind_seats()
    
    # Build player data for each player at the table
    players_data = []
    for p in sorted(state.players, key=lambda x: x.seat):
        players_data.append({
            'id': p.id,
            'name': p.name,
            'seat': p.seat,
            'stack': p.stack,
            'is_human': p.is_human,
            'in_hand': p.in_hand,
            'has_folded': p.has_folded,
            'contribution_this_round': p.contribution_this_round,
            'total_contribution': p.total_contribution,
            # Only show hole cards if it's the human player or at showdown
            'hole_cards': p.hole_cards if (p.is_human or state.betting_round == "finished") else [],
            'position': get_position_name(game, p),
            'is_button': p.seat == state.button_seat,
            'is_sb': p.seat == sb_seat,
            'is_bb': p.seat == bb_seat
        })
    
    # Return complete game state as dictionary
    return {
        'pot': state.pot,
        'community_cards': state.community_cards,
        'betting_round': state.betting_round,
        'current_bet': state.current_bet,
        'button_seat': state.button_seat,
        'sb_seat': sb_seat,
        'bb_seat': bb_seat,
        'players': players_data,
        'hero': {
            'seat': hero.seat,
            'stack': hero.stack,
            'hole_cards': hero.hole_cards,
            'in_hand': hero.in_hand,
            'has_folded': hero.has_folded,
            'position': get_position_name(game, hero)
        },
        'last_event': game.last_event,
        'last_winner': game.last_winner,
        'total_chips': game.total_chips()
    }


# ============================================
# API ENDPOINTS (Routes)
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint - test if backend is running
    URL: https://your-backend.com/api/health
    Returns: {"status": "healthy", "active_games": 0, "timestamp": "..."}
    """
    return jsonify({
        'status': 'healthy',
        'active_games': len(active_games),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/game/new', methods=['POST'])
def create_new_game():
    """
    Create a new poker game
    React calls this when user first loads the page
    
    REQUEST: POST /api/game/new
    RESPONSE: {
        "game_id": "uuid-string",
        "state": { ...game state... }
    }
    """
    # Generate unique game ID
    game_id = str(uuid.uuid4())
    
    # Create player names (1 human + 7 bots)
    names = [
        "HUMAN",
        "Reckless Rafa",
        "Gambler Grace",
        "LAG Lucy",
        "Crusher Carl",
        "Balanced Ben",
        "Nit Neil",
        "Station Sam",
    ]
    
    # Create new game instance
    game = PokerGame(player_names=names, starting_stack=1000)
    game.start_new_hand()
    
    # Store game in memory
    active_games[game_id] = game
    
    # Return game ID and initial state to frontend
    return jsonify({
        'game_id': game_id,
        'state': serialize_game_state(game)
    })


@app.route('/api/game/<game_id>/state', methods=['GET'])
def get_game_state(game_id):
    """
    Get current game state
    React calls this to refresh the display
    
    REQUEST: GET /api/game/abc-123/state
    RESPONSE: { ...game state... }
    """
    # Check if game exists
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = active_games[game_id]
    return jsonify(serialize_game_state(game))


@app.route('/api/game/<game_id>/action', methods=['POST'])
def player_action(game_id):
    """
    Handle player action (fold, check/call, bet/raise)
    React calls this when user clicks a button
    
    REQUEST: POST /api/game/abc-123/action
    BODY: {
        "action": "fold" | "check_call" | "bet_raise",
        "amount": 100  (optional, for bet/raise)
    }
    RESPONSE: {
        "success": true,
        "state": { ...updated game state... }
    }
    """
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = active_games[game_id]
    data = request.json
    
    # Get action details from request
    action = data.get('action')  # 'fold', 'check_call', 'bet_raise'
    amount = data.get('amount', None)
    
    # Process the action using your poker engine
    game.run_street_with_human_choice(action, amount)
    
    # Return updated state
    return jsonify({
        'success': True,
        'state': serialize_game_state(game)
    })


@app.route('/api/game/<game_id>/new-hand', methods=['POST'])
def new_hand(game_id):
    """
    Start a new hand
    React calls this when user clicks "New Hand" button
    
    REQUEST: POST /api/game/abc-123/new-hand
    RESPONSE: {
        "success": true,
        "state": { ...new hand state... }
    }
    """
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = active_games[game_id]
    game.start_new_hand()
    
    return jsonify({
        'success': True,
        'state': serialize_game_state(game)
    })


@app.route('/api/game/<game_id>/coach', methods=['GET'])
def get_coach_advice(game_id):
    """
    Get AI coach advice for current situation
    React calls this when user clicks "Show Advice"
    
    REQUEST: GET /api/game/abc-123/coach
    RESPONSE: {
        "recommendation": "raise",
        "reasoning": "Strong hand...",
        "pot_odds": 0.25,
        "equity_estimate": 0.68,
        ...
    }
    """
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = active_games[game_id]
    hero = game.hero
    state = game.state
    
    # Can't give advice if hand is over or player folded
    if hero.has_folded or not hero.in_hand or state.betting_round == "finished":
        return jsonify({'advice': None, 'message': 'No advice available'})
    
    # Get player position and count opponents
    hero_position = get_position_name(game, hero)
    num_opponents = len([p for p in state.players if p.in_hand and not p.has_folded and not p.is_human])
    
    # Call your AI coach module
    advice = get_poker_advice(
        hero_hand=hero.hole_cards,
        community_cards=state.community_cards,
        pot=state.pot,
        current_bet=state.current_bet,
        hero_contribution=hero.contribution_this_round,
        hero_stack=hero.stack,
        position=hero_position,
        street=state.betting_round,
        num_opponents=num_opponents
    )
    
    # Return advice as JSON
    return jsonify({
        'recommendation': advice.recommendation,
        'reasoning': advice.reasoning,
        'pot_odds': advice.pot_odds,
        'equity_estimate': advice.equity_estimate,
        'hand_strength': advice.hand_strength,
        'outs': advice.outs,
        'confidence': advice.confidence,
        'alternative': advice.alternative
    })


@app.route('/api/game/<game_id>/add-chips', methods=['POST'])
def add_chips(game_id):
    """
    Add chips to hero's stack (buy-in)
    React calls this when player runs out of chips
    
    REQUEST: POST /api/game/abc-123/add-chips
    BODY: {"amount": 1000}
    RESPONSE: {
        "success": true,
        "new_stack": 1000
    }
    """
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = active_games[game_id]
    data = request.json
    amount = data.get('amount', 1000)
    
    # Add chips to hero's stack
    game.hero.stack += amount
    
    return jsonify({
        'success': True,
        'new_stack': game.hero.stack
    })


# ============================================
# RUN THE APP
# ============================================

if __name__ == '__main__':
    # Get port from environment variable (for deployment)
    # Default to 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    
    # Run Flask server
    # host='0.0.0.0' allows external connections (needed for deployment)
    # debug=False for production (set to True for development)
    app.run(host='0.0.0.0', port=port, debug=False)


"""
============================================
HOW TO USE THIS FILE:
============================================

1. REPLACE your current backend/app.py with THIS ENTIRE FILE

2. Make sure you have these files in backend/:
   - app.py (this file)
   - poker_engine.py (your existing file)
   - poker_coach.py (your existing file)
   - requirements.txt (updated with Flask, Flask-CORS, gunicorn)

3. Test locally:
   cd backend
   python app.py
   
   Then visit: http://localhost:5000/api/health
   Should see: {"status": "healthy", ...}

4. Deploy to Render/Railway:
   - Push to GitHub
   - Connect repo to Render/Railway
   - They will automatically detect Python and run this file

============================================
WHAT CHANGED FROM STREAMLIT VERSION:
============================================

OLD (Streamlit):
- Used st.button(), st.write(), etc.
- Created visual interface directly
- Ran as a standalone web app
- Not API-based

NEW (Flask):
- Creates API endpoints (routes)
- Returns JSON data (no visual interface)
- React frontend makes HTTP requests to these endpoints
- Standard REST API architecture

============================================
API ENDPOINT SUMMARY:
============================================

GET  /api/health              → Check if backend is alive
POST /api/game/new            → Create new game
GET  /api/game/{id}/state     → Get current game state
POST /api/game/{id}/action    → Player makes action (fold/call/raise)
POST /api/game/{id}/new-hand  → Start new hand
GET  /api/game/{id}/coach     → Get AI coaching advice
POST /api/game/{id}/add-chips → Add chips to player stack

Your React frontend calls these endpoints to interact with the game!
"""



