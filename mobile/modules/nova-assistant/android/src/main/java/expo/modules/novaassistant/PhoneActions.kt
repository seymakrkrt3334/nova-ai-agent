package expo.modules.novaassistant

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.AlarmClock
import android.provider.ContactsContract
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.util.Calendar

object PhoneActions {
    fun perform(context: Context, request: JSONObject): Pair<Boolean, String> {
        val type = request.optString("type")
        val status = request.optString("status")
        if ((type == "call" || type == "whatsapp") && status != "ready") {
            return false to "confirmation"
        }
        return when (type) {
            "call" -> call(context, request)
            "whatsapp" -> whatsapp(context, request)
            "launch" -> launch(context, request.optString("packageName"))
            "alarm" -> alarm(context, request.optInt("hour"), request.optInt("minute"))
            "timer" -> timer(context, request.optInt("seconds"))
            "reminder" -> reminder(context, request)
            else -> true to "ignored"
        }
    }

    private fun numberFor(context: Context, relation: String): String? {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) {
            return null
        }
        val aliases = if (relation == "anne") {
            listOf("anne", "annem", "annemi", "mom", "mother")
        } else {
            listOf("baba", "babam", "babami", "dad", "father")
        }
        val cursor = context.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            arrayOf(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME, ContactsContract.CommonDataKinds.Phone.NUMBER),
            null,
            null,
            null,
        ) ?: return null
        cursor.use {
            val nameIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            val numberIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
            while (it.moveToNext()) {
                val name = it.getString(nameIndex).orEmpty().lowercase()
                val tokens = name.split(Regex("\\W+")).filter { token -> token.isNotEmpty() }
                val matched = aliases.any { alias ->
                    tokens.any { token -> token == alias || token == alias + "m" || token == alias + "i" || token == alias + "im" }
                }
                if (matched) {
                    return it.getString(numberIndex)?.filter { char -> char.isDigit() || char == '+' }
                }
            }
        }
        return null
    }

    private fun call(context: Context, request: JSONObject): Pair<Boolean, String> {
        val number = numberFor(context, request.optString("relation")) ?: return false to "contact-not-found"
        val place = request.optBoolean("placesCall")
        val permitted = ContextCompat.checkSelfPermission(context, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED
        val action = if (place && permitted) Intent.ACTION_CALL else Intent.ACTION_DIAL
        val intent = Intent(action, Uri.parse("tel:$number")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try {
            context.startActivity(intent)
            true to if (action == Intent.ACTION_CALL) "call" else "dial"
        } catch (_: SecurityException) {
            context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$number")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            true to "dial"
        }
    }

    private fun whatsapp(context: Context, request: JSONObject): Pair<Boolean, String> {
        val number = numberFor(context, request.optString("relation")) ?: return false to "contact-not-found"
        val digits = number.filter { it.isDigit() }
        val text = Uri.encode(request.optString("message"))
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/$digits?text=$text")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        intent.setPackage("com.whatsapp")
        if (intent.resolveActivity(context.packageManager) == null) return false to "whatsapp-not-installed"
        context.startActivity(intent)
        return true to "compose"
    }

    private fun launch(context: Context, packageName: String): Pair<Boolean, String> {
        val intent = context.packageManager.getLaunchIntentForPackage(packageName) ?: return false to "app-not-installed"
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
        return true to "launch"
    }

    private fun alarm(context: Context, hour: Int, minute: Int): Pair<Boolean, String> {
        val intent = Intent(AlarmClock.ACTION_SET_ALARM)
            .putExtra(AlarmClock.EXTRA_HOUR, hour)
            .putExtra(AlarmClock.EXTRA_MINUTES, minute)
            .putExtra(AlarmClock.EXTRA_SKIP_UI, false)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
        return true to "alarm"
    }

    private fun timer(context: Context, seconds: Int): Pair<Boolean, String> {
        val intent = Intent(AlarmClock.ACTION_SET_TIMER)
            .putExtra(AlarmClock.EXTRA_LENGTH, seconds)
            .putExtra(AlarmClock.EXTRA_SKIP_UI, false)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
        return true to "timer"
    }

    private fun reminder(context: Context, request: JSONObject): Pair<Boolean, String> {
        val calendar = Calendar.getInstance()
        val hour = request.optInt("hour", calendar.get(Calendar.HOUR_OF_DAY))
        val minute = request.optInt("minute", calendar.get(Calendar.MINUTE))
        calendar.set(Calendar.HOUR_OF_DAY, hour)
        calendar.set(Calendar.MINUTE, minute)
        calendar.set(Calendar.SECOND, 0)
        calendar.add(Calendar.DAY_OF_YEAR, request.optInt("dayOffset"))
        if (calendar.timeInMillis < System.currentTimeMillis()) calendar.add(Calendar.DAY_OF_YEAR, 1)
        val intent = Intent(context, NovaReminderReceiver::class.java).putExtra("text", request.optString("message"))
        val pending = PendingIntent.getBroadcast(
            context,
            calendar.timeInMillis.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val alarmManager = context.getSystemService(AlarmManager::class.java)
        alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, calendar.timeInMillis, pending)
        return true to "reminder"
    }
}

fun ensureChannel(context: Context) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
    val manager = context.getSystemService(NotificationManager::class.java)
    val channel = NotificationChannel("nova-listen", "NOVA", NotificationManager.IMPORTANCE_LOW)
    channel.description = "NOVA listens only while this notification is visible."
    manager.createNotificationChannel(channel)
}
