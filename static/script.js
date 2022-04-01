'use strict';
window.addEventListener('load', function () {

    var modalMessage = document.getElementById('custom-message')
    if (modalMessage) {
        var message = new bootstrap.Modal(modalMessage, {
            keyboard: true
        })
        message.show()
    }

    document.getElementById('sign-out').onclick = function () {
        firebase.auth().signOut();
        document.cookie = "token=" + ";path=/";
        window.location.replace("/login");
    }

    firebase.auth().onAuthStateChanged(function (user) {
        if (user) {
            document.cookie = "token=" + token + ";path=/";
        } else {
            document.cookie = "token=" + ";path=/";
        }
    }, function (error) {
        console.log(error);
        alert('Unable to log in: ' + error);
    });
});

function editTask(id, boardId, index) {
    var taskContainer = document.querySelector('#task-' + id);
    var checkbox = taskContainer.querySelector(':scope > .task-checkbox')
    var name = taskContainer.querySelector(':scope > .task-name')
    var assignedUser = taskContainer.querySelector(':scope > .task-assigned-user')
    var dueDate = taskContainer.querySelector(':scope > .task-due-date')
    var options = taskContainer.querySelector(':scope > .task-options')

    // create form
    const formId = "update-task-" + id

    var newCheckbox = document.createElement("form")
    newCheckbox.setAttribute("id", formId)
    newCheckbox.setAttribute("action", "/update_task")
    newCheckbox.setAttribute("method", "post")
    var idBoard = document.createElement("input")
    idBoard.setAttribute("type", "hidden")
    idBoard.setAttribute("name", "board-id")
    idBoard.setAttribute("value", boardId)
    newCheckbox.appendChild(idBoard)
    var idTask = document.createElement("input")
    idTask.setAttribute("type", "hidden")
    idTask.setAttribute("name", "task-id")
    idTask.setAttribute("value", id)
    newCheckbox.appendChild(idTask)
    var indexTask = document.createElement("input")
    indexTask.setAttribute("type", "hidden")
    indexTask.setAttribute("name", "task-index")
    indexTask.setAttribute("value", index)
    newCheckbox.appendChild(indexTask)
    checkbox.innerHTML = ''
    checkbox.appendChild(newCheckbox)

    // create name input
    var nameInput = document.createElement("input")
    nameInput.setAttribute("type", "text")
    nameInput.setAttribute("class", "form-control")
    nameInput.setAttribute("form", formId)
    nameInput.setAttribute("name", "update-task-name")
    nameInput.setAttribute("value", name.innerText)
    nameInput.setAttribute("placeholder", "Task name");
    nameInput.setAttribute("required", "");
    name.innerHTML = ''
    name.appendChild(nameInput)

    // create due date input
    var dueDateInput = document.createElement("input")
    dueDateInput.setAttribute("type", "date")
    dueDateInput.setAttribute("class", "form-control")
    dueDateInput.setAttribute("form", formId)
    dueDateInput.setAttribute("name", "update-due-date")
    let date = new Date(dueDate.innerText)
    dueDateInput.setAttribute("value", date.toISOString().substring(0, 10))
    dueDateInput.setAttribute("required", "");
    dueDate.innerHTML = ''
    dueDate.appendChild(dueDateInput)

    // create submit button
    var submitButton = document.createElement("input")
    submitButton.setAttribute("type", "submit")
    submitButton.setAttribute("class", "form-control btn btn-success")
    submitButton.setAttribute("form", formId)
    submitButton.setAttribute("value", "Update")
    options.innerHTML = ''
    options.appendChild(submitButton)

    // creation assigned user selection

    var group = document.createElement("div")
    group.setAttribute("class", "input-group")
    var col1 = document.createElement("div")
    col1.setAttribute("class", "input-group-text")

    var checkboxUser = document.createElement("input")
    checkboxUser.setAttribute("type", "checkbox")
    checkboxUser.setAttribute("class", "form-check-input")
    checkboxUser.setAttribute("onChange", "document.getElementById('update-assigned-user-" + id + "').disabled = !this.checked; document.getElementById('update-assigned-user-" + id + "').required = this.checked; document.getElementById('user-pick-defaut-selection-" + id + "').selected = true ")
    col1.appendChild(checkboxUser)

    var selectUser = document.createElement("select")
    selectUser.setAttribute("id", "update-assigned-user-" + id)
    selectUser.setAttribute("name", "update-assigned-user")
    selectUser.setAttribute("form", formId)
    selectUser.setAttribute("class", "form-select")
    if (assignedUser.innerText == "unassigned")
        selectUser.setAttribute("disabled", "");

    var defaultOption = document.createElement("option")
    defaultOption.setAttribute("id", "user-pick-defaut-selection-" + id);
    defaultOption.setAttribute("disabled", "");
    defaultOption.setAttribute("selected", "");
    defaultOption.setAttribute("value", "");
    defaultOption.innerHTML = "Select a user"

    selectUser.appendChild(defaultOption)

    var users = document.getElementsByName("user-choice")
    users.forEach(function (user) {
        var newUser = user.cloneNode(true)
        if (newUser.innerText.trim() == assignedUser.innerText.trim()) {
            checkboxUser.setAttribute("checked", "")
            defaultOption.setAttribute("selected", "false");
            newUser.setAttribute("selected", "");
        }
        selectUser.appendChild(newUser)
    });

    group.appendChild(col1)
    group.appendChild(selectUser)

    assignedUser.innerHTML = ''

    assignedUser.appendChild(group)
}