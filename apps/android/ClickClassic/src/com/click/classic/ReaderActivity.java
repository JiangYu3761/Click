package com.click.classic;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.graphics.*;
import android.graphics.drawable.*;
import android.net.Uri;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.text.*;
import android.text.style.*;
import android.view.*;
import android.widget.*;
import com.click.shell.EpubOfflineIndexer;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.*;
import java.util.zip.*;

public final class ReaderActivity extends Activity {
  private final ExecutorService worker = Executors.newSingleThreadExecutor();
  private Library db;
  private LinearLayout root, bar;
  private FrameLayout body;
  private TextView heading, counter, text;
  private ScrollView scroll;
  private String book, name, kind, password;
  private List<String> chapters = Collections.emptyList();
  private int page, count, savedOffset, generation;
  private boolean fitWidth, textMode, ttsReady;
  private TextToSpeech speaker;
  private String pendingSpeech;
  private static final Pattern WORD = Pattern.compile("[A-Za-z]+(?:['’-][A-Za-z]+)*");

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    db = new Library(this);
    fitWidth = getPreferences(0).getBoolean("fitWidth", false);
    textMode = getPreferences(0).getBoolean("textMode", false);
    shelf();
    if (state != null && state.getString("book") != null) open(state.getString("book"));
    else if (state == null
        && Intent.ACTION_VIEW.equals(getIntent().getAction())
        && getIntent().getData() != null) receive(getIntent().getData());
  }

  @Override
  protected void onSaveInstanceState(Bundle state) {
    super.onSaveInstanceState(state);
    state.putString("book", book);
  }

  @Override
  protected void onPause() {
    super.onPause();
    save();
    if (speaker != null) speaker.stop();
  }

  @Override
  protected void onDestroy() {
    generation++;
    worker.shutdown();
    if (speaker != null) speaker.shutdown();
    super.onDestroy();
  }

  @Override
  public void onBackPressed() {
    if (book == null) super.onBackPressed();
    else shelf();
  }

  private int dp(int value) {
    return Math.round(value * getResources().getDisplayMetrics().density);
  }

  private LinearLayout row() {
    LinearLayout v = new LinearLayout(this);
    v.setGravity(Gravity.CENTER_VERTICAL);
    return v;
  }

  private void button(LinearLayout parent, String title, Runnable action) {
    Button b = new Button(this);
    b.setText(title);
    b.setTextSize(15);
    b.setMinWidth(0);
    b.setMinimumWidth(0);
    b.setPadding(dp(10), 0, dp(10), 0);
    b.setOnClickListener(v -> action.run());
    parent.addView(b, -2, dp(44));
  }

  private void frame(String title) {
    root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setBackgroundColor(0xfffaf8f2);
    bar = row();
    root.addView(bar, -1, dp(48));
    heading = new TextView(this);
    heading.setTextSize(18);
    heading.setSingleLine(true);
    heading.setEllipsize(TextUtils.TruncateAt.END);
    heading.setPadding(dp(10), 0, dp(5), 0);
    heading.setTextColor(0xff252823);
    heading.setText(title);
    bar.addView(heading, new LinearLayout.LayoutParams(0, -2, 1));
    body = new FrameLayout(this);
    root.addView(body, new LinearLayout.LayoutParams(-1, 0, 1));
    setContentView(root);
  }

  private void shelf() {
    save();
    generation++;
    book = null;
    text = null;
    scroll = null;
    password = null;
    if (speaker != null) speaker.stop();
    frame("Click 书库");
    button(bar, "打开文件", this::pick);
    List<String> names = new ArrayList<>(), ids = new ArrayList<>();
    Cursor c =
        db.getReadableDatabase()
            .rawQuery("SELECT id,name,kind,page FROM books ORDER BY opened DESC,rowid DESC", null);
    try {
      while (c.moveToNext()) {
        ids.add(c.getString(0));
        names.add(c.getString(1) + "\n" + c.getString(2) + "  ·  " + (c.getInt(3) + 1));
      }
    } finally {
      c.close();
    }
    if (ids.isEmpty()) {
      message("打开本机的 PDF 或 EPUB 开始阅读");
      return;
    }
    ListView list = new ListView(this);
    list.setAdapter(new ArrayAdapter<String>(this, android.R.layout.simple_list_item_1, names));
    list.setOnItemClickListener((p, v, i, id) -> open(ids.get(i)));
    body.addView(list);
  }

  private void pick() {
    Intent i = new Intent(Intent.ACTION_GET_CONTENT);
    i.setType("*/*");
    i.addCategory(Intent.CATEGORY_OPENABLE);
    if (android.os.Build.VERSION.SDK_INT <= 18) {
      File storage = android.os.Environment.getExternalStorageDirectory();
      if (i.resolveActivity(getPackageManager()) == null) browse(storage, storage);
      else
        new AlertDialog.Builder(this)
            .setTitle("打开文件")
            .setItems(
                new String[] {"本机文件", "使用文件管理器"},
                (d, index) -> {
                  if (index == 0) browse(storage, storage);
                  else systemPicker(i);
                })
            .show();
    } else systemPicker(i);
  }

  private void systemPicker(Intent intent) {
    try {
      startActivityForResult(Intent.createChooser(intent, "选择 PDF 或 EPUB"), 1);
    } catch (ActivityNotFoundException ex) {
      alert("请使用文件管理器打开 PDF 或 EPUB，并选择 Click。");
    }
  }

  private void browse(File rootDir, File dir) {
    File[] files =
        dir.listFiles(
            f -> {
              String n = f.getName().toLowerCase(Locale.US);
              return !f.isHidden()
                  && (f.isDirectory() || n.endsWith(".pdf") || n.endsWith(".epub"));
            });
    if (files == null) {
      alert("无法读取此文件夹，请使用文件管理器打开");
      return;
    }
    Arrays.sort(
        files,
        (a, b) ->
            a.isDirectory() == b.isDirectory()
                ? a.getName().compareToIgnoreCase(b.getName())
                : (a.isDirectory() ? -1 : 1));
    List<File> choices = new ArrayList<>();
    List<String> labels = new ArrayList<>();
    if (!rootDir.equals(dir)) {
      choices.add(dir.getParentFile());
      labels.add("上一级");
    }
    for (File f : files) {
      choices.add(f);
      labels.add(f.getName() + (f.isDirectory() ? "/" : ""));
    }
    if (choices.isEmpty()) {
      alert("此文件夹里没有 PDF 或 EPUB");
      return;
    }
    new AlertDialog.Builder(this)
        .setTitle(dir.getName())
        .setItems(
            labels.toArray(new String[0]),
            (d, index) -> {
              File f = choices.get(index);
              if (f.isDirectory()) browse(rootDir, f);
              else receive(Uri.fromFile(f));
            })
        .setNegativeButton("取消", null)
        .show();
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request == 1 && result == RESULT_OK && data != null && data.getData() != null)
      receive(data.getData());
  }

  private void receive(Uri uri) {
    if (!"content".equals(uri.getScheme()) && !"file".equals(uri.getScheme())) {
      alert("请选择本机文件");
      return;
    }
    final int task = ++generation;
    message("正在导入…");
    worker.execute(
        () -> {
          try {
            String key = db.importBook(uri);
            runOnUiThread(
                () -> {
                  if (task == generation) open(key);
                });
          } catch (Exception ex) {
            runOnUiThread(
                () -> {
                  if (task == generation) {
                    shelf();
                    alert("导入失败：" + detail(ex));
                  }
                });
          }
        });
  }

  private void open(String id) {
    Cursor c =
        db.getReadableDatabase()
            .rawQuery("SELECT name,kind,page,offset FROM books WHERE id=?", new String[] {id});
    try {
      if (!c.moveToFirst()) {
        shelf();
        return;
      }
      book = id;
      name = c.getString(0);
      kind = c.getString(1);
      page = c.getInt(2);
      savedOffset = c.getInt(3);
    } finally {
      c.close();
    }
    chapters = Collections.emptyList();
    count = 0;
    password = null;
    scroll = null;
    text = null;
    frame(name);
    button(bar, "书库", this::shelf);
    button(bar, "菜单", this::menu);
    LinearLayout nav = row();
    button(nav, "上一页", () -> turn(-1));
    counter = new TextView(this);
    counter.setGravity(Gravity.CENTER);
    nav.addView(counter, new LinearLayout.LayoutParams(0, -2, 1));
    button(nav, "下一页", () -> turn(1));
    root.addView(nav, -1, dp(46));
    body.post(this::render);
  }

  private void message(String s) {
    body.removeAllViews();
    TextView v = new TextView(this);
    v.setGravity(Gravity.CENTER);
    v.setText(s);
    body.addView(v);
  }

  private static String detail(Throwable ex) {
    return ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage();
  }

  private void alert(String msg) {
    if (!isFinishing())
      new AlertDialog.Builder(this).setMessage(msg).setPositiveButton("好", null).show();
  }

  private void save() {
    if (book != null && count > 0)
      db.position(book, page, scroll == null ? savedOffset : scroll.getScrollY());
  }

  private void turn(int delta) {
    jump(page + delta);
  }

  private void jump(int n) {
    if (count < 1 || n < 0 || n >= count || n == page) return;
    page = n;
    savedOffset = 0;
    scroll = null;
    render();
  }

  @Override
  public boolean onKeyDown(int key, KeyEvent e) {
    if (book != null
        && (key == KeyEvent.KEYCODE_DPAD_LEFT
            || key == KeyEvent.KEYCODE_DPAD_RIGHT
            || key == KeyEvent.KEYCODE_PAGE_UP
            || key == KeyEvent.KEYCODE_PAGE_DOWN)) {
      turn(key == KeyEvent.KEYCODE_DPAD_LEFT || key == KeyEvent.KEYCODE_PAGE_UP ? -1 : 1);
      return true;
    }
    return super.onKeyDown(key, e);
  }

  private static final class Page {
    int index, total;
    String plain;
    Bitmap image;
    CharSequence styled;
    List<String> spine;
  }

  private void render() {
    if (book == null || body.getWidth() < 1 || body.getHeight() < 1) return;
    final int request = ++generation,
        wanted = page,
        width = body.getWidth(),
        height = body.getHeight();
    final String id = book, pass = password;
    final boolean pdf = "PDF".equals(kind), original = pdf && !textMode, wide = fitWidth;
    final List<String> spine = chapters;
    text = null;
    scroll = null;
    message("正在打开…");
    worker.execute(
        () -> {
          try {
            Page result = new Page();
            File source = db.source(id);
            if (pdf) {
              PdfBook doc = new PdfBook(this, source, pass);
              try {
                result.total = doc.count;
                if (doc.count < 1) throw new IOException("PDF 没有可阅读的页面");
                result.index = Math.max(0, Math.min(wanted, doc.count - 1));
                doc.select(result.index);
                if (original) result.image = doc.render(width, height, wide);
                else result.plain = doc.text();
              } finally {
                doc.close();
              }
            } else
              try (ZipFile zip = new ZipFile(source)) {
                result.spine = spine.isEmpty() ? EpubOfflineIndexer.spine(zip) : spine;
                result.total = result.spine.size();
                result.index = Math.max(0, Math.min(wanted, result.total - 1));
                String path = result.spine.get(result.index);
                String html = EpubOfflineIndexer.chapterMarkup(zip, path);
                result.styled = Html.fromHtml(html, src -> epubImage(zip, path, src, width), null);
              }
            runOnUiThread(
                () -> {
                  if (request != generation) {
                    if (result.image != null) result.image.recycle();
                    return;
                  }
                  display(result);
                });
          } catch (Exception | LinkageError ex) {
            runOnUiThread(
                () -> {
                  if (request != generation) return;
                  if (pdf
                      && (detail(ex).toLowerCase(Locale.US).contains("password")
                          || ex.getClass().getSimpleName().contains("Password"))) askPassword();
                  else {
                    message("无法打开此页");
                    alert(detail(ex));
                  }
                });
          }
        });
  }

  private Drawable epubImage(ZipFile zip, String chapter, String src, int maxWidth) {
    try {
      int slash = chapter.lastIndexOf('/');
      String path =
          EpubOfflineIndexer.resolveEntryPath(slash < 0 ? "" : chapter.substring(0, slash), src);
      ZipEntry e = zip.getEntry(path);
      if (e == null || e.getSize() < 0 || e.getSize() > 16000000) return null;
      BitmapFactory.Options o = new BitmapFactory.Options();
      o.inJustDecodeBounds = true;
      try (InputStream in = zip.getInputStream(e)) {
        BitmapFactory.decodeStream(in, null, o);
      }
      o.inJustDecodeBounds = false;
      o.inSampleSize = 1;
      while (o.outWidth / o.inSampleSize > maxWidth * 1.5 || o.outHeight / o.inSampleSize > 1400)
        o.inSampleSize *= 2;
      Bitmap b;
      try (InputStream in = zip.getInputStream(e)) {
        b = BitmapFactory.decodeStream(in, null, o);
      }
      if (b == null) return null;
      Drawable d = new BitmapDrawable(getResources(), b);
      int w = Math.min(b.getWidth(), Math.max(1, maxWidth - dp(28)));
      d.setBounds(0, 0, w, Math.max(1, (int) (w * (double) b.getHeight() / b.getWidth())));
      return d;
    } catch (Exception ex) {
      return null;
    }
  }

  private void askPassword() {
    EditText field = new EditText(this);
    field.setSingleLine(true);
    field.setInputType(129);
    new AlertDialog.Builder(this)
        .setTitle("PDF 密码")
        .setView(field)
        .setPositiveButton(
            "打开",
            (d, w) -> {
              password = field.getText().toString();
              render();
            })
        .setNegativeButton("返回书库", (d, w) -> shelf())
        .show();
  }

  private void display(Page p) {
    count = p.total;
    page = p.index;
    if (p.spine != null) chapters = p.spine;
    counter.setText((page + 1) + " / " + count);
    body.removeAllViews();
    scroll = new ScrollView(this);
    scroll.setFillViewport(true);
    body.addView(scroll);
    if (p.image != null) {
      HorizontalScrollView horizontal = new HorizontalScrollView(this);
      horizontal.setFillViewport(true);
      ImageView image = new ImageView(this);
      image.setContentDescription("PDF 第 " + (page + 1) + " 页");
      image.setImageBitmap(p.image);
      int w =
          fitWidth
              ? body.getWidth()
              : (int)
                  Math.round(
                      body.getHeight() * ((double) p.image.getWidth() / p.image.getHeight()));
      int h =
          fitWidth
              ? (int)
                  Math.round(body.getWidth() * ((double) p.image.getHeight() / p.image.getWidth()))
              : body.getHeight();
      FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(w, h);
      lp.gravity = w < body.getWidth() ? Gravity.CENTER_HORIZONTAL : Gravity.LEFT;
      image.setScaleType(ImageView.ScaleType.FIT_XY);
      horizontal.addView(image, lp);
      scroll.addView(horizontal);
    } else {
      CharSequence content = p.styled != null ? p.styled : p.plain;
      if (content == null || content.length() == 0) content = "本页没有文字层，请从菜单切回原页。";
      SpannableString raw = new SpannableString(content);
      for (URLSpan url : raw.getSpans(0, raw.length(), URLSpan.class)) raw.removeSpan(url);
      Cursor marks =
          db.getReadableDatabase()
              .rawQuery(
                  "SELECT start,end,quote FROM marks WHERE book=? AND page=?",
                  new String[] {book, "" + page});
      try {
        while (marks.moveToNext()) {
          int a = marks.getInt(0), b = marks.getInt(1);
          if (a >= 0
              && b > a
              && b <= raw.length()
              && raw.subSequence(a, b).toString().equals(marks.getString(2)))
            raw.setSpan(
                new BackgroundColorSpan(0xffffaca6), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
      } finally {
        marks.close();
      }
      text = new TextView(this);
      text.setTextSize(getPreferences(0).getInt("font", 20));
      text.setPadding(dp(14), dp(8), dp(14), dp(12));
      text.setTextColor(0xff232722);
      text.setTextIsSelectable(true);
      text.setText(raw);
      text.setCustomSelectionActionModeCallback(actions());
      scroll.addView(text);
      GestureDetector taps =
          new GestureDetector(
              this,
              new GestureDetector.SimpleOnGestureListener() {
                @Override
                public boolean onSingleTapConfirmed(android.view.MotionEvent e) {
                  if (text == null || text.hasSelection()) return false;
                  int at = text.getOffsetForPosition(e.getX(), e.getY());
                  Matcher matcher = WORD.matcher(text.getText());
                  while (matcher.find()) {
                    if (matcher.start() > at) break;
                    if (at < matcher.end()) {
                      lookup(matcher.group());
                      return true;
                    }
                  }
                  return false;
                }
              });
      text.setOnTouchListener(
          (v, e) -> {
            taps.onTouchEvent(e);
            return false;
          });
    }
    final ScrollView sc = scroll;
    final int offset = savedOffset;
    sc.post(() -> sc.scrollTo(0, offset));
    db.position(book, page, savedOffset);
  }

  private ActionMode.Callback actions() {
    return new ActionMode.Callback() {
      public boolean onCreateActionMode(ActionMode mode, Menu menu) {
        for (String item : new String[] {"标红", "备注", "查词", "朗读"})
          menu.add(867, Menu.NONE, Menu.NONE, item);
        return true;
      }

      public boolean onPrepareActionMode(ActionMode mode, Menu menu) {
        return false;
      }

      public void onDestroyActionMode(ActionMode mode) {}

      public boolean onActionItemClicked(ActionMode mode, MenuItem item) {
        if (item.getGroupId() != 867 || text == null) return false;
        int a = Math.min(text.getSelectionStart(), text.getSelectionEnd()),
            b = Math.max(text.getSelectionStart(), text.getSelectionEnd());
        if (a < 0 || b <= a) return false;
        String q = text.getText().subSequence(a, b).toString();
        mode.finish();
        String action = item.getTitle().toString();
        if ("朗读".equals(action)) speak(q);
        else if ("查词".equals(action)) lookup(q);
        else if ("标红".equals(action)) mark(a, b, q, null);
        else {
          EditText input = new EditText(ReaderActivity.this);
          new AlertDialog.Builder(ReaderActivity.this)
              .setTitle("添加备注")
              .setMessage(q)
              .setView(input)
              .setPositiveButton("保存", (d, w) -> mark(a, b, q, input.getText().toString()))
              .setNegativeButton("取消", null)
              .show();
        }
        return true;
      }
    };
  }

  private void mark(int a, int b, String q, String note) {
    db.mark(book, page, a, b, q, note);
    savedOffset = scroll.getScrollY();
    render();
  }

  private void lookup(String q) {
    final String word = q.trim();
    final int request = generation;
    worker.execute(
        () -> {
          try {
            String[] entry = db.lookup(word);
            runOnUiThread(
                () -> {
                  if (request == generation) {
                    AlertDialog card = new AlertDialog.Builder(this)
                        .setTitle(word)
                        .setMessage((entry[0].isEmpty() ? "" : "/" + entry[0] + "/\n") + entry[1])
                        .setPositiveButton("关闭", null)
                        .setNeutralButton("再读一次", null)
                        .show();
                    card.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> speak(word));
                    speak(word);
                  }
                });
          } catch (Exception ex) {
            runOnUiThread(
                () -> {
                  if (request == generation) alert(detail(ex));
                });
          }
        });
  }

  private void speak(String phrase) {
    if (!ttsReady) {
      pendingSpeech = phrase;
      if (speaker == null)
        speaker =
            new TextToSpeech(
                getApplicationContext(),
                status ->
                    runOnUiThread(
                        () -> {
                          ttsReady = status == TextToSpeech.SUCCESS;
                          if (ttsReady && pendingSpeech != null) {
                            String next = pendingSpeech;
                            pendingSpeech = null;
                            speak(next);
                          } else {
                            if (speaker != null) speaker.shutdown();
                            speaker = null;
                            alert("设备没有可用的系统朗读引擎");
                          }
                        }));
      return;
    }
    int lang =
        speaker.setLanguage(
            Pattern.compile("[\\u3400-\\u9fff]").matcher(phrase).find()
                ? Locale.CHINESE
                : Locale.US);
    if (lang < 0) {
      alert("系统朗读引擎缺少此语言的声音");
      return;
    }
    for (int i = 0; i < phrase.length(); i += 1600)
      speaker.speak(
          phrase.substring(i, Math.min(i + 1600, phrase.length())),
          i == 0 ? TextToSpeech.QUEUE_FLUSH : TextToSpeech.QUEUE_ADD,
          null);
  }

  private void menu() {
    List<String> items = new ArrayList<>();
    if ("PDF".equals(kind)) {
      items.add(textMode ? "显示 PDF 原页" : "可选文字");
      if (!textMode) items.add(fitWidth ? "适合高度" : "适合宽度");
    }
    if (!"PDF".equals(kind) || textMode) items.add("字号");
    items.add("跳到页码");
    if (!chapters.isEmpty()) items.add("目录");
    items.add("标红与备注");
    new AlertDialog.Builder(this)
        .setItems(
            items.toArray(new String[0]),
            (d, n) -> {
              String a = items.get(n);
              if (a.equals("标红与备注")) {
                notes();
                return;
              }
              if (a.equals("目录")) {
                new AlertDialog.Builder(this)
                    .setTitle(a)
                    .setItems(chapters.toArray(new String[0]), (x, i) -> jump(i))
                    .show();
                return;
              }
              if (a.equals("跳到页码")) {
                EditText edit = new EditText(this);
                edit.setInputType(2);
                new AlertDialog.Builder(this)
                    .setTitle("页码（1–" + count + "）")
                    .setView(edit)
                    .setPositiveButton(
                        "前往",
                        (x, w) -> {
                          try {
                            int i = Integer.parseInt(edit.getText().toString());
                            if (i > 0 && i <= count) jump(i - 1);
                            else alert("页码超出范围");
                          } catch (NumberFormatException ex) {
                            alert("请输入页码");
                          }
                        })
                    .setNegativeButton("取消", null)
                    .show();
                return;
              }
              if (a.equals("字号")) {
                String[] sizes = {"16", "20", "24", "28", "32"};
                new AlertDialog.Builder(this)
                    .setTitle(a)
                    .setItems(
                        sizes,
                        (x, i) -> {
                          getPreferences(0)
                              .edit()
                              .putInt("font", Integer.parseInt(sizes[i]))
                              .apply();
                          savedOffset = scroll == null ? 0 : scroll.getScrollY();
                          render();
                        })
                    .show();
                return;
              }
              if (a.startsWith("适合")) fitWidth = !fitWidth;
              else textMode = !textMode;
              getPreferences(0)
                  .edit()
                  .putBoolean("fitWidth", fitWidth)
                  .putBoolean("textMode", textMode)
                  .apply();
              savedOffset = 0;
              render();
            })
        .show();
  }

  private void notes() {
    Cursor c =
        db.getReadableDatabase()
            .rawQuery(
                "SELECT page,quote,note,start FROM marks WHERE book=? ORDER BY page,start",
                new String[] {book});
    List<String> labels = new ArrayList<>();
    List<Integer> pages = new ArrayList<>();
    try {
      while (c.moveToNext()) {
        pages.add(c.getInt(0));
        labels.add(
            (c.getInt(0) + 1)
                + " · "
                + c.getString(1)
                + (c.isNull(2) ? "" : "\n" + c.getString(2)));
      }
    } finally {
      c.close();
    }
    if (labels.isEmpty()) {
      alert("这本书还没有标红或备注");
      return;
    }
    new AlertDialog.Builder(this)
        .setTitle("标红与备注")
        .setItems(
            labels.toArray(new String[0]),
            (d, i) -> {
              if ("PDF".equals(kind)) textMode = true;
              page = pages.get(i);
              savedOffset = 0;
              render();
            })
        .show();
  }
}
