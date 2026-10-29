package com.tvfreedom.launcher

import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.StateListDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Minimal TV-first home screen. Source preview; compile and validate on target hardware before release. */
class MainActivity : Activity() {
    private val bgColor = Color.rgb(11, 16, 32)
    private val cardColor = Color.rgb(26, 36, 58)
    private val accentColor = Color.rgb(125, 211, 252)

    @Suppress("DEPRECATION")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bgColor
        window.navigationBarColor = bgColor
        renderHome()
    }

    override fun onResume() {
        super.onResume()
        if (findViewById<View>(ROOT_ID) != null) renderHome()
    }

    private fun renderHome() {
        val pm = packageManager
        val density = resources.displayMetrics.density
        val cornerRadius = 8f * density
        val strokeWidth = (2 * density).toInt()
        val iconSize = (32 * density).toInt()
        val drawablePadding = (12 * density).toInt()

        val normalDrawable = GradientDrawable().apply {
            setColor(cardColor)
            setCornerRadius(cornerRadius)
        }
        val focusedDrawable = GradientDrawable().apply {
            setColor(Color.rgb(40, 56, 88))
            setStroke(strokeWidth, accentColor)
            setCornerRadius(cornerRadius)
        }
        val buttonBackground = StateListDrawable().apply {
            addState(intArrayOf(android.R.attr.state_focused), focusedDrawable)
            addState(intArrayOf(), normalDrawable)
        }

        val root = LinearLayout(this).apply {
            id = ROOT_ID
            orientation = LinearLayout.VERTICAL
            setPadding(48, 28, 48, 24)
            setBackgroundColor(bgColor)
        }
        val title = TextView(this).apply {
            text = "TV Freedom"
            textSize = 32f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(Color.WHITE)
        }
        val subtitle = TextView(this).apply {
            text = "Your TV. Your home screen."
            textSize = 16f
            setTextColor(accentColor)
            setPadding(0, 4, 0, 20)
        }
        val scroll = ScrollView(this)
        val grid = GridLayout(this).apply {
            columnCount = 5
            useDefaultMargins = true
        }
        val apps = loadLaunchableApps()
        if (apps.isEmpty()) {
            grid.addView(TextView(this).apply {
                text = "No launchable apps found. Open Settings to review installed apps."
                textSize = 18f
                setTextColor(Color.WHITE)
                setPadding(20, 20, 20, 20)
            })
        } else {
            apps.forEach { app ->
                val appLabel = app.loadLabel(pm).toString()
                val pkgName = app.activityInfo.packageName
                val launchButton = Button(this).apply {
                    text = appLabel
                    textSize = 15f
                    isAllCaps = false
                    setTextColor(Color.WHITE)
                    background = buttonBackground
                    isFocusable = true
                    isFocusableInTouchMode = true
                    minHeight = 104
                    setPadding(16, 16, 16, 16)
                    contentDescription = "Open $appLabel"

                    val icon = app.loadIcon(pm)
                    if (icon != null) {
                        icon.setBounds(0, 0, iconSize, iconSize)
                        setCompoundDrawables(icon, null, null, null)
                        compoundDrawablePadding = drawablePadding
                    }

                    setOnClickListener {
                        try {
                            val launch = pm.getLeanbackLaunchIntentForPackage(pkgName)
                                ?: pm.getLaunchIntentForPackage(pkgName)
                            if (launch != null) startActivity(launch)
                        } catch (_: Exception) { }
                    }
                }
                grid.addView(launchButton, GridLayout.LayoutParams().apply {
                    width = 0
                    height = GridLayout.LayoutParams.WRAP_CONTENT
                    columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f)
                    setMargins(8, 8, 8, 8)
                })
            }
        }
        scroll.addView(grid)
        root.addView(title)
        root.addView(subtitle)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        val footer = TextView(this).apply {
            text = "Preview launcher • Press Home to choose your default launcher in Android settings"
            textSize = 12f
            setTextColor(Color.LTGRAY)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 14, 0, 0)
        }
        root.addView(footer)
        setContentView(root)
    }

    private fun loadLaunchableApps(): List<android.content.pm.ResolveInfo> {
        val pm = packageManager
        val leanback = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LEANBACK_LAUNCHER)
        val standard = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val results = (pm.queryIntentActivities(leanback, PackageManager.MATCH_ALL) +
            pm.queryIntentActivities(standard, PackageManager.MATCH_ALL))
            .filter { it.activityInfo.packageName != packageName }
            .distinctBy { "${it.activityInfo.packageName}/${it.activityInfo.name}" }
            .sortedBy { it.loadLabel(pm).toString().lowercase() }
        return results
    }

    companion object { private const val ROOT_ID = 98765 }
}
