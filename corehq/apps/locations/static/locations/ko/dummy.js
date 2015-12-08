// define([], function() {
define(["jquery", "underscore"], function($, _) {
    var module = {};

    console.log("jquery?", $);
    console.log("underscore?", _);

    module.say_hi = function(name) {
        console.log("hello, " + name + "!");
    };

    module.update_text = function(new_text) {
        console.log($('#foo').text(new_text));
    };

    return module;
});
