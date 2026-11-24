package expo.modules.novaassistant

import org.json.JSONObject

object CommandParser {
    var pending: JSONObject? = null

    fun interpret(utterance: String): JSONObject {
        val language = if (utterance.any { it in "çğıöşüÇĞİÖŞÜ" } || utterance.lowercase().contains(" ara") || utterance.lowercase().contains("annem") || utterance.lowercase().contains("babam")) "tr" else "en"
        val text = utterance.lowercase().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')
        val rest = text.removePrefix("hey nova").removePrefix("hi nova").removePrefix("nova").trim()
        val command = if (text.startsWith("hey nova") || text.startsWith("hi nova") || text.startsWith("nova")) rest else text
        val waiting = pending
        if (waiting != null && (command == "evet" || command == "yes" || command == "confirm" || command == "hemen ara" || command == "place the call")) {
            val immediate = command == "hemen ara" || command == "place the call"
            pending = null
            return JSONObject(waiting.toString())
                .put("status", "ready")
                .put("placesCall", immediate && waiting.optString("type") == "call")
                .put("delivery", if (waiting.optString("type") == "whatsapp") "compose" else if (immediate) "call" else "dial")
        }
        if (waiting != null && (command == "hayir" || command == "no" || command == "cancel" || command == "iptal")) {
            pending = null
            return JSONObject().put("type", "cancel").put("status", "cancelled").put("language", language)
        }
        val relation = when {
            listOf("annemi", "annemin", "annem", "anne", "mom", "mother").any { command.contains(it) } -> "anne"
            listOf("babami", "babamin", "babam", "baba", "dad", "father").any { command.contains(it) } -> "baba"
            else -> ""
        }
        val result = JSONObject().put("language", language).put("status", "ready").put("placesCall", false)
        if (relation.isNotEmpty() && command.contains("whatsapp")) {
            pending = result.put("type", "whatsapp").put("status", "confirmation_required").put("relation", relation).put("message", command)
            return result
        }
        if (relation.isNotEmpty() && (command.contains(" ara") || command.startsWith("ara") || command.contains("call"))) {
            pending = result.put("type", "call").put("status", "confirmation_required").put("relation", relation)
            return result
        }
        val apps = mapOf(
            "instagram" to "com.instagram.android",
            "whatsapp" to "com.whatsapp",
            "phone" to "com.android.dialer",
            "telefon" to "com.android.dialer",
        )
        val app = apps.entries.firstOrNull { command.contains(it.key) }
        if (app != null && (command.contains("open") || command.contains(" ac") || command.startsWith("ac "))) {
            return result.put("type", "launch").put("packageName", app.value)
        }
        if (command.contains("alarm")) {
            val clock = Regex("(\\d{1,2})(?::(\\d{2}))?").find(command)
            val hour = clock?.groupValues?.get(1)?.toIntOrNull() ?: 7
            val minute = clock?.groupValues?.get(2)?.toIntOrNull() ?: 0
            return result.put("type", "alarm").put("hour", hour.coerceIn(0, 23)).put("minute", minute.coerceIn(0, 59))
        }
        if (command.contains("timer") || command.contains("dakika") || command.contains("zamanlayici")) {
            val amount = Regex("(\\d+)").find(command)?.groupValues?.get(1)?.toIntOrNull() ?: 1
            val seconds = if (command.contains("saniye") || command.contains("second")) amount else amount * 60
            return result.put("type", "timer").put("seconds", seconds)
        }
        if (command.contains("hatirlat") || command.contains("remind")) {
            return result.put("type", "reminder").put("message", command).put("dayOffset", if (command.contains("yarin") || command.contains("tomorrow")) 1 else 0)
        }
        if (command.isBlank()) return result.put("type", "wake")
        return result.put("type", "chat")
    }
}
