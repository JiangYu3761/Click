#include "c-api.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// The model directory is the working directory. Reader text arrives only on stdin.
int main(int argc, char **argv) {
    if (argc != 3 || (strcmp(argv[1], "en") && strcmp(argv[1], "zh"))) return 2;
    char *text = NULL;
    size_t capacity = 0;
    if (getdelim(&text, &capacity, '\0', stdin) <= 0) { free(text); return 2; }

    SherpaOnnxOfflineTtsConfig config = {0};
    config.model.kokoro.model = "model.int8.onnx";
    config.model.kokoro.voices = "voices.bin";
    config.model.kokoro.tokens = "tokens.txt";
    config.model.kokoro.data_dir = "espeak-ng-data";
    int chinese = strcmp(argv[1], "zh") == 0;
    config.model.kokoro.lexicon = chinese ? "lexicon-us-en.txt,lexicon-zh.txt" : "lexicon-us-en.txt";
    if (chinese) config.model.kokoro.dict_dir = "dict";
    config.model.kokoro.lang = chinese ? "cmn" : "en-us";
    if (chinese) config.rule_fsts = "date-zh.fst,number-zh.fst,phone-zh.fst";
    config.model.num_threads = 2;
    config.model.provider = "cpu";
    const SherpaOnnxOfflineTts *tts = SherpaOnnxCreateOfflineTts(&config);
    if (!tts) { free(text); return 1; }

    SherpaOnnxGenerationConfig voice = {0};
    voice.sid = chinese ? 3 : 0; // zf_001 or US English af_maple
    voice.speed = 1.0f;
    voice.silence_scale = 0.2f;
    const SherpaOnnxGeneratedAudio *audio =
        SherpaOnnxOfflineTtsGenerateWithConfig(tts, text, &voice, NULL, NULL);
    int ok = audio && audio->n > 0 &&
        SherpaOnnxWriteWave(audio->samples, audio->n, audio->sample_rate, argv[2]);
    if (audio) SherpaOnnxDestroyOfflineTtsGeneratedAudio(audio);
    SherpaOnnxDestroyOfflineTts(tts);
    free(text);
    return ok ? 0 : 1;
}
