// Overrides __cmp()
// Alternative methods tested:
// - modifying window.__cmp directly (not inserting a script) : does not work
// - modifying window.__cmp using an event listener (https://stackoverflow.com/a/46888730/2678806) : does not work
// - using a mutation observer to override window.__cmp when inserted: not possible because window is not in the DOM
// - avoid event propagation of window.__cmp overriding announcement: same problem as above
// - using a mutation observer to avoid propagation of the event indicating the insertion of the inline script overriding __cmp(): I don't know how to identify the exact script, and I don't know if I can stop event propagation with this API

var api;
if (chrome == undefined) {
    api = browser;
} else {
    api = chrome;
}

function insert_override_cmp_js() {
    var newcmp = document.createElement("script");
    newcmp.setAttribute("type", "text/javascript");
    newcmp.setAttribute("async", true);
    newcmp.textContent = `Object.defineProperty(window, "__cmp", {
      value: function() {
        var stack = new Error().stack.split("\\n");
        if (stack.length < 2)
           return;
        var res = /\\((.*)\\)/.exec(stack[2]);
        if (res === null)
           return;
        var script_file = res[1];
        console.log("__cmp overriden and frozen. Caller: ", arguments[2].name, ", Arguments: ", arguments, ", file: ", script_file, ", full stack: ", stack);
        console.log("sc-script-file: " + script_file);
      },
      writable:false, configurable:false
    });
    console.log("__cmp overriding inserted");`;
    var head = document.head || document.getElementsByTagName("head")[0] || document.documentElement;
    head.insertBefore(newcmp, head.firstChild)
}

insert_override_cmp_js();

// I can overwrite __cmp to configure responses automatically
// I can identify callers of __cmp to get a list of 3rd party scripts verifing consent
// I CANNOT verify which answer is sent to __cmp callers (yet) because I can't detect when __cmp is overwritten

// https://c.amazon-adsystem.com/aax2/apstag.js seems to override __cmp and set its own response. There is something about BoundArgs I don't understand. In local storage: crfgL0cSt0r
