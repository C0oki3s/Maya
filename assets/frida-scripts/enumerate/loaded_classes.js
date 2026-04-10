/* loaded_classes.js — Enumerate all loaded Java classes, optionally filtered.
 * Usage: frida_run_script with this script.
 * Set FILTER below or pass via Frida params.
 */
'use strict';

var FILTER = ''; // e.g. 'com.target' — empty means list all

Java.perform(function () {
    Java.enumerateLoadedClasses({
        onMatch: function (className) {
            if (FILTER === '' || className.indexOf(FILTER) !== -1) {
                send({ type: 'class', name: className });
            }
        },
        onComplete: function () {
            send({ type: 'done', message: 'Class enumeration complete' });
        }
    });
});
