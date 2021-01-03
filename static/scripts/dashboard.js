var buttons = document.getElementsByTagName("button")
var passwords_column = document.getElementsByClassName("password")

console.log(passwords_column.length)
function attach_events() {
    for(i=0;i< buttons.length;i++){

        buttons[i].i=i
        buttons[i].addEventListener("click", function(ev){

            if(this.value=="copy"){
                const el = document.createElement('textarea');
                el.value = passwords_column[this.i].value;
                el.setAttribute('readonly', '');
                el.style.position = 'absolute';
                el.style.left = '-9999px';
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
    
            }else{

                var user_password = prompt("Podaj hasło główne", "");

                if(user_password != null){
                    var link = "/passwords/"+this.value+"?password="+user_password
                    var xhr = new XMLHttpRequest();
                    xhr.open("GET", link);
                    xhr.onload = function (e) {
                        var DONE = 4;
                        if (xhr.readyState == DONE) {

                            if(xhr.status != 200){
                                alert(xhr.response)
                            }else{
                                console.log(xhr.response)
                                console.log(this.i)
                                passwords_column[this.i].innerText=xhr.response
                                passwords_column[this.i].value=xhr.response
                                buttons[this.i].innerText="Kopiuj"
                                buttons[this.i].value = "copy"
                            }
                        }
                    }
                    xhr.send();
                    xhr.i=this.i
                }
            }
        })

    }
}

attach_events();