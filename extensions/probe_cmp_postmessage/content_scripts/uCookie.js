var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function setup_cmp_wrapper() {
    // find the CMP frame
    var f = window;
    var cmpFrame;
    while(!cmpFrame) {
	try {
	    if(f.frames["__cmpLocator"]) {
		cmpFrame = f;
	    }
	} catch(e) {}
	if(f === window.top)
	    break;
	f = f.parent;
    }
    if (!cmpFrame) {
	return 0;
    }
    //console.log("__cmpLocator found. Origin:", window.origin, cmpFrame);

    var cmpCallbacks = {}

    /* Set up a __cmp function to do the postMessage and 
       stash the callback.
       This function behaves (from the caller's perspective)
       identically to the in-frame __cmp call */

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
	if(json.__cmpReturn) {
	    var i = json.__cmpReturn;
	    if (i.callId in cmpCallbacks) {
		cmpCallbacks[i.callId](i.returnValue, i.success);
		delete cmpCallbacks[i.callId];
	    }
	}
    }, false);
    return 1;
}

function call_cmp(request, sender, sendResponse) {
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
    return true;
}

var correct_frame = setup_cmp_wrapper();
if (correct_frame) {
    api.runtime.onMessage.addListener(call_cmp);
}
