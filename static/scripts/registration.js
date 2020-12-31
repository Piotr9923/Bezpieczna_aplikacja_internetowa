let mail_correct = true
let phone_correct = true
let login_correct = true
let password_correct = true
let password2_correct = true
let master_password_correct = true
let master_password2_correct = true

let mail = document.getElementById("mail")
let phone = document.getElementById("phone_number")
let login = document.getElementById("login")
let password = document.getElementById("password")
let password2 = document.getElementById("password2")
let master_password = document.getElementById("master_password")
let master_password2 = document.getElementById("master_password2")


let buttons = document.getElementsByTagName("img")

let description = []
description.push("Adres e-mail może składać się z małych i dużych liter alfabetu łacińskiego, cyfr oraz symboli:  znak podkreślenia (_ ), kropka(.), myślnik (-), małpa (@) ")
description.push("Numer telefonu musi składać się z cyfr")
description.push("Login może zawierać małe i duże litery alfabetu łacińskiego oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-)")
description.push("Hasło może zawierać małe i duże litery alfabetu łacińskiego oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-), wykrzyknik (!), dolar ($) i gwiazdkę (*)")
description.push("Hasło główne może zawierać małe i duże litery alfabetu łacińskiego oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-), wykrzyknik (!), dolar ($) i gwiazdkę (*)")

update_submit_button();
buttons_events()
input_fields_events()

// var imie = prompt("Podaj imię", "Adam");
// console.log("Twoje imię: "+imie);


function buttons_events(){

    for(i=1;i<buttons.length;i++){
        buttons[i].i=i
        buttons[i].addEventListener("click", function(ev){
            info = description.slice(this.i-1,this.i)    
            alert(info.pop())
        });

    }

}


function input_fields_events(){

    mail.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z_.@-]+$/)){
            mail_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            mail_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

    phone.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[0-9]+$/)){
            phone_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            phone_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });


    login.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z_.-]+$/)){
            login_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            login_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

    password.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z_.@!$*-]+$/)){
            password_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            password_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

    password2.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z_.@!$*-]+$/)){
            password2_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            password2_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

    master_password.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z_.@!$*-]+$/)){
            master_password_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            master_password_correct = false;
            this.classList.add("incorrect_field");

        }

        update_submit_button()

    });

    master_password2.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z_.@!$*-]+$/)){
            master_password_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            master_password_correct = false;
            this.classList.add("incorrect_field");

        }

        update_submit_button()

    });

}


function update_submit_button(){

    if(mail_correct && phone_correct && login_correct && password_correct && password2_correct && master_password_correct &&master_password2_correct){
        document.getElementById("button").disabled = false;
        document.getElementById("button").classList.remove("disabled_button");
        document.getElementById("info").innerText = ""
    }else{
        document.getElementById("button").disabled = true;
        document.getElementById("button").classList.add("disabled_button");
        document.getElementById("info").innerText = "Formularz zawiera niedozwolone symbole!"
    }

}

function correct_values(word,values){
    

    for(i=0;i<word.length;i++){
        
        if(!word[i].match(values)){
            return false;
        }

    }

    return true

}