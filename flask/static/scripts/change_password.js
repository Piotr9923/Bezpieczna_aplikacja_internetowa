let login_correct = true
let mail_correct = true

let login = document.getElementById("login")
let mail = document.getElementById("mail")

input_fields_events()


function input_fields_events(){

    login.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z0-9_.-]+$/)){
            login_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            login_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

    mail.addEventListener("keyup", function (ev) {

        if(correct_values(this.value,/[A-Za-z0-9_.@!$*-]+$/)){
            mail_correct = true;
            this.classList.remove("incorrect_field");
        }
        else{
            mail_correct = false;
            this.classList.add("incorrect_field");
        }

        update_submit_button()

    });

}

function update_submit_button(){

    if(login_correct && mail_correct){
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