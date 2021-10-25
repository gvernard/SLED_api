$( document ).ready(function() {
    users_autocomplete();
});
    

function users_autocomplete(){
    $("#users-autocomplete").select2({
	width: '100%',
	ajax: {
	    url: "/api/",
	    dataType: 'json',
	    delay: 250,
	    data: function (params) {
		return {
		    q: params.term, // search term
		};
	    },
	    processResults: function (data, params) {

		var results = []
		$.each(data.users,function(i,user){
		    results.push({
			id: i,
			text: String(user.username),
			first_name: String(user.first_name),
			last_name: String(user.last_name),
			full_name: String(user.first_name+' '+user.last_name),
			email: String(user.email)
		    });
		});
		
		return {
		    results: results,
		    pagination: {
			more: false
		    }
		};
	    },
	    cache: true
	},
	placeholder: 'Search for a user',
	minimumInputLength: 1,
	templateResult: formatUser,
	templateSelection: formatUserSelection
    });
}

function formatUser(user){
    if (user.loading) {
	return user.text;
    }

    var $container = $(
	"<div class='select2-result-repository clearfix'>" +
	    "<div class='select2-result-user__meta'>" +
            "<div class='select2-result-user__full_name'></div>" +
	    "</div>" +
	    "</div>"
    );
    $container.find(".select2-result-user__full_name").append(user.first_name + " " + user.last_name);
    
    return $container;
}

function formatUserSelection(user){
    return user.full_name;
}
