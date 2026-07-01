package com.click.shell;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.PopupWindow;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String PREFS = "ClickShellPrefs";
    private static final String KEY_HOST = "host";
    private static final String KEY_PORT = "port";
    private static final String KEY_HERMES_PORT = "hermes_port";
    private static final String KEY_DEVICE_ID = "device_id";
    private static final String KEY_ACCESS_TOKEN = "access_token";
    private static final String DEFAULT_PORT = "18180";
    private static final String DEFAULT_HERMES_PORT = "8765";
    private static final String DEFAULT_HOST = BuildConfig.CLICK_DEFAULT_HOST;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;
    private FrameLayout root;
    private WebView webView;
    private String baseUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            startShell();
        } catch (Throwable throwable) {
            showFatalError(throwable);
        }
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        if (webView != null) {
            try {
                webView.destroy();
            } catch (Throwable ignored) {
                // Keep shutdown best-effort; app exit should not crash.
            }
        }
        super.onDestroy();
    }

    private void startShell() {
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        hideSystemChrome();

        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(5, 5, 5));
        setContentView(root);

        String savedHost = prefs.getString(KEY_HOST, "");
        String savedPort = prefs.getString(KEY_PORT, DEFAULT_PORT);
        String savedHermesPort = prefs.getString(KEY_HERMES_PORT, DEFAULT_HERMES_PORT);
        ensureDeviceId();
        if (savedHost != null && !savedHost.trim().isEmpty()) {
            showConnectionView(savedHost, savedPort, savedHermesPort, accessToken(), "正在尝试上次连接...");
            connect(savedHost, savedPort, savedHermesPort, accessToken());
        } else if (!defaultHost().isEmpty()) {
            showConnectionView(defaultHost(), DEFAULT_PORT, savedHermesPort, accessToken(), "正在连接默认 Mac，可在右上角菜单里更换地址。");
            connect(defaultHost(), DEFAULT_PORT, savedHermesPort, accessToken());
        } else {
            showConnectionView("", DEFAULT_PORT, savedHermesPort, accessToken(), "");
        }
    }

    private void hideSystemChrome() {
        Window window = getWindow();
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.BLACK);
        window.getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
        );
    }

    private void showFatalError(Throwable throwable) {
        FrameLayout fallback = new FrameLayout(this);
        fallback.setBackgroundColor(Color.rgb(5, 5, 5));

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dpSafe(24), dpSafe(24), dpSafe(24), dpSafe(24));
        panel.setBackgroundColor(Color.rgb(7, 8, 6));

        TextView title = new TextView(this);
        title.setText("Click 启动失败");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        panel.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        TextView body = new TextView(this);
        body.setText("这版已经拦住了闪退。请把下面这行发给我，我继续修：\n\n" + compactError(throwable));
        body.setTextColor(Color.rgb(184, 184, 164));
        body.setTextSize(15);
        body.setPadding(0, dpSafe(16), 0, 0);
        panel.addView(body, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        fallback.addView(panel, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER
        ));
        setContentView(fallback);
    }

    private String compactError(Throwable throwable) {
        StringWriter writer = new StringWriter();
        throwable.printStackTrace(new PrintWriter(writer));
        String stack = writer.toString().trim();
        if (stack.length() > 900) {
            return stack.substring(0, 900);
        }
        return stack;
    }

    private void showConnectionView(String hostValue, String portValue, String hermesPortValue, String tokenValue, String messageValue) {
        root.removeAllViews();

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setGravity(Gravity.CENTER_HORIZONTAL);
        panel.setPadding(dp(28), dp(28), dp(28), dp(28));
        panel.setBackgroundColor(Color.rgb(7, 8, 6));

        TextView title = text("Click", 42, Color.WHITE);
        title.setGravity(Gravity.START);
        title.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        panel.addView(title, matchWrap());

        TextView subtitle = text("连接你的 Mac", 20, Color.rgb(184, 184, 164));
        subtitle.setPadding(0, dp(6), 0, dp(24));
        panel.addView(subtitle, matchWrap());

        EditText host = field("<mac-lan-ip>");
        String displayHost = (hostValue == null || hostValue.trim().isEmpty()) ? defaultHost() : hostValue;
        host.setText(displayHost);
        panel.addView(label("Mac 地址"));
        panel.addView(host, matchFixedHeight(54));

        EditText port = field(DEFAULT_PORT);
        port.setText((portValue == null || portValue.trim().isEmpty()) ? DEFAULT_PORT : portValue);
        port.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        panel.addView(label("Reader / Click 端口"));
        panel.addView(port, matchFixedHeight(54));

        EditText hermesPort = field(DEFAULT_HERMES_PORT);
        hermesPort.setText((hermesPortValue == null || hermesPortValue.trim().isEmpty()) ? DEFAULT_HERMES_PORT : hermesPortValue);
        hermesPort.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        panel.addView(label("Hermes 端口"));
        panel.addView(hermesPort, matchFixedHeight(54));

        EditText accessToken = field("approve 后的一次性 token");
        accessToken.setText(tokenValue == null ? "" : tokenValue);
        panel.addView(label("设备 token"));
        panel.addView(accessToken, matchFixedHeight(54));

        TextView device = text("设备 ID：" + ensureDeviceId(), 12, Color.rgb(130, 130, 118));
        device.setPadding(0, dp(8), 0, 0);
        panel.addView(device, matchWrap());

        Button connect = new Button(this);
        connect.setText("连接");
        connect.setAllCaps(false);
        connect.setOnClickListener(v -> connect(host.getText().toString(), port.getText().toString(), hermesPort.getText().toString(), accessToken.getText().toString()));
        LinearLayout.LayoutParams buttonParams = matchFixedHeight(52);
        buttonParams.setMargins(0, dp(20), 0, dp(12));
        panel.addView(connect, buttonParams);

        TextView message = text(messageValue == null ? "" : messageValue, 15, Color.rgb(184, 184, 164));
        message.setId(View.generateViewId());
        panel.addView(message, matchWrap());

        FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER
        );
        panelParams.setMargins(dp(24), 0, dp(24), 0);
        root.addView(panel, panelParams);
    }

    private void connect(String hostInput, String portInput, String hermesPortInput, String tokenInput) {
        String normalized = normalizeBaseUrl(hostInput, portInput);
        if (normalized == null) {
            showConnectionView(defaultHost(), portInput, hermesPortInput, tokenInput, "请输入 Mac 的局域网地址。");
            return;
        }
        showCheckingOverlay();
        executor.execute(() -> {
            boolean ok = checkHealth(normalized + "/health");
            runOnUiThread(() -> {
                if (ok) {
                    baseUrl = normalized;
                    prefs.edit()
                            .putString(KEY_HOST, hostInput.trim())
                            .putString(KEY_PORT, normalizePort(portInput))
                            .putString(KEY_HERMES_PORT, normalizePortWithDefault(hermesPortInput, DEFAULT_HERMES_PORT))
                            .putString(KEY_ACCESS_TOKEN, tokenInput == null ? "" : tokenInput.trim())
                            .apply();
                    showWebView(withAccessParams(normalized + "/home"));
                } else {
                    showConnectionView(hostInput, portInput, hermesPortInput, tokenInput, "没有连上 Click。请确认 Mac 已打开、同一 Wi-Fi、18180 正在运行，或在这里改 Mac 地址。");
                }
            });
        });
    }

    private void showCheckingOverlay() {
        ProgressBar progress = new ProgressBar(this);
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(dp(44), dp(44), Gravity.CENTER);
        root.addView(progress, params);
    }

    private boolean checkHealth(String healthUrl) {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(healthUrl).openConnection();
            connection.setConnectTimeout(5000);
            connection.setReadTimeout(5000);
            connection.setRequestMethod("GET");
            int code = connection.getResponseCode();
            return code >= 200 && code < 300;
        } catch (IOException ignored) {
            return false;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private void showWebView(String url) {
        root.removeAllViews();

        try {
            webView = new WebView(this);
        } catch (Throwable throwable) {
                showConnectionView(
                        prefs.getString(KEY_HOST, ""),
                        prefs.getString(KEY_PORT, DEFAULT_PORT),
                        prefs.getString(KEY_HERMES_PORT, DEFAULT_HERMES_PORT),
                        accessToken(),
                        "系统 WebView 启动失败。请确认 Android System WebView 或 Chrome 已启用。"
                );
            return;
        }
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setBackgroundColor(Color.BLACK);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request != null && request.isForMainFrame()) {
                    showConnectionView(
                            prefs.getString(KEY_HOST, ""),
                            prefs.getString(KEY_PORT, DEFAULT_PORT),
                            prefs.getString(KEY_HERMES_PORT, DEFAULT_HERMES_PORT),
                            accessToken(),
                            "页面加载失败，请检查 Mac 服务和网络。"
                    );
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                if (android.os.Build.VERSION.SDK_INT >= 23
                        && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1001);
                    request.deny();
                    return;
                }
                try {
                    request.grant(request.getResources());
                } catch (Throwable ignored) {
                    request.deny();
                }
            }
        });

        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        Button menu = new Button(this);
        menu.setText("⋯");
        menu.setAllCaps(false);
        menu.setTextSize(22);
        menu.setTextColor(Color.WHITE);
        menu.setBackgroundColor(Color.argb(96, 0, 0, 0));
        menu.setOnClickListener(v -> showShellMenu(menu));
        FrameLayout.LayoutParams menuParams = new FrameLayout.LayoutParams(dp(52), dp(52), Gravity.TOP | Gravity.END);
        menuParams.setMargins(0, dp(12), dp(12), 0);
        root.addView(menu, menuParams);

        webView.loadUrl(url);
    }

    private void showShellMenu(View anchor) {
        LinearLayout menu = new LinearLayout(this);
        menu.setOrientation(LinearLayout.VERTICAL);
        menu.setPadding(dp(14), dp(12), dp(14), dp(12));
        menu.setBackgroundColor(Color.rgb(18, 18, 18));

        TextView status = text(connectionLabel(), 13, Color.rgb(184, 184, 164));
        menu.addView(status, matchWrap());
        menu.addView(menuButton("首页", () -> webView.loadUrl(withAccessParams(baseUrl + "/home"))));
        menu.addView(menuButton("阅读", () -> webView.loadUrl(withAccessParams(baseUrl + "/library"))));
        menu.addView(menuButton("录音", () -> webView.loadUrl(withAccessParams(baseUrl + "/recordings"))));
        menu.addView(menuButton("Hermes", () -> webView.loadUrl(withAccessParams(baseUrl + "/hermes"))));
        menu.addView(menuButton("刷新", () -> webView.reload()));
        menu.addView(menuButton("更换地址", () -> showConnectionView(
                preferredHost(),
                prefs.getString(KEY_PORT, DEFAULT_PORT),
                prefs.getString(KEY_HERMES_PORT, DEFAULT_HERMES_PORT),
                accessToken(),
                ""
        )));

        PopupWindow popup = new PopupWindow(menu, dp(210), ViewGroup.LayoutParams.WRAP_CONTENT, true);
        popup.setOutsideTouchable(true);
        popup.showAsDropDown(anchor, -dp(140), 0);
    }

    private Button menuButton(String label, Runnable action) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        button.setOnClickListener(v -> action.run());
        return button;
    }

    private String connectionLabel() {
        if (baseUrl == null) {
            return "未连接";
        }
        Uri uri = Uri.parse(baseUrl);
        return "已连接 " + (uri.getHost() == null ? "Mac" : uri.getHost());
    }

    private String normalizeBaseUrl(String hostInput, String portInput) {
        if (hostInput == null || hostInput.trim().isEmpty()) {
            return null;
        }
        String raw = hostInput.trim();
        if (!raw.contains("://")) {
            raw = "http://" + raw;
        }
        Uri uri = Uri.parse(raw);
        String host = uri.getHost();
        if (host == null || host.trim().isEmpty()) {
            return null;
        }
        int port = uri.getPort() > 0 ? uri.getPort() : Integer.parseInt(normalizePort(portInput));
        return "http://" + host + ":" + port;
    }

    private String normalizePort(String portInput) {
        return normalizePortWithDefault(portInput, DEFAULT_PORT);
    }

    private String normalizePortWithDefault(String portInput, String fallback) {
        if (portInput == null || portInput.trim().isEmpty()) {
            return fallback;
        }
        try {
            int port = Integer.parseInt(portInput.trim());
            return port > 0 ? String.valueOf(port) : fallback;
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private String defaultHost() {
        return DEFAULT_HOST == null ? "" : DEFAULT_HOST.trim();
    }

    private String ensureDeviceId() {
        String existing = prefs.getString(KEY_DEVICE_ID, "");
        if (existing != null && !existing.trim().isEmpty()) {
            return existing.trim();
        }
        String created = "android-" + UUID.randomUUID().toString();
        prefs.edit().putString(KEY_DEVICE_ID, created).apply();
        return created;
    }

    private String accessToken() {
        String token = prefs.getString(KEY_ACCESS_TOKEN, "");
        return token == null ? "" : token.trim();
    }

    private String withAccessParams(String url) {
        Uri.Builder builder = Uri.parse(url).buildUpon();
        builder.appendQueryParameter("device_id", ensureDeviceId());
        builder.appendQueryParameter("device_name", "Android Click");
        String token = accessToken();
        if (!token.isEmpty()) {
            builder.appendQueryParameter("access_token", token);
        }
        return builder.build().toString();
    }

    private String preferredHost() {
        String saved = prefs.getString(KEY_HOST, "");
        if (saved != null && !saved.trim().isEmpty()) {
            return saved;
        }
        return defaultHost();
    }

    private TextView label(String value) {
        TextView view = text(value, 14, Color.rgb(184, 184, 164));
        view.setPadding(0, dp(14), 0, dp(6));
        return view;
    }

    private EditText field(String hint) {
        EditText editText = new EditText(this);
        editText.setHint(hint);
        editText.setSingleLine(true);
        editText.setTextColor(Color.WHITE);
        editText.setHintTextColor(Color.rgb(130, 130, 118));
        editText.setBackgroundColor(Color.rgb(30, 32, 26));
        editText.setPadding(dp(12), 0, dp(12), 0);
        return editText;
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
    }

    private LinearLayout.LayoutParams matchFixedHeight(int heightDp) {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(heightDp)
        );
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }

    private int dpSafe(int value) {
        try {
            return dp(value);
        } catch (Throwable ignored) {
            return value;
        }
    }
}
