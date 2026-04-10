package com.mobsec.companion

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Launcher activity — shows the companion server status, a start/stop toggle, and a live log.
 * Built entirely with standard Android Views so no extra dependencies are required.
 */
class MainActivity : Activity() {

    // ── Palette (GitHub Dark) ────────────────────────────────────────────────
    private val BG           = Color.parseColor("#0D1117")
    private val BG_CARD      = Color.parseColor("#161B22")
    private val BORDER       = Color.parseColor("#30363D")
    private val TEXT_PRIMARY = Color.parseColor("#C9D1D9")
    private val TEXT_MUTED   = Color.parseColor("#8B949E")
    private val ACCENT_BLUE  = Color.parseColor("#58A6FF")
    private val GREEN        = Color.parseColor("#3FB950")
    private val RED          = Color.parseColor("#F85149")
    private val BTN_GREEN    = Color.parseColor("#238636")
    private val BTN_RED      = Color.parseColor("#B62324")

    private lateinit var statusDot: TextView
    private lateinit var statusText: TextView
    private lateinit var portText: TextView
    private lateinit var toggleBtn: Button
    private lateinit var logView: TextView
    private lateinit var logScroll: ScrollView

    private val handler = Handler(Looper.getMainLooper())
    private val refreshLoop = object : Runnable {
        override fun run() {
            refreshUi()
            handler.postDelayed(this, 1_000)
        }
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        actionBar?.hide()
        window.decorView.setBackgroundColor(BG)
        setContentView(buildUi())
        handler.post(refreshLoop)
    }

    override fun onDestroy() {
        handler.removeCallbacks(refreshLoop)
        super.onDestroy()
    }

    // ── UI construction ──────────────────────────────────────────────────────

    private fun buildUi(): View {
        val root = vBox(BG, dp(20), dp(28), dp(20), dp(20))

        // Header
        root.addView(label("Maya Companion", 22f, ACCENT_BLUE, Typeface.BOLD))
        root.addView(label("Autonomous mobile security agent — on-device bridge", 13f, TEXT_MUTED).apply {
            setPadding(0, dp(2), 0, dp(20))
        })

        // Status card
        val card = vBox(BG_CARD, dp(16), dp(14), dp(16), dp(14)).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { it.bottomMargin = dp(16) }
        }

        // Status row
        val statusRow = hBox().apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, dp(8))
        }
        statusDot = label("●  ", 18f, TEXT_MUTED)
        statusText = label("Stopped", 15f, TEXT_MUTED, Typeface.BOLD)
        statusRow.addView(statusDot)
        statusRow.addView(statusText)
        card.addView(statusRow)

        // Port row
        portText = label("Port: ${defaultPort()}", 13f, TEXT_MUTED)
        card.addView(portText)

        root.addView(card)

        // Toggle button
        toggleBtn = Button(this).apply {
            text = "Start Service"
            textSize = 15f
            setTextColor(Color.WHITE)
            setBackgroundColor(BTN_GREEN)
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(48)
            ).also { it.bottomMargin = dp(20) }
            setOnClickListener { onToggle() }
        }
        root.addView(toggleBtn)

        // Divider + log header
        root.addView(divider())
        root.addView(label("Activity Log", 12f, TEXT_MUTED, Typeface.BOLD).apply {
            setPadding(0, dp(12), 0, dp(6))
        })

        // Log area
        logView = TextView(this).apply {
            textSize = 11.5f
            setTextColor(TEXT_PRIMARY)
            typeface = Typeface.MONOSPACE
            setPadding(dp(12), dp(10), dp(12), dp(10))
            setTextIsSelectable(true)
            text = "(no activity yet)"
        }
        logScroll = ScrollView(this).apply {
            setBackgroundColor(BG_CARD)
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
            ).also { it.topMargin = dp(2) }
            addView(logView)
        }
        root.addView(logScroll)

        return root
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    private fun onToggle() {
        val intent = Intent(this, CompanionService::class.java)
        if (CompanionHttpServer.isRunning()) {
            stopService(intent)
            CompanionLog.add("Service stopped by user")
        } else {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
            CompanionLog.add("Service start requested by user")
        }
        refreshUi()
    }

    // ── State refresh ─────────────────────────────────────────────────────────

    private fun refreshUi() {
        val running = CompanionHttpServer.isRunning()

        statusDot.setTextColor(if (running) GREEN else TEXT_MUTED)
        statusText.text  = if (running) "Running" else "Stopped"
        statusText.setTextColor(if (running) GREEN else TEXT_MUTED)
        portText.text    = if (running) "Port: ${defaultPort()}" else "Port: —"
        portText.setTextColor(if (running) TEXT_PRIMARY else TEXT_MUTED)

        toggleBtn.text = if (running) "Stop Service" else "Start Service"
        toggleBtn.setBackgroundColor(if (running) BTN_RED else BTN_GREEN)

        val lines = CompanionLog.snapshot()
        logView.text = if (lines.isEmpty()) "(no activity yet)" else lines.joinToString("\n")
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private fun vBox(bg: Int, l: Int, t: Int, r: Int, b: Int) = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(bg)
        setPadding(l, t, r, b)
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.MATCH_PARENT
        )
    }

    private fun hBox() = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        )
    }

    private fun label(text: String, size: Float, color: Int, style: Int = Typeface.NORMAL) =
        TextView(this).apply {
            this.text = text
            textSize = size
            setTextColor(color)
            if (style != Typeface.NORMAL) setTypeface(typeface, style)
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

    private fun divider() = View(this).apply {
        setBackgroundColor(BORDER)
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 1
        )
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}
