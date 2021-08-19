var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function fetch_data(interval=false) {
    api.tabs.query({active: true, currentWindow: true}, function(tabs) {
	if (tabs[0] === undefined) {
	    return;
	}
	try {
	    message = {call: "getConsentData", manual: false};
	    var mes = api.tabs.sendMessage(tabs[0].id, message, handle_response);
	    message2 = {call: "getVendorConsents", manual: false};
	    var mes2 = api.tabs.sendMessage(tabs[0].id, message2, handle_response);
	    message_v2 = {call: "getTCData", manual: false};
	    var mes_v2 = api.tabs.sendMessage(tabs[0].id, message_v2, handle_response_v2);
	} catch(error) {
	    console.log("background.js: error caught", error);
	}
    });
}

function handle_response(message) {
    if (message == undefined || message.response == null)
	return;
    var res = message.response;
    // written in hidden views
    if (res.metadata)
	console.log("sc-probe-cmp-metadata:", res.metadata);
    if (res.consentData)
	console.log("sc-probe-cmp-consentData:", res.consentData);
}

function handle_response_v2(message) {
    if (message == undefined || message.response == null)
	return;
    var res = message.response;
    // written in hidden views
    if (res.TCData)
	console.log("sc-probe-cmp-TCData:", res.TCData);
}

/*window.onload = function() {
    fetch_data();
}
*/
/*console.log("sleeping");

// Javascript sucks.
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
async function call_sleep() {
    await sleep(5000);
}
call_sleep();

console.log("done sleeping");

fetch_data();*/

window.setInterval(function(){
    fetch_data();
}, 2000);
