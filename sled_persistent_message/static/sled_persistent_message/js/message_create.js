function set_modal_message_create(){
    $("#id_from_date_0").datepicker();
    $("#id_to_date_0").datepicker();
    $('#id_from_date_1').timepicker({
	timeFormat: 'HH:mm',
	interval: 60,
	minTime: '00:00',
	maxTime: '23:00',
	defaultTime: '0',
	startTime: '00:00',
	dynamic: false,
	dropdown: true,
	scrollbar: false,
	zindex: 9999
    });
    $('#id_to_date_1').timepicker({
	timeFormat: 'HH:mm',
	interval: 60,
	minTime: '00:00',
	maxTime: '23:00',
	defaultTime: '0',
	startTime: '00:00',
	dynamic: false,
	dropdown: true,
	scrollbar: false,
	zindex: 9999
    });
}
