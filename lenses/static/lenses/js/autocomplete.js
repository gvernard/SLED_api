function groups_autocomplete(target_id){
    $("#"+target_id).select2({
	width: '100%',
	ajax: {
	    url: $("#Urlgroups").attr("data-url"),
	    dataType: 'json',
	    delay: 250,
	    data: function (params) {
		return {
		    q: params.term, // search term
		};
	    },
	    processResults: function (data, params) {
		var results = []
		console.log(data.groups);
		$.each(data.groups,function(i,group){
		    results.push({
			id: group.id,
			text: String(group.name),
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
	placeholder: 'Search for a group',
	minimumInputLength: 1,
	templateResult: formatGroup,
	templateSelection: formatGroupSelection
    });
}


function formatGroup(group){
    if (group.loading) {
	return group.text;
    }
    var $container = $(
	"<div class='select2-result-repository clearfix'>" +
	    "<div class='select2-result-group__meta'>" +
            "<div class='select2-result-group__name'></div>" +
	    "</div>" +
	    "</div>"
    );
    $container.find(".select2-result-group__name").append(group.text);    
    return $container;
}

function formatGroupSelection(group){
    return group.text;
}





function users_autocomplete(target_id){
    $("#"+target_id).select2({
	width: '100%',
	ajax: {
	    url: $("#Urlusers").attr("data-url"),
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
			id: user.id,
			text: String(user.first_name)+' '+String(user.last_name),
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
    return user.text;
}
