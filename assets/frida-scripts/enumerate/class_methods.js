/* class_methods.js — List all declared methods for a given Java class.
 * Set TARGET_CLASS before running.
 */
'use strict';

var TARGET_CLASS = 'REPLACE_ME'; // e.g. 'com.target.AuthManager'

Java.perform(function () {
    try {
        var cls = Java.use(TARGET_CLASS);
        var methods = cls.class.getDeclaredMethods();
        methods.forEach(function (m) {
            send({ type: 'method', class: TARGET_CLASS, signature: m.toString() });
        });
        send({ type: 'done', message: 'Enumerated ' + methods.length + ' methods' });
    } catch (e) {
        send({ type: 'error', message: 'Failed to enumerate: ' + e.message });
    }
});
