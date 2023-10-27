from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


board = [["" for _ in range(3)] for _ in range(3)]
current_player = "X"

@app.route("/")
def index():
    return render_template("game.html", board=board, current_player=current_player)

@app.route("/make_move", methods=["POST"])
def make_move():
    global current_player
    data = request.get_json()
    
    try:
        row = int(data["row"])
        col = int(data["col"])
        
        if board[row][col] == "":
            board[row][col] = current_player
            current_player = "O" if current_player == "X" else "X"
            winner = check_winner()
            return jsonify({"board": board, "winner": winner})
        else:
            return jsonify({"error": "Invalid move"}), 400
    except (KeyError, ValueError, IndexError):
        return jsonify({"error": "Invalid input"}), 400


@app.route("/reset_game", methods=["POST"])
def reset_game():
    global board, current_player
    board = [["" for _ in range(3)] for _ in range(3)]
    current_player = "X"
    return jsonify({"board": board})

def check_winner():
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] and board[i][0] != "":
            return board[i][0]
        if board[0][i] == board[1][i] == board[2][i] and board[0][i] != "":
            return board[0][i]
    if board[0][0] == board[1][1] == board[2][2] and board[0][0] != "":
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] and board[0][2] != "":
        return board[0][2]
    return ""

if __name__ == "__main__":
    app.run(debug=True)
