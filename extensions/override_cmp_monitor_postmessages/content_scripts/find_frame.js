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
	console.log("I found the __cmpLocator frame!");
	console.log(cmpFrame);
	sendResponse({response: "__cmpLocator found"});
    }

    if (window.frames["__cmpLocator"]) {
	console.log("I'm the __cmpLocator frame!");
    }
}

browser.runtime.onMessage.addListener(find_cmpLocator);
