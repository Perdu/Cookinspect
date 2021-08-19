//console.log(window);

function find_cmpLocator(request, sender, sendResponse, frame_name) {
    // find the CMP frame
    var f = window;
    var cmpFrame;
    while(!cmpFrame) {
	try {
	    if(f.frames[frame_name]) {
		cmpFrame = f;
	    }
	} catch(e) {}
	if(f === window.top)
	    break;
	f = f.parent;
    }

    if (cmpFrame) {
	console.log(cmpFrame);
	sendResponse({response: frame_name + " found"});
    }
}

browser.runtime.onMessage.addListener(find_cmpLocator, "__cmpLocator");
browser.runtime.onMessage.addListener(find_cmpLocator, "__tcfapiLocator");
