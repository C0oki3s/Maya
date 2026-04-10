/* native_exports.js — Enumerate exported symbols from native libraries.
 * Set LIB_NAME to filter a specific library or leave empty for all.
 */
'use strict';

var LIB_NAME = ''; // e.g. 'libnative-lib.so'

Process.enumerateModules()
    .filter(function (m) {
        return LIB_NAME === '' || m.name.indexOf(LIB_NAME) !== -1;
    })
    .forEach(function (mod) {
        mod.enumerateExports().forEach(function (exp) {
            send({
                type: 'export',
                module: mod.name,
                name: exp.name,
                address: exp.address.toString()
            });
        });
    });

send({ type: 'done', message: 'Native export enumeration complete' });
