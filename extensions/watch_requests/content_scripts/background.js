var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function handle_response(message) {
    //console.log("ok, got answer");
}

function callback(requestDetails) {
    params = "";
    if (requestDetails.requestBody != undefined) {
	params = String.fromCharCode.apply(null, new Uint8Array(requestDetails.requestBody.raw[0].bytes))
    }
    console.log("Chargement : " + requestDetails.url, requestDetails, params);
    api.tabs.query({active: true, currentWindow: true}, function(tabs) {
        if (tabs[0] === undefined) {
            return;
        }
        try {
            message = {call: requestDetails, post_params: params, manual: false};
            var mes = api.tabs.sendMessage(tabs[0].id, message, handle_response);
        } catch(error) {
            console.log("background.js: error caught", error);
        }
    });
//    return true;
}

api.webRequest.onBeforeRequest.addListener(
  callback,
  {urls: ["<all_urls>"]},
  ["requestBody"]
);
