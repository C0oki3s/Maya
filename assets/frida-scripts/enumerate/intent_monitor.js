/* intent_monitor.js — Hook Android Intent dispatch to log all intents.
 * Attach to a running app to observe IPC flow.
 */
'use strict';

Java.perform(function () {
    var Intent = Java.use('android.content.Intent');
    var Activity = Java.use('android.app.Activity');

    Activity.startActivity.overload('android.content.Intent').implementation = function (intent) {
        send({
            type: 'intent',
            action: intent.getAction() ? intent.getAction().toString() : 'null',
            data: intent.getDataString() ? intent.getDataString().toString() : 'null',
            component: intent.getComponent() ? intent.getComponent().toString() : 'null',
            extras: intent.getExtras() ? intent.getExtras().toString() : 'null'
        });
        this.startActivity(intent);
    };

    var ContextWrapper = Java.use('android.content.ContextWrapper');
    ContextWrapper.sendBroadcast.overload('android.content.Intent').implementation = function (intent) {
        send({
            type: 'broadcast',
            action: intent.getAction() ? intent.getAction().toString() : 'null',
            data: intent.getDataString() ? intent.getDataString().toString() : 'null'
        });
        this.sendBroadcast(intent);
    };

    send({ type: 'ready', message: 'Intent monitor hooks active' });
});
