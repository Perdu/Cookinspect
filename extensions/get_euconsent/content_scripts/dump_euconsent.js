var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function handle_message(message, sender, sendResponse) {
    if (message.sc_cookie) {
        if (message.version == 1) {
	    console.log("sc-cookie:", message.sc_cookie)
        } else {
	    console.log("sc-cookie-v2:", message.sc_cookie)
        }
    }
}

api.runtime.onMessage.addListener(handle_message);
