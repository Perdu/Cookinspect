//console.log(window);

function find_cmpLocator(request, sender, sendResponse) {
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

    if (cmpFrame) {
	console.log(cmpFrame);
	sendResponse({response: "__cmpLocator found"});
    }
}

browser.runtime.onMessage.addListener(find_cmpLocator);
