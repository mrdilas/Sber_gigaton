
import PyPDF2
from pathlib import Path
import hashlib

class PDFSegmenter:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.segments_dir = self.project_root / "segments"
        self.segments_dir.mkdir(exist_ok=True)

    def get_file_hash(self, pdf_path):
        """Создает хэш файла для отслеживания изменений"""
        hasher = hashlib.md5()
        with open(pdf_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def is_already_processed(self, pdf_path, txt_path):
        """Проверяет, был ли файл уже обработан"""
        if not txt_path.exists():
            return False

        # Проверяем хэш в имени файла
        expected_hash = self.get_file_hash(pdf_path)
        return expected_hash in txt_path.stem

    def segment_pdf_to_txt(self, pdf_path):
        """Основная функция сегментации PDF в TXT"""
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")

        # Создаем имя для txt файла с хэшем
        file_hash = self.get_file_hash(pdf_path)
        txt_filename = f"{pdf_path.stem}_{file_hash}.txt"
        txt_path = self.segments_dir / txt_filename

        # Проверяем, не обработан ли уже файл
        if self.is_already_processed(pdf_path, txt_path):
            print(f"Файл уже сегментирован: {txt_path}")
            return txt_path

        print(f"Начинаем сегментацию PDF: {pdf_path}")

        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                segments = []
                total_pages = len(pdf_reader.pages)

                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    # Очищаем и форматируем текст
                    cleaned_text = self.clean_text(text)
                    if cleaned_text.strip():
                        segment = self.create_segment(cleaned_text, page_num + 1, total_pages)
                        segments.append(segment)

                    print(f"Обработана страница {page_num + 1}/{total_pages}", end='\r')

                # Сохраняем все сегменты в один файл
                self.save_segments(segments, txt_path)
                print(f"Сегментация завершена. Сохранено в: {txt_path}")

                return txt_path

        except Exception as e:
            raise Exception(f"Ошибка при обработке PDF: {e}")

    def clean_text(self, text):
        """Очищает и форматирует извлеченный текст"""
        # Удаляем лишние пробелы и переносы строк
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # Убираем слишком короткие строки (возможно артефакты)
                if len(line) > 2:
                    cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def create_segment(self, text, page_num, total_pages):
        """Создает улучшенный структурированный сегмент"""
        segment = {
            'page': page_num,
            'total_pages': total_pages,
            'content': text,
            'segment_id': f"page_{page_num:03d}",
            'metadata': f"=== СТРАНИЦА {page_num}/{total_pages} ==="
        }
        return segment

    def save_segments(self, segments, output_path):
        """Сохраняет сегменты в улучшенном формате"""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Добавляем заголовок документа
            f.write("=== ТЕХНИЧЕСКИЙ ДОКУМЕНТ ===\n")
            f.write(f"Всего страниц: {segments[0]['total_pages']}\n")
            f.write("=" * 50 + "\n\n")
            
            for segment in segments:
                # Улучшенная структура
                f.write(f"📄 СТРАНИЦА {segment['page']}\n")
                f.write("─" * 40 + "\n")
                f.write(segment['content'] + "\n")
                f.write("─" * 40 + "\n\n")
                
                # Добавляем разделитель каждые 5 страниц для удобства
                if segment['page'] % 5 == 0:
                    f.write("✦✦✦ РАЗДЕЛ ✦✦✦\n\n")

    def list_processed_files(self):
        """Показывает список уже обработанных файлов"""
        txt_files = list(self.segments_dir.glob("*.txt"))
        if not txt_files:
            print("Нет обработанных файлов в папке segments")
            return []

        print("Обработанные файлы:")
        for i, file in enumerate(txt_files, 1):
            print(f"{i}. {file.name}")
        return txt_files


# Функция для удобного использования
def process_pdf(pdf_path, project_root="."):
    """
    Основная функция для обработки PDF файла

    Args:
        pdf_path (str): Путь к PDF файлу
        project_root (str): Корневая папка проекта

    Returns:
        Path: Путь к созданному txt файлу
    """
    segmenter = PDFSegmenter(project_root)
    return segmenter.segment_pdf_to_txt(pdf_path)

