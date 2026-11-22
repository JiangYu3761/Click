package com.click.classic;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.net.Uri;
import android.provider.OpenableColumns;
import com.click.shell.EpubOfflineIndexer;
import java.io.*;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.zip.ZipFile;

final class Library extends SQLiteOpenHelper {
  private final Context context;

  Library(Context context) {
    super(context, "click-books.db", null, 1);
    this.context = context;
  }

  @Override
  public void onCreate(SQLiteDatabase db) {
    db.execSQL(
        "CREATE TABLE books (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, page"
            + " INTEGER DEFAULT 0, offset INTEGER DEFAULT 0, opened INTEGER DEFAULT 0)");
    db.execSQL(
        "CREATE TABLE marks (book TEXT, page INTEGER, start INTEGER, end INTEGER, quote TEXT, note"
            + " TEXT, PRIMARY KEY(book,page,start,end))");
  }

  @Override
  public void onUpgrade(SQLiteDatabase db, int oldVersion, int version) {}

  File source(String id) {
    return new File(context.getFilesDir(), id + ".book");
  }

  String importBook(Uri uri) throws Exception {
    String name = uri.getLastPathSegment();
    if ("content".equals(uri.getScheme())) {
      Cursor cursor =
          context
              .getContentResolver()
              .query(uri, new String[] {OpenableColumns.DISPLAY_NAME}, null, null, null);
      if (cursor != null)
        try {
          if (cursor.moveToFirst() && !cursor.isNull(0)) name = cursor.getString(0);
        } finally {
          cursor.close();
        }
    }
    if (name == null || name.length() == 0) name = "未命名书籍";
    File temp = File.createTempFile("import-", ".part", context.getFilesDir());
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      try (InputStream in = context.getContentResolver().openInputStream(uri);
          OutputStream out = new FileOutputStream(temp)) {
        if (in == null) throw new IOException("无法读取文件");
        byte[] buf = new byte[32768];
        int n;
        while ((n = in.read(buf)) != -1) {
          out.write(buf, 0, n);
          digest.update(buf, 0, n);
        }
      }
      byte[] magic = new byte[5];
      try (DataInputStream in = new DataInputStream(new FileInputStream(temp))) {
        in.readFully(magic);
      }
      String kind;
      if ("%PDF-".equals(new String(magic, "US-ASCII"))) kind = "PDF";
      else {
        try (ZipFile zip = new ZipFile(temp)) {
          EpubOfflineIndexer.spine(zip);
        }
        kind = "EPUB";
      }
      StringBuilder id = new StringBuilder();
      for (byte b : digest.digest()) id.append(String.format(Locale.US, "%02x", b & 255));
      String key = id.toString();
      File target = source(key);
      if (!target.exists() && !temp.renameTo(target)) throw new IOException("保存书籍失败");
      ContentValues row = new ContentValues();
      row.put("id", key);
      row.put("kind", kind);
      row.put("name", name);
      getWritableDatabase()
          .insertWithOnConflict("books", null, row, SQLiteDatabase.CONFLICT_IGNORE);
      return key;
    } finally {
      temp.delete();
    }
  }

  void position(String book, int page, int offset) {
    ContentValues row = new ContentValues();
    row.put("page", page);
    row.put("offset", offset);
    row.put("opened", System.currentTimeMillis());
    getWritableDatabase().update("books", row, "id=?", new String[] {book});
  }

  void mark(String book, int page, int start, int end, String quote, String note) {
    ContentValues row = new ContentValues();
    row.put("book", book);
    row.put("page", page);
    row.put("start", start);
    row.put("end", end);
    row.put("quote", quote);
    SQLiteDatabase db = getWritableDatabase();
    db.beginTransaction();
    try {
      db.insertWithOnConflict("marks", null, row, SQLiteDatabase.CONFLICT_IGNORE);
      if (note != null) {
        ContentValues changes = new ContentValues();
        changes.put("note", note);
        db.update(
            "marks",
            changes,
            "book=? AND page=? AND start=? AND end=?",
            new String[] {book, "" + page, "" + start, "" + end});
      }
      db.setTransactionSuccessful();
    } finally {
      db.endTransaction();
    }
  }

  String[] lookup(String word) throws IOException {
    File file = new File(context.getFilesDir(), "lexicon-v1.db");
    if (!file.exists()) {
      File tmp = File.createTempFile("lexicon-", ".part", context.getFilesDir());
      try {
        try (InputStream in = context.getAssets().open("lexicon.db");
            OutputStream out = new FileOutputStream(tmp)) {
          byte[] b = new byte[32768];
          int n;
          while ((n = in.read(b)) != -1) out.write(b, 0, n);
        }
        if (!tmp.renameTo(file)) throw new IOException("词库无法打开");
      } finally {
        tmp.delete();
      }
    }
    SQLiteDatabase db =
        SQLiteDatabase.openDatabase(file.getPath(), null, SQLiteDatabase.OPEN_READONLY);
    Cursor c =
        db.rawQuery(
            "SELECT ipa,zh FROM words WHERE word=?", new String[] {word.toLowerCase(Locale.US)});
    try {
      return c.moveToFirst()
          ? new String[] {c.getString(0), c.getString(1)}
          : new String[] {"", "词库暂未收录"};
    } finally {
      c.close();
      db.close();
    }
  }
}
