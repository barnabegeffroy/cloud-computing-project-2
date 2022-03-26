from crypt import methods
import datetime
import google.oauth2.id_token
from flask import Flask, render_template, request, redirect, url_for
from google.auth.transport import requests
from google.cloud import datastore


app = Flask(__name__)
datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


def createUser(claims):
    entity_key = datastore_client.key('User', claims['email'])
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'name': claims['name'],
        'boards': []
    })
    datastore_client.put(entity)


def getUser(claims):
    entity_key = datastore_client.key('User', claims['email'])
    entity = datastore_client.get(entity_key)
    if not entity:
        createUser(claims)
        entity = datastore_client.get(entity_key)
    return entity


def getUserByEmail(email):
    entity_key = datastore_client.key('User', email)
    entity = datastore_client.get(entity_key)
    return entity


@app.route('/', methods=['GET'])
def root():
    id_token = request.cookies.get("token")
    claims = None
    user_data = None
    message = request.args.get('message')
    status = request.args.get('status')
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_data = getUser(claims)
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html')
    return render_template('index.html', user_data=user_data, message=message, status=status)


@app.route('/login')
def login():
    id_token = request.cookies.get("token")
    if id_token:
        return redirect(url_for('.root', message="You are already logged in", status="success"))
    else:
        return render_template('login.html')


@app.route('/my_account')
def myAccount():
    id_token = request.cookies.get("token")
    claims = None
    user_data = None
    message = None
    status = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_data = getUser(claims)
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html', message="You can't access this page without being logged in", status="error")

    return render_template('my_account.html', user_data=user_data, message=message, status=status)


def addBoardToUser(email, id, name):
    entity_key = datastore_client.key('User', email)
    entity = datastore_client.get(key=entity_key)
    board_info = datastore.Entity()
    board_info.update({
        'id': id,
        'name': name
    })
    new_board_list = entity['boards']
    new_board_list.append(board_info)
    entity.update({
        'boards': new_board_list
    })
    datastore_client.put(entity)


def CreateBoard(name, email):
    entity_key = datastore_client.key('Board')
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'name': name,
        'creator': email,
        'tasks': [],
        'users': [email]
    })
    datastore_client.put(entity)
    addBoardToUser(email, entity.key.id, name)


@app.route('/put_board', methods=['POST'])
def putboard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            CreateBoard(request.form['name'], claims['email'])
            message = "Your board has been created !"
            status = "success"
        except ValueError as exc:
            message = str(exc)
            status = "error"

    return redirect(url_for('.root', message=message, status=status))


def getBoardById(id):
    entity_key = datastore_client.key('Board', id)
    entity = datastore_client.get(entity_key)
    return entity


@app.route('/board/<int:id>', methods=['GET'])
def board(id):
    id_token = request.cookies.get("token")
    claims = None
    user_data = None
    board = None
    message = request.args.get('message')
    status = request.args.get('status')
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_data = getUser(claims)
            board = getBoardById(id)
            if board:
                if claims['email'] not in board['users']:
                    return redirect(url_for('.root', message="You haven't the right to access this board", status="error"))
            else:
                return redirect(url_for('.root', message="This board does not exist", status="error"))
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html', message="You can't access this page without being logged in", status="error")

    return render_template('board.html', user_data=user_data, board=board, message=message, status=status)


def addUserInBoard(board, email):
    user_list = board['users']
    user_list.append(email)
    board.update({
        'users': user_list
    })
    datastore_client.put(board)
    addBoardToUser(email, board.key.id, board['name'])


@app.route('/put_user_in_board', methods=['POST'])
def putUserInBoard():
    id = int(request.form['board-id'])
    email = request.form['email']
    user_entity = getUserByEmail(email)
    board = datastore_client.get(key=datastore_client.key('Board', id))
    if email in board['users']:
        return redirect(url_for('.board', id=id,
                                message="This user is already in this board", status="error"))
    if user_entity:
        addUserInBoard(board, email)
        return redirect(url_for('.board', id=id,
                                message="The user has been added", status="success"))
    else:
        return redirect(url_for('.board', id=id,
                                message="The email does not match with an account", status="error"))


@app.errorhandler(404)
def notFound(error):
    return redirect(url_for('.root', message=error, status="error"))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
