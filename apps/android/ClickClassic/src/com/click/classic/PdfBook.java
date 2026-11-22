package com.click.classic;

import android.content.Context;
import android.graphics.Bitmap;
import android.os.ParcelFileDescriptor;
import com.shockwave.pdfium.PdfDocument;
import com.shockwave.pdfium.PdfiumCore;
import java.io.File;
import java.io.IOException;

/** An old device only needs one open native page at a time. */
final class PdfBook {
  private static native String pageText(long handle);

  private final PdfiumCore core;
  private final File file;
  private final String password;
  private PdfDocument doc;
  private long page;
  private int index = -1;
  final int count;

  PdfBook(Context context, File file, String password) throws IOException {
    this.file = file;
    this.password = password;
    core = new PdfiumCore(context);
    System.loadLibrary("clicktext");
    reopen();
    count = core.getPageCount(doc);
  }

  private void reopen() throws IOException {
    close();
    ParcelFileDescriptor fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
    try {
      doc = core.newDocument(fd, password);
    } catch (IOException | RuntimeException ex) {
      fd.close();
      throw ex;
    }
  }

  void select(int number) throws IOException {
    if (index == number) return;
    if (index != -1) reopen();
    page = core.openPage(doc, number);
    index = number;
  }

  Bitmap render(int width, int height, boolean fitWidth) {
    int w = core.getPageWidthPoint(doc, index), h = core.getPageHeightPoint(doc, index);
    if (w < 1 || h < 1) throw new IllegalArgumentException("页面尺寸无效");
    double scale = fitWidth ? (double) width / w : (double) height / h;
    scale =
        Math.min(scale, Math.min(4096.0 / Math.max(w, h), Math.sqrt(1800000.0 / ((double) w * h))));
    int bw = Math.max(1, (int) Math.round(w * scale)),
        bh = Math.max(1, (int) Math.round(h * scale));
    Bitmap image = Bitmap.createBitmap(bw, bh, Bitmap.Config.ARGB_8888);
    image.eraseColor(0xffffffff);
    core.renderPageBitmap(doc, image, index, 0, 0, bw, bh, true);
    return image;
  }

  String text() {
    String value = pageText(page);
    return value == null ? "" : value.replace("\r\n", "\n");
  }

  void close() {
    if (doc != null) core.closeDocument(doc);
    doc = null;
    index = -1;
  }
}
