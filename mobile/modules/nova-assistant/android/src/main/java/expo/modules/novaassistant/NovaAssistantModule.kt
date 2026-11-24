package expo.modules.novaassistant

import android.app.role.RoleManager
import android.content.Intent
import android.os.Build
import expo.modules.kotlin.Promise
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import org.json.JSONObject

class NovaAssistantModule : Module() {
    override fun definition() = ModuleDefinition {
        Name("NovaAssistant")

        AsyncFunction("listen") { promise: Promise ->
            val context = appContext.reactContext ?: return@AsyncFunction promise.reject("NO_CONTEXT", "No Android context", null)
            NovaSpeech.listenOnce(context, { text -> promise.resolve(mapOf("text" to text)) }, { error -> promise.reject("LISTEN", error, null) })
        }

        AsyncFunction("perform") { request: String, promise: Promise ->
            val context = appContext.reactContext ?: return@AsyncFunction promise.reject("NO_CONTEXT", "No Android context", null)
            val (ok, detail) = PhoneActions.perform(context, JSONObject(request))
            promise.resolve(mapOf("ok" to ok, "detail" to detail))
        }

        AsyncFunction("speak") { text: String, language: String, promise: Promise ->
            val context = appContext.reactContext ?: return@AsyncFunction promise.reject("NO_CONTEXT", "No Android context", null)
            NovaSpeech.speak(context, text, language) { available ->
                promise.resolve(mapOf("ok" to available, "turkishVoice" to (language != "tr" || available)))
            }
        }

        AsyncFunction("requestAssistant") { promise: Promise ->
            val context = appContext.reactContext ?: return@AsyncFunction promise.reject("NO_CONTEXT", "No Android context", null)
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
                promise.resolve(mapOf("ok" to false))
                return@AsyncFunction
            }
            val roles = context.getSystemService(RoleManager::class.java)
            if (!roles.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) {
                promise.resolve(mapOf("ok" to false))
                return@AsyncFunction
            }
            if (!roles.isRoleHeld(RoleManager.ROLE_ASSISTANT)) {
                val intent = roles.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
            }
            promise.resolve(mapOf("ok" to true))
        }

        AsyncFunction("setBackgroundListening") { enabled: Boolean, promise: Promise ->
            val context = appContext.reactContext ?: return@AsyncFunction promise.reject("NO_CONTEXT", "No Android context", null)
            val intent = Intent(context, NovaListenService::class.java)
            if (!enabled) {
                context.stopService(intent)
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
            promise.resolve(mapOf("ok" to true))
        }

        AsyncFunction("installTurkishVoice") { promise: Promise ->
            val context = appContext.reactContext ?: return@AsyncFunction promise.reject("NO_CONTEXT", "No Android context", null)
            NovaSpeech.installTurkishVoice(context)
            promise.resolve(mapOf("ok" to true))
        }
    }
}
