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
    boards = []
    message = request.args.get('message')
    status = request.args.get('status')
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_data = getUser(claims)
            boards = getBoardsFromUser(user_data)
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html')
    return render_template('index.html', user_data=user_data, boards=boards, message=message, status=status)


def getBoardsFromUser(user_data):
    boardIds = user_data['boards']
    boardKeys = []
    for i in range(len(boardIds)):
        boardKeys.append(datastore_client.key('Board', boardIds[i]))
    return datastore_client.get_multi(boardKeys)


@ app.route('/login')
def login():
    id_token = request.cookies.get("token")
    if id_token:
        return redirect(url_for('.root', message="You are already logged in", status="success"))
    else:
        return render_template('login.html')


@ app.route('/my_account')
def myAccount():
    id_token = request.cookies.get("token")
    claims = None
    user_data = None
    boards = []
    message = None
    status = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_data = getUser(claims)
            boards = getBoardsFromUser(user_data)
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html', message="You can't access this page without being logged in", status="error")

    return render_template('my_account.html', user_data=user_data, boards=boards, message=message, status=status)


def addBoardToUser(email, id):
    entity_key = datastore_client.key('User', email)
    entity = datastore_client.get(key=entity_key)
    new_board_list = entity['boards']
    new_board_list.append(id)
    entity.update({
        'boards': new_board_list
    })
    datastore_client.put(entity)


def createBoard(name, email):
    entity_key = datastore_client.key('Board')
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'name': name,
        'tasks': [],
        'users': [email]
    })
    datastore_client.put(entity)
    addBoardToUser(email, entity.key.id)


@ app.route('/put_board', methods=['POST'])
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
    list = []
    for i in range(len(taskIds)):
        list.append(datastore_client.get(
            datastore_client.key('Task', taskIds[i])))
    return list


@ app.route('/board/<int:id>', methods=['GET'])
def board(id):
    id_token = request.cookies.get("token")
    claims = None
    user_data = None
    boards = []
    board = None
    tasks = None
    message = request.args.get('message')
    status = request.args.get('status')
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_data = getUser(claims)
            boards = getBoardsFromUser(user_data)
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

    return render_template('board.html', user_data=user_data, boards=boards, board=board, tasks=tasks, today=datetime.today().strftime('%Y-%m-%d'), message=message, status=status)


def addUserInBoard(board, email):
    user_list = board['users']
    user_list.append(email)
    board.update({
        'users': user_list
    })
    datastore_client.put(board)
    addBoardToUser(email, board.key.id)


@ app.route('/put_user_in_board', methods=['POST'])
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
    entity_key = datastore_client.key('Board', boardId)
    entity = datastore_client.get(key=entity_key)
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


@ app.route('/add_task', methods=['POST'])
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


def putTaskDone(task):
    task.update({
        'done': True,
        'done-date': datetime.today(),
    })
    datastore_client.put(task)


@ app.route('/check_task', methods=['POST'])
def checkTask():
    id_token = request.cookies.get("token")
    message = None
    status = None
    taskId = request.form['task-id']
    boardId = int(request.form['board-id'])
    if id_token:
        try:
            task = getTaskById(taskId)
            if task:
                putTaskDone(task)
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


def putTaskUndone(task):
    task.update({
        'done': False,
        'done-date': None,
    })
    datastore_client.put(task)


@ app.route('/uncheck_task', methods=['POST'])
def uncheckTask():
    id_token = request.cookies.get("token")
    message = None
    status = None
    taskId = request.form['task-id']
    boardId = int(request.form['board-id'])
    if id_token:
        try:
            task = getTaskById(taskId)
            if task:
                putTaskUndone(task)
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


@ app.route('/update_task', methods=['POST'])
def updateTask():
    id_token = request.cookies.get("token")
    message = None
    status = None
    taskId = request.form['task-id']
    boardId = int(request.form['board-id'])
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
    datastore_client.delete(taskKey)
    del taskListKeys[taskIndex]
    board.update({
        'tasks': taskListKeys
    })
    datastore_client.put(board)


@ app.route('/delete_task', methods=['POST'])
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


def updateBoardName(board, name):
    board.update({
        'name': name
    })
    datastore_client.put(board)


@app.route('/rename_board', methods=['POST'])
def renameBoard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    boardId = int(request.form['board-id'])
    boardName = request.form['board-name']
    if id_token:
        try:
            board = getBoardById(boardId)
            if board:
                if boardName != board['name']:
                    updateBoardName(board, boardName)
                    message = "Board has been renamed !"
                    status = "success"
            else:
                message = "Board not found"
                status = "error"

        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        message = "You must log in to update a vehicle"
        status = "error"
    return redirect(url_for('.board', id=boardId, message=message, status=status))


def deleteBoardFromUser(email, boardId):
    user = getUserByEmail(email)
    boardList = user['boards']
    index = boardList.index(boardId)
    del boardList[index]
    user.update({
        'boards': boardList
    })
    datastore_client.put(user)


def deleteUserFromBoard(boardId, index):
    board = getBoardById(boardId)
    userListKeys = board['users']
    del userListKeys[index]
    board.update({
        'users': userListKeys
    })
    datastore_client.put(board)


@app.route('/delete_user', methods=['POST'])
def removeUserFromBoard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            deleteUserFromBoard(
                int(request.form['board-id']), int(request.form['user-index']))
            deleteBoardFromUser(
                request.form['user-email'], int(request.form['board-id']))
            message = "The user has been removed !"
            status = "success"
        except ValueError as exc:
            message = str(exc)
            status = "error"

    return redirect(url_for('.board', id=int(request.form['board-id']), message=message, status=status))


def deleteBoard(id):
    boardKey = datastore_client.key('Board', id)
    datastore_client.delete(boardKey)


@app.route('/delete_board', methods=['POST'])
def removeBoard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            deleteBoard(
                int(request.form['board-id']))
            deleteBoardFromUser(
                request.form['user-email'], int(request.form['board-id']))
            message = "The board has been removed !"
            status = "success"
        except ValueError as exc:
            message = str(exc)
            status = "error"
    return redirect(url_for('.root', message=message, status=status))


@app.errorhandler(404)
def notFound(error):
    return redirect(url_for('.root', message=error, status="error"))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
