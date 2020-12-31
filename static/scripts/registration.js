let buttons = document.getElementsByTagName("img")

let description = []
description.push("Adres e-mail może składać się z małych i dużych liter alfabetu łacińskiego, cyfr oraz symboli:  znak podkreślenia (_ ), kropka(.), myślnik (-), małpa (@) ")
description.push("Numer telefonu musi składać się z cyfr")
description.push("Login może zawierać małe i duże litery alfabetu łacińskiego oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-)")
description.push("Hasło może zawierać małe i duże litery alfabetu łacińskiego oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-), wykrzyknik (!), dolar ($) i gwiazdkę (*)")
description.push("Hasło główne może zawierać małe i duże litery alfabetu łacińskiego oraz symbole: znak podkreślenia (_ ), kropka(.), myślnik (-), wykrzyknik (!), dolar ($) i gwiazdkę (*)")



function attach_events(){

    for(i=1;i<buttons.length;i++){
        buttons[i].i=i
        buttons[i].addEventListener("click", function(ev){
            info = description.slice(this.i-1,this.i)    
            alert(info.pop())
        });

    }


}

attach_events()