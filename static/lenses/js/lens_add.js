let lensForm = document.querySelectorAll(".lens-form");
let container = document.querySelector("#form-container");
let addButton = document.querySelector("#add-form");
let removeButton = document.querySelectorAll(".remove-button");
let totalForms = document.querySelector("#id_form-TOTAL_FORMS");

let formNum = lensForm.length-1;
let baseForm = lensForm[0].cloneNode(true);
let Nforms = parseInt(totalForms.getAttribute('value'));


addButton.addEventListener('click', addForm);

removeButton.forEach((button) => {
    button.addEventListener('click', removeLens);
});


function addForm(e){
    e.preventDefault();
    
    let newForm = lensForm[0].cloneNode(true);
    let formRegex = RegExp(`form-(\\d){1}-`,'g');

    formNum++;
    newForm.innerHTML = newForm.innerHTML.replace(formRegex, `form-${formNum}-`);
    newForm.querySelector('.remove-button').addEventListener('click',removeLens);
    Nforms += 1;
    totalForms.setAttribute('value', Nforms);
    
    // let btn = document.createElement("button");
    // btn.classList.add('remove-button');
    // btn.innerHTML = "remove";
    // newForm.appendChild(btn);
    console.log(Nforms);
    
    container.insertBefore(newForm, addButton);
}

function removeLens(e){
    e.preventDefault();
    this.parentNode.remove();
    Nforms -= 1;
    totalForms.setAttribute('value', Nforms);
    console.log(Nforms);
}

