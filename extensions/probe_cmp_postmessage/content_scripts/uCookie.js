var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}
var correct_frame_v1;
var correct_frame_v2;

function setup_cmp_wrapper(version) {
    // find the CMP frame
    var f = window;
    var cmpFrame;
    if (version == 1) {
        var frame_name = "__cmpLocator";
    } else if (version == 2) {
        var frame_name = "__tcfapiLocator";
    }
    while(!cmpFrame) {
	try {
	    if(f.frames[frame_name]) {
		cmpFrame = f;
                break;
	    }
	} catch(e) {}
	if(f === window.top)
	    break;
	f = f.parent;
    }
    if (!cmpFrame) {
	return 0;
    }
    //console.log("__cmpLocator found. Version " + version);

    var cmpCallbacks = {}
    var tcfapiCallbacks = {}

    /* Set up a __cmp function to do the postMessage and 
       stash the callback.
       This function behaves (from the caller's perspective)
       identically to the in-frame __cmp call */

    if (version == 1) {
        window.__cmpCookieGlasses = function(cmd, arg, callback) {
	    var callId = "uCookie_" + Math.random() + "";
	    var msg = {__cmpCall: {
	        command: cmd,
	        parameter: arg,
	        callId: callId
	    }};
	    cmpCallbacks[callId] = callback;
	    cmpFrame.postMessage(msg, '*');
        }
    } else if (version == 2) {
        window.__tcfapiCookieGlasses = function(cmd, version, arg, callback) {
	    var callId = "uCookie_" + Math.random() + "";
	    var msg = {__tcfapiCall: {
	        command: cmd,
	        parameter: arg,
                version: version,
	        callId: callId
	    }};
	    tcfapiCallbacks[callId] = callback;
	    cmpFrame.postMessage(msg, '*');
        }
    }

    /* when we get the return message, call the stashed callback */
    window.addEventListener("message", function(event) {
	var json;
	if (typeof event.data === "string") {
	    try {
		json = JSON.parse(event.data);
	    } catch {
		json = event.data;
	    }
	} else {
	    json = event.data;
	}
	if (json.__cmpReturn) {
	    var i = json.__cmpReturn;
	    if (i.callId in cmpCallbacks) {
		cmpCallbacks[i.callId](i.returnValue, i.success);
		delete cmpCallbacks[i.callId];
	    }
	} else if (json.__tcfapiReturn) {
	    var i = json.__tcfapiReturn;
	    if (i.callId in tcfapiCallbacks) {
		tcfapiCallbacks[i.callId](i.returnValue, i.success);
		delete tcfapiCallbacks[i.callId];
	    }
        }
    }, false);
    return 1;
}

function call_cmp(request, sender, sendResponse) {
    //console.log("requesting: " + request.call);
    if (request.call == "getTCData") { // v2
        if (!correct_frame_v2) {
            return;
        }
        __tcfapiCookieGlasses(request.call, 2, null, function(val, success) {
            if (success) {
                console.log("val: " + val);
	        if (val.TCData)
		    console.log("sc-probe-cmp-TCData:", val.TCData);
	        sendResponse({response: val});
            }
        });
    } else { // v1
        if (!correct_frame_v1) {
            return;
        }
        __cmpCookieGlasses(request.call, null, function(val, success) {
	    if (request.call == "getConsentData") {
	        if (val.metadata)
		    console.log("sc-probe-cmp-metadata:", val.metadata);
	        if (val.consentData)
		    console.log("sc-probe-cmp-consentData:", val.consentData);
	    } else {
	        if (val.metadata)
		    console.log("sc-probe-cmp-vendorConsents:", val.metadata);
	        if (val.consentData)
		    console.log("sc-probe-cmp-vendorConsents:", val.consentData);
	    }
	    sendResponse({response: val});
        });
    }
    return true;
}

correct_frame_v1 = setup_cmp_wrapper(1);
correct_frame_v2 = setup_cmp_wrapper(2);
if (correct_frame_v1 || correct_frame_v2) {
    api.runtime.onMessage.addListener(call_cmp);
}
