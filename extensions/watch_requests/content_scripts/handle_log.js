var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function log_message(message) {
    console.log("sc-requests: " + message.call.url, message.call.method, message.post_params, message)
}

api.runtime.onMessage.addListener(log_message);
