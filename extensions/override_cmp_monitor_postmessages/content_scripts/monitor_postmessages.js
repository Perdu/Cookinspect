window.addEventListener("message", function(e) {
    var callid = "";
    if (e.data.__cmpCall) {
	callid = e.data.__cmpCall.callId;
    } else if (e.data.__cmpReturn) {
	callid = e.data.__cmpReturn.callId;
    } else {
	return;
    }
    var re = /^uCookie_/;
    if (!re.test(callid)) {
	console.log("postMessage: ", window.origin, e.origin, callid, e.source, e.data, e);
    }
});
