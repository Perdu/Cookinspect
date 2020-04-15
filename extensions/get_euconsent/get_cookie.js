var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function getCookie(tabs) {
    // we're supposed to put tabs[0].url in url here, but for some reason, it only works with undefined
    api.cookies.getAll({
	url: undefined,
	name: 'euconsent'
	//domain: '.consensu.org'
    }, function (cookies) {
	//if (cookies.length > 0) {
	console.log("sc-cookies-vue:", cookies, "url:", tabs[0].url);
	if (cookies.length > 0) {
	    for(i = 0; i < cookies.length; i++) {
		if (cookies[i].domain == '.consensu.org') {
		    api.tabs.sendMessage(tabs[0].id, {sc_cookie: cookies[i].value})
		}
	    }
	}
	//}
    });
    //return euconsent;
}

function dump_cookie() {
    api.tabs.query({active: true, currentWindow: true}, function(tabs) {
        if (tabs[0] === undefined) {
            return;
        }
	getCookie(tabs);
    });
    //console.log("sc-euconsent:", cookie, window.origin);
}

window.setInterval(function(){
    dump_cookie();
}, 1000);
