import sys
from pathlib import Path
import ctranslate2
from huggingface_hub.errors import LocalEntryNotFoundError
import ctypes

from faster_whisper import WhisperModel

MODEL_NAME = "large-v3"
CUBLAS_LIB = "libcublas.so.12"

def pick_device():
    gpu_count = ctranslate2.get_cuda_device_count()
    if gpu_count > 0:
        try:
            ctypes.CDLL(CUBLAS_LIB)
            return "cuda", "float16"
        except OSError:
            pass
    return "cpu", "int8"



def load_model(on_progress):
    on_progress(0, "Завантажую модель...")
    device, compute_type = pick_device()
    if device == "cpu":
        on_progress(0, "Обробка на процесорі — це буде повільніше")
    else:
        on_progress(0, "Обробка на відеокарті — зазвичай це швидко")
    try:
        tr_model = WhisperModel(
            MODEL_NAME,
            device=device,
            compute_type=compute_type,
            local_files_only=True,
        )

    except LocalEntryNotFoundError:
        on_progress(0, "Завантажую модель. Це одноразове завантаження.")
        tr_model = WhisperModel(
            MODEL_NAME,
            device=device,
            compute_type=compute_type,
            local_files_only=False,
        )
    return tr_model


def show_progress(percent, text):
    clear_view = f'[{percent:3.0f}%] {text}'
    print(clear_view)


def transcribe(tr_model, tr_video, on_progress, language):
    segments, info = tr_model.transcribe(
        str(tr_video),
        language=language,
        beam_size=5,  # краще підбирає слова у контексті речення
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=True,
        # True бо будуть видимі явні місця з пропусками, а не вигадані слова, що не відповідають відео
    )

    all_parts = [] # сирець для подальшої обробки
    all_words = []
    for seg in segments:
        percent = seg.end / info.duration * 100
        text = seg.text.strip()
        for w in seg.words:
            word = (w.start, w.end, w.word.strip())
            all_words.append(word)
        part = (seg.start, seg.end, text)
        all_parts.append(part)
        on_progress(percent, text)
    on_progress(100, "Розпізнано")
    return all_parts, all_words


def make_chunk(current):
    start = current[0][0]  # початок першого слова
    end = current[-1][1]  # кінець останнього слова
    text = ' '.join(w[2] for w in current)  # склеїти тексти слів
    return start, end, text


def group_words(words, max_words=3, max_pause=0.5):
    chunks = [] # готові субтитри
    current = [] # слова субтитра, який зараз збираємо

    for word in words:
        if current and word[0] - current[-1][1] > max_pause:
            chunks.append(make_chunk(current))
            current = []

        current.append(word)

        if len(current) == max_words or current[-1][2].endswith(('!','.','?',',')):
            chunks.append(make_chunk(current))
            current = []

    if current:
        chunks.append(make_chunk(current))

    return chunks


def write_clear(segments, path):
    out_clean = path.with_suffix(".txt")  # суцільний текст
    all_text = [text for _, _, text in segments]
    out_clean.write_text(" ".join(all_text), encoding="utf-8")
    return out_clean


def write_srt(segments, path):
    out_srt = path.with_suffix(".srt")  # субтитри
    with out_srt.open("w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(segments, start=1):
            block = f'{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n'
            f.write(block + "\n")
    return out_srt


def srt_time(seconds):
    ms = round(seconds * 1000)
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    result = f'{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}'
    return result



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Використання: python transcribe.py <шлях до відео>")
        sys.exit(1)

    video = Path(sys.argv[1])
    if not video.is_file():
        print(f"Файл не знайдено: {video}")
        sys.exit(1)

    model = load_model(show_progress)
    all_info, all_words = transcribe(model, video, show_progress, 'uk')
    clear_file_path = write_clear(all_info, video)
    str_file_path = write_srt(group_words(all_words, 4), video)
    print(f"Готово:\n {clear_file_path}\n {str_file_path}")

