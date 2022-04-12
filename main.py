from crypt import methods
from datetime import datetime
import hashlib
import random
import google.oauth2.id_token
from flask import Flask, render_template, request, redirect, url_for
from google.auth.transport import requests
from google.cloud import datastore


app = Flask(__name__)
datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


def getUser(claims):
    entity_key = datastore_client.key('User', claims['email'])
    entity = datastore_client.get(entity_key)
    if not entity:
        entity = datastore.Entity(key=entity_key)
        entity.update({
            'name': claims['name'],
            'boards': []
        })
        datastore_client.put(entity)
    return entity


def getUserByEmail(email):
    return datastore_client.get(datastore_client.key('User', email))


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


def createBoard(name, email):
    # create board
    id = random.getrandbits(63)
    board_key = datastore_client.key('Board', id)
    board = datastore.Entity(key=board_key)
    board.update({
        'name': name,
        'tasks': [],
        'users': [email]
    })
    # add board id to user
    user = getUserByEmail(email)
    new_board_list = user['boards']
    new_board_list.append(id)
    user.update({
        'boards': new_board_list
    })
    transaction = datastore_client.transaction()
    with transaction:
        transaction.put(board)
        transaction.put(user)
    return id


@app.route('/put_board', methods=['POST'])
def putboard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            boardId = createBoard(request.form['name'], claims['email'])
            message = "Your board has been created !"
            status = "success"
        except ValueError as exc:
            message = str(exc)
            status = "error"

    return redirect(url_for('.board', id=boardId, message=message, status=status))


def getBoardById(id):
    return datastore_client.get(datastore_client.key('Board', id))


def getTasksFromBoard(board):
    taskIds = board['tasks']
    list = []
    for i in range(len(taskIds)):
        list.append(datastore_client.get(
            datastore_client.key('Task', taskIds[i])))
    return list


@app.route('/board/<int:id>', methods=['GET'])
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
                return redirect(url_for('.root', message=("This board does not exist:" + str(id)), status="error"))
        except ValueError as exc:
            message = str(exc)
            status = "error"
    else:
        return render_template('login.html', message="You can't access this page without being logged in", status="error")

    return render_template('board.html', user_data=user_data, boards=boards, board=board, tasks=tasks, today=datetime.today().strftime('%Y-%m-%d'), message=message, status=status)


def addUserInBoard(board, user):
    # update board
    user_list = board['users']
    user_list.append(user.key.name)
    board.update({
        'users': user_list
    })
    # update user
    new_board_list = user['boards']
    new_board_list.append(board.key.id)
    user.update({
        'boards': new_board_list
    })
    transaction = datastore_client.transaction()
    with transaction:
        transaction.put(board)
        transaction.put(user)


@app.route('/put_user_in_board', methods=['POST'])
def putUserInBoard():
    id = int(request.form['board-id'])
    email = request.form['email']
    board = getBoardById(id)
    if email in board['users']:
        return redirect(url_for('.board', id=id,
                                message="This user is already in this board", status="error"))
    user = getUserByEmail(email)
    if user:
        addUserInBoard(board, user)
        return redirect(url_for('.board', id=id,
                                message="The user has been added", status="success"))
    else:
        return redirect(url_for('.board', id=id,
                                message="The email does not match with an account", status="error"))


def getTaskById(id):
    return datastore_client.get(datastore_client.key('Task', id))


def createTask(name, assignedUser, dueDate, boardId):
    id = hashlib.md5((name + str(boardId)).encode()).hexdigest()
    if getTaskById(id):
        return False
    else:
        # create task entity
        task_key = datastore_client.key('Task', id)
        task = datastore.Entity(key=task_key)
        if not assignedUser:
            assignedUser = "unassigned"
        task.update({
            'name': name,
            'assigned': assignedUser,
            'due': dueDate,
            'board': boardId,
            'done': None
        })
        # add task id to board
        board = getBoardById(boardId)
        new_task_list = board['tasks']
        new_task_list.append(id)
        board.update({
            'tasks': new_task_list
        })
        # put in datastore
        transaction = datastore_client.transaction()
        with transaction:
            transaction.put(task)
            transaction.put(board)
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


def putTaskDone(task):
    task.update({
        'done':  datetime.today()
    })
    datastore_client.put(task)


@app.route('/check_task', methods=['POST'])
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
        'done':  None,
    })
    datastore_client.put(task)


@app.route('/uncheck_task', methods=['POST'])
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


def updateTaskInfo(task, assignedUser, dueDate):
    task.update({
        'assigned': assignedUser,
        'due': dueDate,
    })
    datastore_client.put(task)


def updateTaskId(boardId, name, assignedUser, dueDate, taskIndex):
    id = hashlib.md5((name + str(boardId)).encode()).hexdigest()
    new_task_key = datastore_client.key('Task', id)
    if datastore_client.get(new_task_key):
        return False
    else:
        # create new task entity
        new_task = datastore.Entity(new_task_key)
        new_task.update({
            'name': name,
            'assigned': assignedUser,
            'due': dueDate,
            'board': boardId,
            'done':  None
        })

        # delete old task entity
        board = getBoardById(boardId)
        taskListKeys = board['tasks']
        oldTaskKey = datastore_client.key('Task', taskListKeys[taskIndex])
        del taskListKeys[taskIndex]
        # add task id to board
        taskListKeys.append(id)
        board.update({
            'tasks': taskListKeys
        })
        # update datastore
        transaction = datastore_client.transaction()
        with transaction:
            transaction.put(new_task)
            transaction.delete(oldTaskKey)
            transaction.put(board)

        return True


@app.route('/update_task', methods=['POST'])
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
                assignedUser = request.form.get('update-assigned-user')
                if not assignedUser:
                    assignedUser = "unassigned"
                if request.form['update-task-name'] == task['name']:
                    updateTaskInfo(task, assignedUser,  datetime.strptime(
                        request.form['update-due-date'], '%Y-%m-%d'))
                    message = "Task has been updated !"
                    status = "success"
                else:
                    isUpdate = updateTaskId(boardId, request.form['update-task-name'], assignedUser,
                                            datetime.strptime(request.form['update-due-date'], '%Y-%m-%d'), int(request.form['task-index']))
                    if isUpdate:
                        message = "Task has been updated !"
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
    del taskListKeys[taskIndex]
    board.update({
        'tasks': taskListKeys
    })
    transaction = datastore_client.transaction()
    with transaction:
        transaction.delete(taskKey)
        transaction.put(board)


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


def deleteUserFromBoard(boardId, email, index):
    # delete user from board
    board = getBoardById(boardId)
    userListKeys = board['users']
    del userListKeys[index]
    board.update({
        'users': userListKeys
    })

    # delete board from user
    user = getUserByEmail(email)
    boardList = user['boards']
    index = boardList.index(boardId)
    del boardList[index]
    user.update({
        'boards': boardList
    })
    tasks = getTasksFromBoard(board)
    transaction = datastore_client.transaction()
    with transaction:
        transaction.put(board)
        transaction.put(user)
        for task in tasks:
            if task['assigned'] == email:
                task.update({
                    'assigned': 'unassigned',
                    'to-assign': True,
                })
                transaction.put(task)


@app.route('/delete_user', methods=['POST'])
def removeUserFromBoard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            deleteUserFromBoard(
                int(request.form['board-id']), request.form['user-email'], int(request.form['user-index']))
            message = "The user has been removed !"
            status = "success"
        except ValueError as exc:
            message = str(exc)
            status = "error"

    return redirect(url_for('.board', id=int(request.form['board-id']), message=message, status=status))


def deleteBoard(id, email):
    boardKey = datastore_client.key('Board', id)
    user = getUserByEmail(email)
    boardList = user['boards']
    index = boardList.index(id)
    del boardList[index]
    user.update({
        'boards': boardList
    })
    transaction = datastore_client.transaction()
    with transaction:
        transaction.delete(boardKey)
        transaction.put(user)


@app.route('/delete_board', methods=['POST'])
def removeBoard():
    id_token = request.cookies.get("token")
    message = None
    status = None
    if id_token:
        try:
            deleteBoard(
                int(request.form['board-id']), request.form['user-email'])
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
