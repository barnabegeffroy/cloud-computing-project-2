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

function editTask(id) {
    console.log(document.querySelector('#assigned-user > :not(:first-child)'))
    var taskContainer = document.querySelector('#' + id);
    var checkbox = taskContainer.querySelector(':scope > .task-checkbox')
    var name = taskContainer.querySelector(':scope > .task-name')
    var assignedUser = taskContainer.querySelector(':scope > .task-assigned-user')
    var dueDate = taskContainer.querySelector(':scope > .task-due-date')
    var options = taskContainer.querySelector(':scope > .task-options')

    // create form
    var newCheckbox = document.createElement("form")
    newCheckbox.setAttribute("id", "update-task-" + id)
    newCheckbox.setAttribute("action", "/update_task")
    newCheckbox.setAttribute("method", "post")
    var idForm = document.createElement("input")
    idForm.setAttribute("type", "hidden")
    idForm.setAttribute("name", "update-task-id")
    idForm.setAttribute("value", id)
    newCheckbox.appendChild(idForm)
    checkbox.innerHTML = ''
    checkbox.appendChild(newCheckbox)

    // create name input
    var nameInput = document.createElement("input")
    nameInput.setAttribute("type", "text")
    nameInput.setAttribute("class", "form-control")
    nameInput.setAttribute("form", "update-task")
    nameInput.setAttribute("id", "update-task-name-" + id)
    nameInput.setAttribute("name", "update-task-name")
    nameInput.setAttribute("value", name.innerHTML)
    nameInput.setAttribute("placeholder", "Task name");
    nameInput.setAttribute("required", "");
    name.innerHTML = ''
    name.appendChild(nameInput)

    // create due date input
    var dueDateInput = document.createElement("input")
    dueDateInput.setAttribute("type", "date")
    dueDateInput.setAttribute("class", "form-control")
    dueDateInput.setAttribute("form", "update-task")
    dueDateInput.setAttribute("id", "update-due-date-" + id)
    dueDateInput.setAttribute("name", "update-due-date")
    dueDateInput.setAttribute("value", dueDate.innerHTML)
    dueDateInput.setAttribute("required", "");
    dueDate.innerHTML = ''
    dueDate.appendChild(dueDateInput)

    // create submit button
    var submitButton = document.createElement("input")
    submitButton.setAttribute("type", "submit")
    submitButton.setAttribute("class", "form-control btn btn-success")
    submitButton.setAttribute("form", "update-task")
    submitButton.setAttribute("value", "Update")
    options.innerHTML = ''
    options.appendChild(submitButton)

    // creation assigned user selection

    var row = document.createElement("div")
    row.setAttribute("class", "row")
    var col1 = document.createElement("div")
    col1.setAttribute("class", "col-1")
    var col11 = document.createElement("div")
    col11.setAttribute("class", "col-11")

    var checkboxUser = document.createElement("input")
    checkboxUser.setAttribute("type", "checkbox")
    checkboxUser.setAttribute("class", "form-check-input")
    checkboxUser.setAttribute("onChange", "document.getElementById('update-assigned-user-" + id + "').disabled = !this.checked; document.getElementById('user-pick-defaut-selection-" + id + "').selected = true ")
    col1.appendChild(checkboxUser)

    var selectUser = document.createElement("select")
    selectUser.setAttribute("id", "update-assigned-user-" + id)
    selectUser.setAttribute("name", "update-assigned-user")
    selectUser.setAttribute("form", "update-task")
    selectUser.setAttribute("class", "form-select")
    if (assignedUser.innerHTML == "unassigned")
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
        if (newUser.innerHTML == assignedUser.innerHTML) {
            checkboxUser.setAttribute("checked", "")
            defaultOption.setAttribute("selected", "false");
            newUser.setAttribute("selected", "");
        }
        selectUser.appendChild(newUser)
    });

    col11.appendChild(selectUser)

    row.appendChild(col1)
    row.appendChild(col11)

    assignedUser.innerHTML = ''

    assignedUser.appendChild(row)
}