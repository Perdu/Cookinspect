window.addEventListener("message", function(e) {
    var callid = "";
    var version;
    var debug = false;
    if (e.data.__cmpCall) {
	callid = e.data.__cmpCall.callId;
        version = 1;
    } else if (debug && e.data.__cmpReturn) {
	callid = e.data.__cmpReturn.callId;
        version = 1;
    } else if (e.data.__tcfapiCall) {
	callid = e.data.__tcfapiCall.callId;
        version = 2;
    } else if (debug && e.data.__tcfapiReturn) {
	callid = e.data.__tcfapiReturn.callId;
        version = 2;
    } else {
	return;
    }
    var re = /^uCookie_/;
    if (!re.test(callid) || debug) {
        if (version == 1) {
	    console.log("sc-postMessage: " + e.origin, callid, e.source, e.data, e);
        } else {
            if (debug) {
                var callid = "";
                if (e.data.__tcfapiCall) {
                    callid = e.data.__tcfapiCall.callId;
                }
                if (e.data.__tcfapiReturn) {
                    callid = e.data.__tcfapiReturn.callId;
                }
                console.log(e.data, callid);
            }
	    console.log("sc-postMessage_v2: " + e.origin, callid, e.source, e.data, e);
        }
    }
});
