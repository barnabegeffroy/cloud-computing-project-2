'use strict';
window.addEventListener('load', function () {
    document.getElementById('sign-out').onclick = function () {
        firebase.auth().signOut();
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
