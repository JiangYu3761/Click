#include <stddef.h>
#include <jni.h>

extern void *FPDFText_LoadPage(void *page);
extern int FPDFText_CountChars(void *text);
extern int FPDFText_GetText(void *text, int start, int count, unsigned short *output);
extern void FPDFText_ClosePage(void *text);

JNIEXPORT jstring JNICALL Java_com_click_classic_PdfBook_pageText(JNIEnv *env, jclass type, jlong page) {
    void *text = FPDFText_LoadPage((void *)(uintptr_t)page);
    if (!text) return NULL;
    int count = FPDFText_CountChars(text);
    jstring result = NULL;
    if (count >= 0 && count < 250000) {
        jcharArray chars = (*env)->NewCharArray(env, count + 1);
        if (chars) {
            jchar *buf = (*env)->GetCharArrayElements(env, chars, NULL);
            if (buf) {
                int length = count ? FPDFText_GetText(text, 0, count, buf) : 0;
                if (length > 0 && buf[length - 1] == 0) length--;
                if (length >= 0 && length <= count)
                    result = (*env)->NewString(env, buf, length);
                (*env)->ReleaseCharArrayElements(env, chars, buf, JNI_ABORT);
            }
        }
    }
    FPDFText_ClosePage(text);
    return result;
}
