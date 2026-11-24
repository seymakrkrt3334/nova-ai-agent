package expo.modules.novaassistant

import android.app.Notification
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.service.voice.VoiceInteractionService
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService
import androidx.core.app.NotificationCompat

class NovaAssistantService : VoiceInteractionService()

class NovaSessionService : VoiceInteractionSessionService() {
    override fun onNewSession(args: Bundle?): VoiceInteractionSession = NovaSession(this)
}

class NovaSession(context: Context) : VoiceInteractionSession(context) {
    override fun onShow(args: Bundle?, showFlags: Int) {
        super.onShow(args, showFlags)
        NovaSpeech.listenOnce(context, { text ->
            val action = CommandParser.interpret(text)
            if (action.optString("status") == "ready" && action.optString("type") != "chat" && action.optString("type") != "wake") {
                PhoneActions.perform(context, action)
            }
            hide()
        }, { hide() })
    }
}

class NovaListenService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private var running = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        ensureChannel(this)
        val notification: Notification = NotificationCompat.Builder(this, "nova-listen")
            .setContentTitle("NOVA")
            .setContentText("Dinleme açık. Ses kaydı yüklenmez.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(41, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(41, notification)
        }
        running = true
        listenBurst()
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private fun listenBurst() {
        if (!running) return
        NovaSpeech.listenOnce(this, { text ->
            val folded = text.lowercase()
            if (folded.contains("nova") || CommandParser.pending != null) {
                val action = CommandParser.interpret(text)
                if (action.optString("status") == "ready" && action.optString("type") !in setOf("chat", "wake", "cancel")) {
                    PhoneActions.perform(this, action)
                }
            }
            handler.postDelayed({ listenBurst() }, 1500)
        }, { error ->
            if (error == "recognizer-5" || error == "recognizer-9" || error == "recognizer-unavailable") {
                stopSelf()
            } else {
                handler.postDelayed({ listenBurst() }, 1500)
            }
        })
    }
}

class NovaReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        ensureChannel(context)
        val text = intent.getStringExtra("text") ?: "NOVA"
        val notification = NotificationCompat.Builder(context, "nova-listen")
            .setContentTitle("NOVA")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()
        val manager = context.getSystemService(android.app.NotificationManager::class.java)
        manager.notify(text.hashCode(), notification)
    }
}
