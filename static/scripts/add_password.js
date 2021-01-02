let login_correct = true
let password_correct = true

let website = document.getElementById("website")
let password = document.getElementById("password")

let buttons = document.getElementsByTagName("img")
let description = []
description.push("Nazwa serwisu może zawierać małe i duże litery alfabetu łacińskiego, cyfry oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-), wykrzyknik (!), dolar ($), gwiazdkę (*), dwukropek(:), slash (/) i odstęp( ). Maksymalnie 64 znaki.")
description.push("Hasło może zawierać małe i duże litery alfabetu łacińskiego, cyfry oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-), wykrzyknik (!), dolar ($) i gwiazdkę (*)")


input_fields_events()
buttons_events()


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

    website.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z0-9_.-:/ ]+$/)){
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

        if(correct_values(this.value,/[A-Za-z0-9_.@!$*-]+$/)){
            password_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            password_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

}

function update_submit_button(){

    if(login_correct && password_correct){
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