package expo.modules.novaassistant

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import java.util.Locale

object NovaSpeech {
    fun listenOnce(context: Context, onResult: (String) -> Unit, onError: (String) -> Unit) {
        Handler(Looper.getMainLooper()).post {
            if (!SpeechRecognizer.isRecognitionAvailable(context)) {
                onError("recognizer-unavailable")
                return@post
            }
            val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
            recognizer.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) = Unit
                override fun onBeginningOfSpeech() = Unit
                override fun onRmsChanged(rmsdB: Float) = Unit
                override fun onBufferReceived(buffer: ByteArray?) = Unit
                override fun onEndOfSpeech() = Unit
                override fun onPartialResults(partialResults: Bundle?) = Unit
                override fun onEvent(eventType: Int, params: Bundle?) = Unit
                override fun onError(error: Int) {
                    recognizer.destroy()
                    onError("recognizer-$error")
                }
                override fun onResults(results: Bundle?) {
                    val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                    recognizer.destroy()
                    if (text.isBlank()) onError("empty") else onResult(text)
                }
            })
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                .putExtra("android.speech.extra.ENABLE_LANGUAGE_DETECTION", true)
                .putExtra("android.speech.extra.LANGUAGE_DETECTION_ALLOWED_LANGUAGES", arrayOf("tr-TR", "en-US"))
            recognizer.startListening(intent)
        }
    }

    fun speak(context: Context, text: String, language: String, done: (Boolean) -> Unit) {
        val locale = if (language == "en") Locale.US else Locale.forLanguageTag("tr-TR")
        lateinit var engine: TextToSpeech
        engine = TextToSpeech(context) { status ->
            if (status != TextToSpeech.SUCCESS) {
                done(false)
                return@TextToSpeech
            }
            val available = engine.setLanguage(locale) >= TextToSpeech.LANG_AVAILABLE
            if (available) engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nova")
            done(available)
        }
    }

    fun installTurkishVoice(context: Context) {
        val intent = Intent(TextToSpeech.Engine.ACTION_INSTALL_TTS_DATA).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }
}
