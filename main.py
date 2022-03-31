from crypt import methods
from datetime import datetime
import hashlib
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


def createBoard(name, email):
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
            createBoard(request.form['name'], claims['email'])
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


def getTasksFromBoard(board):
    taskIds = board['tasks']
    taskKeys = []
    list = []
    for i in range(len(taskIds)):
        list.append(datastore_client.get(
            datastore_client.key('Task', taskIds[i])))
    #     taskKeys.append(datastore_client.key('Task', taskIds[i]))
    # list = datastore_client.get_multi(taskKeys)
    return list


@app.route('/board/<int:id>', methods=['GET'])
def board(id):
    id_token = request.cookies.get("token")
    claims = None
    user_data = None
    board = None
    tasks = None
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
                tasks = getTasksFromBoard(board)
            else:
                return redirect(url_for('.root', message="This board does not exist", status="error"))
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html', message="You can't access this page without being logged in", status="error")

    return render_template('board.html', user_data=user_data, board=board, tasks=tasks, message=message, status=status)


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


def addTaskToBoard(boardId, taskId):
    print(boardId)
    entity_key = datastore_client.key('Board', boardId)
    entity = datastore_client.get(key=entity_key)
    print(entity)
    new_task_list = entity['tasks']
    new_task_list.append(taskId)
    entity.update({
        'tasks': new_task_list
    })
    datastore_client.put(entity)


def getTaskById(id):
    entity_key = datastore_client.key('Task', id)
    entity = datastore_client.get(entity_key)
    return entity


def createTask(name, assignedUser, dueDate, boardId):
    id = hashlib.md5((name + str(boardId)).encode()).hexdigest()
    if getTaskById(id):
        return False
    else:
        entity_key = datastore_client.key('Task', id)
        entity = datastore.Entity(key=entity_key)
        if not assignedUser:
            assignedUser = "unassigned"
        entity.update({
            'name': name,
            'assigned': assignedUser,
            'due': dueDate,
            'board': boardId,
            'done': False,
            'done-date': None
        })
        datastore_client.put(entity)
        addTaskToBoard(boardId, id)
        return True


@app.route('/add_task', methods=['POST'])
def addTask():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            task = createTask(request.form['task-name'], request.form.get('assigned-user'),
                              datetime.strptime(request.form['due-date'], '%Y-%m-%d'), int(request.form['board-id']))
            if task:
                message = "Your task has been created !"
                status = "success"
            else:
                message = "This task already exists !"
                status = "error"
        except ValueError as exc:
            message = str(exc)
            status = "error"

    return redirect(url_for('.board', id=int(request.form['board-id']), message=message, status=status))


@app.route('/check_task', methods=['POST'])
def checkTask():
    pass


def updateTaskInfo(id, assignedUser, dueDate):
    entity_key = datastore_client.key('Task', id)
    entity = datastore_client.get(entity_key)
    if not assignedUser:
        assignedUser = "unassigned"
    entity.update({
        'assigned': assignedUser,
        'due': dueDate,
    })
    datastore_client.put(entity)


def updateTaskId(boardId, name, assignedUser, dueDate):
    id = hashlib.md5((name + str(boardId)).encode()).hexdigest()
    entity_key = datastore_client.key('Task', id)
    if datastore_client.get(entity_key):
        return None
    entity = datastore.Entity(entity_key)
    if not assignedUser:
        assignedUser = "unassigned"
    entity.update({
        'name': name,
        'assigned': assignedUser,
        'due': dueDate,
        'board': boardId,
        'done': False,
        'done-date': None
    })
    datastore_client.put(entity)
    return id


@app.route('/update_task', methods=['POST'])
def updateTask():
    id_token = request.cookies.get("token")
    message = None
    status = None
    taskId = request.form['task-id']
    boardId = int(request.form['board-id'])
    print(request.form['board-id'])
    print(request.form['update-task-name'])
    print(request.form.get('update-assigned-user'))
    print(request.form['update-due-date'])
    if id_token:
        try:
            task = getTaskById(taskId)
            if task:

                if request.form['update-task-name'] == task['name']:
                    updateTaskInfo(taskId, request.form.get(
                        'update-assigned-user'),  datetime.strptime(request.form['update-due-date'], '%Y-%m-%d'))
                    message = "Task has been updated !"
                    status = "success"
                else:
                    taskId = updateTaskId(boardId, request.form['update-task-name'], request.form.get(
                        'update-assigned-user'), datetime.strptime(request.form['update-due-date'], '%Y-%m-%d'))
                    if taskId:
                        deleteTask(boardId,
                                   int(request.form['task-index']))

                        addTaskToBoard(boardId, taskId)
                        message = "Vehicle has been updated !"
                        status = "success"
                    else:
                        message = "The information you wish to add corresponds to an existing task"
                        status = "error"
            else:
                message = "Task not found"
                status = "error"

        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        message = "You must log in to update a vehicle"
        status = "error"
    return redirect(url_for('.board', id=boardId, message=message, status=status))


def deleteTask(boardId, taskIndex):
    board = getBoardById(boardId)
    taskListKeys = board['tasks']
    taskKey = datastore_client.key('Task', taskListKeys[taskIndex])
    print(taskKey)
    datastore_client.delete(taskKey)
    del taskListKeys[taskIndex]
    board.update({
        'tasks': taskListKeys
    })
    datastore_client.put(board)


@app.route('/delete_task', methods=['POST'])
def removeTask():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            deleteTask(int(request.form['board-id']),
                       int(request.form['task-index']))
            message = "Your task has been removed !"
            status = "success"
        except ValueError as exc:
            message = str(exc)
            status = "error"

    return redirect(url_for('.board', id=int(request.form['board-id']), message=message, status=status))


@app.route('/rename_board', methods=['POST'])
def renameBoard():
    pass


@app.route('/delete_user', methods=['POST'])
def removeUserFromBoard():
    pass


@app.route('/delete_board', methods=['POST'])
def removeBoard():
    pass


@app.errorhandler(404)
def notFound(error):
    return redirect(url_for('.root', message=error, status="error"))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
