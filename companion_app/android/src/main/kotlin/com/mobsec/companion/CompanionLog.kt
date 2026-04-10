package com.mobsec.companion

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Thread-safe in-memory log buffer shared between [CompanionHttpServer] and [MainActivity].
 * Newest entries are at index 0. Capped at MAX_ENTRIES to avoid unbounded growth.
 */
object CompanionLog {
    private const val MAX_ENTRIES = 100
    private val entries = ArrayDeque<String>(MAX_ENTRIES)
    private val lock = Any()
    private val fmt = SimpleDateFormat("HH:mm:ss", Locale.US)

    fun add(line: String) {
        val stamped = "${fmt.format(Date())}  $line"
        synchronized(lock) {
            entries.addFirst(stamped)
            while (entries.size > MAX_ENTRIES) entries.removeLast()
        }
    }

    fun snapshot(): List<String> = synchronized(lock) { entries.toList() }

    fun clear() = synchronized(lock) { entries.clear() }
}
